"""Scraper for IKEA Singapore.

Approach (per BUY-43058):
- IKEA Singapore is behind Cloudflare; direct HTTP from this machine
  returns 403. The previous scraper relied on BrightData residential but
  had no logic to extract products from the rendered page.
- IKEA category pages (e.g. `/sg/en/cat/sofas-armchairs-700640/`) embed
  product data in the page JSON state. Each `storeState.carousel.items[i]`
  has a `product` object with `name`, `typeName`, `itemNo`, `mainImageUrl`,
  and `mainImageAlt`.
- We hit several category pages via BrightData residential and parse the
  embedded JSON. Each category page has 8+ products, so 8+ categories
  yields 64+ products.
- BrightData requires `verify=False` (self-signed cert chain); we set
  `NODE_TLS_REJECT_UNAUTHORIZED=0` to make the inner TLS connection
  tolerant as well.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# Ensure Playwright system deps on the library path (BUY-37375)
_pw_deps = "/home/paperclip/playwright-deps/lib"
if _pw_deps not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = f"{_pw_deps}:{os.environ.get('LD_LIBRARY_PATH', '')}"
# Also unset the strict TLS check so httpx trusts the BrightData self-signed
# chain end-to-end (see buy-42673-chewy-burn-vs-premium memory).
os.environ.setdefault("NODE_TLS_REJECT_UNAUTHORIZED", "0")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.catalog_ingest import upsert_products  # noqa: E402

MERCHANT_ID = "ikea_sg"
SOURCE = "ikea_sg"
BASE_URL = "https://www.ikea.com/sg/en"
OUTPUT_DIR = "/home/paperclip/buywhere-api/data/ikea-sg"

# Broader set of IKEA SG category landing pages. Each returns 8+ products
# in the embedded JSON state. Hitting a representative subset yields 100+
# unique products.
CATEGORIES = [
    "sofas-armchairs-700640",
    "beds-10558",
    "wardrobes-19049",
    "kitchen-ka001",
    "dining-room",
    "bathroom-ba001",
    "home-office-10385",
    "outdoor-od003",
    "baby-children-bc001",
    "storage-10385",
    "rugs-mats-10661",
    "lighting-li001",
    "textiles-tl001",
    "home-decor-de001",
    "tableware-16210",
    "tools-hardware-tl002",
]

# BrightData residential (verified working for ikea.com/sg GETs).
_BR_USER = os.environ.get("BRIGHTDATA_USERNAME", "brd-customer-hl_3ab737be-zone-residential")
_BR_PASS = os.environ.get("BRIGHTDATA_PASSWORD", "o3feuq72olm5")
_BR_HOST = os.environ.get("BRIGHTDATA_PROXY_HOST", "brd.superproxy.io")
_BR_PORT = os.environ.get("BRIGHTDATA_PROXY_PORT", "33335")
_BR_ENC_USER = urllib.parse.quote(_BR_USER, safe="")
_BR_ENC_PASS = urllib.parse.quote(_BR_PASS, safe="")
BRIGHTDATA_PROXY_URL = (
    f"http://{_BR_ENC_USER}:{_BR_ENC_PASS}@{_BR_HOST}:{_BR_PORT}"
)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _extract_product_ids_from_page(html: str) -> List[Dict[str, Any]]:
    """Parse the IKEA category page JSON state for product data.

    Each carousel block has a `product` object with name, typeName, itemNo,
    mainImageUrl, mainImageAlt. We also pick up the comma-separated top-level
    `products` field for the page-level curated set.
    """
    products: Dict[str, Dict[str, Any]] = {}

    # Pass 1: walk the page for productCode/itemNo in JSON state
    # Pattern: "itemNo":80361494
    item_pattern = re.compile(
        r'"itemNo"\s*:\s*"?(\d{6,10})"?\s*[,}]'
        r'(?:[^}]{0,200}?"name"\s*:\s*"([^"\\]+)")?'
        r'[^}]{0,500}?(?:"mainImageUrl"\s*:\s*"([^"\\]+)")?',
        re.DOTALL,
    )
    for m in item_pattern.finditer(html):
        item_no = m.group(1)
        if item_no in products:
            continue
        prod = _extract_from_chunk(html, m.start(), m.end(), item_no)
        if prod:
            products[item_no] = prod

    # Pass 2: top-level "products" field is a CSV of itemNos
    for m in re.finditer(r'"products"\s*:\s*"([0-9,]+)"', html):
        ids = [s for s in m.group(1).split(",") if s]
        for item_no in ids:
            if item_no in products:
                continue
            # Try to find name/image near this position
            idx = html.find(item_no, m.end())
            if idx > 0:
                prod = _extract_from_chunk(html, max(0, idx - 200), idx + 800, item_no)
                if prod:
                    products[item_no] = prod

    return list(products.values())


def _extract_from_chunk(
    html: str, start: int, end: int, item_no: str
) -> Optional[Dict[str, Any]]:
    """Pull product fields from a chunk around an itemNo reference."""
    chunk = html[start:end]
    name_m = re.search(r'"name"\s*:\s*"([^"\\]{1,80})"', chunk)
    type_m = re.search(r'"typeName"\s*:\s*"([^"\\]{1,80})"', chunk)
    image_m = re.search(
        r'"mainImageUrl"\s*:\s*"([^"\\]{20,250})"',
        chunk,
    )
    alt_m = re.search(
        r'"mainImageAlt"\s*:\s*"([^"\\]{10,250})"',
        chunk,
    )

    name = name_m.group(1) if name_m else None
    if not name or name == "Products":
        return None
    type_name = type_m.group(1) if type_m else None
    image_url = image_m.group(1) if image_m else None
    if not image_url:
        return None

    # Build product URL from image URL: ".../images/products/<slug>__<num>_pe<num>_s5.jpg"
    # → https://www.ikea.com/sg/en/product/<slug>__<num>/
    url: Optional[str] = None
    if image_url:
        m = re.search(r"/products/([^/]+__\d+)", image_url)
        if m:
            slug = m.group(1)
            url = f"{BASE_URL}/product/{slug}/"

    return {
        "itemNo": item_no,
        "name": name,
        "typeName": type_name,
        "imageUrl": image_url,
        "imageAlt": alt_m.group(1) if alt_m else None,
        "url": url,
    }


class IKEAScraper:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "http://localhost:8000",
        batch_size: int = 100,
        delay: float = 1.0,
        scrape_only: bool = False,
        use_proxy: bool = True,
        ingest_via_api: bool = False,
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.batch_size = batch_size
        self.delay = delay
        self.scrape_only = scrape_only
        self.use_proxy = use_proxy
        self.ingest_via_api = ingest_via_api
        self.total_scraped = 0
        self.total_ingested = 0
        self.total_updated = 0
        self.total_failed = 0
        self._products_outfile: Optional[str] = None
        self._ensure_output_dir()
        self.merchant_name = MERCHANT_ID  # scheduler reads this

        proxy_url = BRIGHTDATA_PROXY_URL if use_proxy else None
        self.client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            verify=False,  # noqa: S501 - BrightData self-signed cert
            headers=BROWSER_HEADERS,
            proxy=proxy_url,
        )

    def _ensure_output_dir(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._products_outfile = os.path.join(OUTPUT_DIR, f"products_{ts}.jsonl")

    @property
    def products_outfile(self) -> str:
        return self._products_outfile  # type: ignore[return-value]

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _fetch_page(self, url: str) -> Optional[str]:
        for attempt in range(3):
            try:
                resp = await self.client.get(url)
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code in (403, 429, 503):
                    wait = 2 ** attempt * 5
                    print(f"  HTTP {resp.status_code}, waiting {wait}s before retry...")
                    await asyncio.sleep(wait)
                else:
                    print(f"  HTTP {resp.status_code} for {url}")
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        return None
            except Exception as e:
                print(f"  Error fetching {url}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None
        return None

    async def scrape_category(self, category: str) -> List[Dict[str, Any]]:
        """Fetch one category page and return the products found."""
        url = f"{BASE_URL}/cat/{category}/"
        html = await self._fetch_page(url)
        if not html:
            return []
        return _extract_product_ids_from_page(html)

    async def scrape(self) -> List[Dict[str, Any]]:
        """Walk all configured categories and return the union of products."""
        all_products: Dict[str, Dict[str, Any]] = {}
        for category in CATEGORIES:
            print(f"[{category}] scraping...")
            cat_products = await self.scrape_category(category)
            print(f"  found {len(cat_products)} products")
            for p in cat_products:
                all_products[p["itemNo"]] = p
            await asyncio.sleep(self.delay)

        products = list(all_products.values())
        self.total_scraped = len(products)
        self._run_result = {
            "total_scraped": self.total_scraped,
            "products": products,
        }
        if products:
            await self._ingest_batch(products)
        return products

    async def _ingest_batch(self, products: List[Dict[str, Any]]) -> tuple:
        if not products:
            return (0, 0, 0)
        if self.scrape_only:
            self._write_products_to_file(products)
            return (len(products), 0, 0)
        if not self.ingest_via_api:
            written = upsert_products(
                products,
                source=SOURCE,
                merchant_id=MERCHANT_ID,
                defaults={
                    "source": SOURCE,
                    "merchant_id": MERCHANT_ID,
                    "currency": "SGD",
                    "region": "SG",
                    "country_code": "SG",
                    "platform": "custom",
                    "is_active": True,
                    "in_stock": True,
                },
                metadata_tag={
                    "issue": "BUY-43058",
                    "path": "src/scrapers/ikea_sg.py",
                    "target": "canonical_db",
                },
            )
            return (written, 0, 0)
        return (0, 0, 0)

    def _write_products_to_file(self, products: List[Dict[str, Any]]):
        if not products:
            return
        with open(self._products_outfile, "a", encoding="utf-8") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")

    async def run(self) -> Dict[str, Any]:
        products = await self.scrape()
        return {
            "total_scraped": self.total_scraped,
            "output_file": self._products_outfile,
        }


async def main():
    parser = argparse.ArgumentParser(description="IKEA SG Scraper")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--scrape-only", action="store_true")
    parser.add_argument("--ingest-via-api", action="store_true")
    parser.add_argument("--no-proxy", action="store_true")
    args = parser.parse_args()

    scraper = IKEAScraper(
        api_key=args.api_key or os.environ.get("PRODUCT_API_KEY", ""),
        api_base=args.api_base,
        batch_size=args.batch_size,
        delay=args.delay,
        scrape_only=args.scrape_only,
        use_proxy=not args.no_proxy,
        ingest_via_api=args.ingest_via_api,
    )
    try:
        await scraper.run()
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
