"""Lazada Thailand grocery/commercial product scraper."""

import argparse
import asyncio
import json
import os
import re
import time
from typing import Any

import httpx
from playwright.async_api import async_playwright
try:
    from playwright_stealth.stealth import Stealth
except ImportError:
    stealth_async = None

try:
    import cloudscraper
except ModuleNotFoundError:
    cloudscraper = None

from .scraper_registry import register
from .scraper_logging import get_logger

MERCHANT_ID = "lazada_th"
SOURCE = "lazada_th"
BASE_URL = "https://www.lazada.co.th"
OUTPUT_DIR = "/home/paperclip/buywhere-api/data/lazada-th"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-TH,en;q=0.9,th;q=0.8",
    "Referer": "https://www.lazada.co.th/",
}

CATEGORIES = [
    {"id": "lazmart-grocery", "name": "Grocery", "sub": "LazMart", "url": "https://www.lazada.co.th/tag/lazmart/", "target": 8000},
    {"id": "food-beverages", "name": "Grocery", "sub": "Food & Beverages", "url": "https://www.lazada.co.th/food-beverages/", "target": 5000},
    {"id": "snacks", "name": "Grocery", "sub": "Snacks", "url": "https://www.lazada.co.th/snacks/", "target": 3000},
    {"id": "breakfast-cereal", "name": "Grocery", "sub": "Breakfast & Cereal", "url": "https://www.lazada.co.th/breakfast-cereal/", "target": 2000},
    {"id": "beverages", "name": "Grocery", "sub": "Beverages", "url": "https://www.lazada.co.th/beverages/", "target": 4000},
    {"id": "cooking-ingredients", "name": "Grocery", "sub": "Cooking Ingredients", "url": "https://www.lazada.co.th/cooking-ingredients/", "target": 3000},
    {"id": "canned-food", "name": "Grocery", "sub": "Canned & Packaged Food", "url": "https://www.lazada.co.th/canned-packaged-food/", "target": 2000},
    {"id": "rice-noodles", "name": "Grocery", "sub": "Rice & Noodles", "url": "https://www.lazada.co.th/rice-noodles/", "target": 2000},
    {"id": "condiments-sauces", "name": "Grocery", "sub": "Condiments & Sauces", "url": "https://www.lazada.co.th/condiments-sauces/", "target": 2000},
    {"id": "dairy", "name": "Grocery", "sub": "Dairy & Eggs", "url": "https://www.lazada.co.th/dairy-eggs/", "target": 3000},
    {"id": "fresh-food", "name": "Grocery", "sub": "Fresh Food", "url": "https://www.lazada.co.th/fresh-food/", "target": 2000},
    {"id": "frozen-food", "name": "Grocery", "sub": "Frozen Food", "url": "https://www.lazada.co.th/frozen-food/", "target": 2000},
    {"id": "baby-food", "name": "Baby & Kids", "sub": "Baby Food & Diapers", "url": "https://www.lazada.co.th/baby-food-diapers/", "target": 2000},
    {"id": "pet-food", "name": "Pet Supplies", "sub": "Pet Food", "url": "https://www.lazada.co.th/pet-food/", "target": 1500},
    {"id": "personal-care", "name": "Health & Beauty", "sub": "Personal Care", "url": "https://www.lazada.co.th/personal-care/", "target": 3000},
    {"id": "home-care", "name": "Home Care", "sub": "Cleaning & Laundry", "url": "https://www.lazada.co.th/cleaning-laundry/", "target": 2500},
]


@register("lazada_th")
class LazadaTHScraper:
    """Scraper for Lazada Thailand grocery and FMCG categories."""

    DEFAULT_HEADERS = HEADERS
    MAX_RETRIES = 4
    RETRY_DELAY = 5
    REQUEST_TIMEOUT = 60

    def __init__(self,
        api_key="", api_base="http://localhost:8000",
        batch_size=100, delay=1.0, data_dir=OUTPUT_DIR,
        limit=0, scrape_only=False, max_concurrent=4,
        target_products=25000, max_pages_per_category=200,
        scraperapi_key=None, category_filter=None, extract_gtin=False):

        self.api_key = api_key
        self.api_base = api_base
        self.batch_size = batch_size
        self.delay = delay
        self.limit = limit
        self.scrape_only = scrape_only
        self.max_concurrent = max_concurrent
        self.target_products = target_products
        self.max_pages_per_category = max_pages_per_category
        self.scraperapi_key = scraperapi_key or os.environ.get("SCRAPERAPI_KEY")
        self.extract_gtin = extract_gtin
        self.log = get_logger(SOURCE)
        self.client = httpx.AsyncClient(timeout=30.0, headers=self.DEFAULT_HEADERS)
        self.total_scraped = 0
        self.total_ingested = 0
        self.total_updated = 0
        self.total_failed = 0
        self._scraper = None
        self._semaphore = None
        self._category_filter = self._normalize_category_filter(category_filter)
        self._ensure_output_dir()
        if cloudscraper is not None:
            self._scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "desktop": True},
                delay=10,
            )

    @staticmethod
    def _normalize_category_filter(raw):
        if not raw:
            return []
        values = []
        for item in raw.replace(";", ",").split(","):
            v = item.strip().lower()
            if v:
                values.append(v)
        return values

    def _category_matches_filter(self, category):
        if not self._category_filter:
            return True
        candidates = {str(category.get(k, "")).lower()
                      for k in ("id", "name", "sub", "slug")}
        return any(f in c for c in candidates for f in self._category_filter)

    def get_categories(self):
        if not self._category_filter:
            return CATEGORIES
        selected = [c for c in CATEGORIES if self._category_matches_filter(c)]
        if not selected:
            self.log.progress("No categories matched filter: " + ", ".join(self._category_filter))
        return selected

    def _ensure_output_dir(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._products_outfile = os.path.join(OUTPUT_DIR, f"products_{ts}.ndjson")

    @property
    def products_outfile(self):
        if not hasattr(self, "_products_outfile") or self._products_outfile is None:
            ts = time.strftime("%Y%m%d_%H%M%S")
            self._products_outfile = os.path.join(OUTPUT_DIR, f"products_{ts}.ndjson")
        return self._products_outfile

    def _build_scraperapi_url(self, url, params=None):
        import urllib.parse
        if params:
            sep = "&" if "?" in url else "?"
            full_url = f"{url}{sep}{urllib.parse.urlencode(params)}"
        else:
            full_url = url
        encoded = urllib.parse.quote(full_url, safe="")
        return f"http://api.scraperapi.com?api_key={self.scraperapi_key}&url={encoded}&render=true&premium=true&country_code=th"

    async def _init_playwright(self):
        if not hasattr(self, "_playwright") or self._playwright is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
            )

    async def _close_playwright(self):
        if hasattr(self, "_browser") and self._browser:
            await self._browser.close()
        if hasattr(self, "_playwright") and self._playwright:
            await self._playwright.stop()

    async def _fetch_with_playwright(self, url):
        try:
            await self._init_playwright()
            context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-TH",
            )
            page = await context.new_page()
            if stealth_async:
                await Stealth().apply_stealth_async(page)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            content = await page.content()
            await page.close()
            return content
        except Exception as e:
            self.log.progress(f"Playwright unavailable for {url}: {e}")
            return None

    async def _get_with_retry(self, url, params=None):
        if not self.scraperapi_key and self._scraper is None:
            self.log.progress("Skipping: no cloudscraper or ScraperAPI key")
            return None
        for attempt in range(self.MAX_RETRIES):
            try:
                if self.scraperapi_key:
                    proxy_url = self._build_scraperapi_url(url, params)
                    if self._scraper:
                        resp = await asyncio.to_thread(self._scraper.get, proxy_url)
                    else:
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            resp = await client.get(proxy_url, follow_redirects=True)
                elif self._scraper:
                    resp = await asyncio.to_thread(
                        self._scraper.get, url, params=params or {}
                    )
                else:
                    return None
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code in (429, 503):
                    wait = 2 ** attempt * 5
                    self.log.progress(f"Rate limited ({resp.status_code}), waiting {wait}s")
                    await asyncio.sleep(wait)
                else:
                    self.log.request_failed(url if not self.scraperapi_key else proxy_url, attempt, f"HTTP {resp.status_code}")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    self.log.network_error(url, str(e))
                    return None
        return None

    async def fetch_page(self, category, page=1):
        """Fetch a single category page from Lazada TH."""
        url = f"{BASE_URL}/cat/geelhoed?ajax=true&page={page}"
        params = {"categoryId": category["id"], "page": page}
        text = await self._get_with_retry(url, params)
        if text:
            try:
                data = json.loads(text)
                return self._extract_products_from_response(data, category)
            except json.JSONDecodeError:
                return self._extract_products_from_html(text, category)
        return await self._fetch_search_api_fallback(category, page)

    async def _fetch_search_api_fallback(self, category, page=1):
        url = f"{BASE_URL}/search"
        params = {"q": category["sub"].replace("&", ""), "page": page}
        try:
            text = await self._get_with_retry(url, params=params)
            if text is None:
                return []
            return self._extract_products_from_html(text, category)
        except Exception:
            return []

    def _extract_products_from_response(self, data, category):
        for key_path in [
            lambda d: d.get("data", {}).get("products", []),
            lambda d: d.get("products", []),
            lambda d: d.get("mods", {}).get("productItems", []),
            lambda d: d.get("items", []),
        ]:
            try:
                items = key_path(data)
                if items:
                    return list(items)
            except (KeyError, TypeError):
                pass
        return []

    def _extract_products_from_html(self, html, category):
        patterns = [
            r'window\.DS\.conf\s*=\s*(\{.*?\});',
            r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
        ]
        for pattern in patterns:
            m = re.search(pattern, html, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    items = (data.get("data", {}).get("products", [])
                             or data.get("products", {}).get("products", [])
                             or data.get("products", []))
                    if items:
                        return list(items)
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
        return []

    def transform(self, raw, category):
        """Transform a raw product dict into the catalog schema."""
        try:
            sku = str(raw.get("productId", "") or raw.get("sku", "") or raw.get("itemId", "") or "")
            if not sku:
                return None
            name = raw.get("name", "") or raw.get("title", "") or raw.get("productTitle", "") or ""
            if not name:
                return None
            price = raw.get("price", 0.0)
            if isinstance(price, str):
                price = float(price.replace("฿", "").replace("THB", "").replace(",", "").strip() or 0)
            elif isinstance(price, int):
                price = float(price) / 100000.0 if price > 100000 else float(price)
            images = raw.get("images", []) or raw.get("imageUrl", "") or []
            image_url = ""
            if isinstance(images, list) and images:
                image_url = images[0] if isinstance(images[0], str) else ""
            elif isinstance(images, str) and images:
                image_url = images
            product_url = raw.get("productUrl", "") or raw.get("url", "") or raw.get("product_url", "")
            if product_url and not product_url.startswith("http"):
                product_url = BASE_URL + product_url
            brand = raw.get("brand", "") or raw.get("brandName", "") or raw.get("productBrand", "") or ""
            primary_category = category["name"]
            sub_category = category["sub"]
            category_path = [category["name"], category["sub"]]
            seller = raw.get("seller", {}) or raw.get("sellerInfo", {}) or {}
            seller_name = ""
            if isinstance(seller, dict):
                seller_name = seller.get("name", "") or seller.get("shopName", "") or seller.get("sellerName", "") or ""
            else:
                seller_name = str(seller) if seller else ""
            return {
                "sku": sku,
                "gtin": raw.get("gtin13") or raw.get("gtin") or "",
                "merchant_id": MERCHANT_ID,
                "title": name,
                "description": raw.get("description", "") or raw.get("productDescription", "") or "",
                "price": price,
                "currency": "THB",
                "url": product_url,
                "image_url": image_url,
                "category": primary_category,
                "category_path": category_path,
                "brand": brand,
                "is_active": True,
                "metadata": {
                    "original_price": float(raw.get("originalPrice", price) if isinstance(raw.get("originalPrice"), (int, float)) else price),
                    "subcategory": sub_category,
                    "seller_name": seller_name,
                    "vertical": primary_category,
                    "source": SOURCE,
                },
            }
        except Exception:
            return None

    async def scrape_category(self, category):
        async with self._semaphore:
            cat_name = category["name"]
            sub_name = category["sub"]
            target = category.get("target", 2000)
            self.log.progress(f"[{cat_name} / {sub_name}] Starting, target={target}")
            counts = {"scraped": 0, "ingested": 0, "updated": 0, "failed": 0}
            batch = []
            page = 1
            while self.total_scraped < self.target_products and counts["scraped"] < target:
                if self.limit > 0 and self.total_scraped >= self.limit:
                    break
                products_raw = await self.fetch_page(category, page)
                if not products_raw:
                    break
                for raw in products_raw:
                    if self.limit > 0 and self.total_scraped >= self.limit:
                        break
                    product = self.transform(raw, category)
                    if product is None:
                        continue
                    batch.append(product)
                    counts["scraped"] += 1
                    self.total_scraped += 1
                self.log.progress(f"  page={page}, scraped={counts['scraped']}, total={self.total_scraped}")
                if len(products_raw) < 40:
                    break
                page += 1
                await asyncio.sleep(self.delay)
            if batch and not self.scrape_only:
                i, u, f = await self.ingest_batch(batch)
                counts["ingested"] += i
                counts["updated"] += u
                counts["failed"] += f
            elif batch and self.scrape_only:
                self._write_ndjson(batch)
            self.log.progress(f"[{cat_name} / {sub_name}] Done: {counts}")
            return counts

    def _write_ndjson(self, products):
        with open(self.products_outfile, "a") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False, default=str) + "\n")
        self.log.progress(f"Wrote {len(products)} products to {self.products_outfile}")

    async def ingest_batch(self, batch):
        """Ingest a batch of products via the catalog API."""
        if not batch:
            return (0, 0, 0)
        ingested = 0
        updated = 0
        failed = 0
        url = f"{self.api_base}/v1/ingest/products"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }
        try:
            resp = await self.client.post(url, json={"products": batch}, headers=headers)
            if resp.status_code in (200, 201):
                data = resp.json()
                ingested = data.get("ingested", data.get("created", len(batch)))
                updated = data.get("updated", 0)
                self.log.progress(f"Ingested batch: {ingested} created, {updated} updated")
            else:
                failed = len(batch)
                self.log.ingestion_error(f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            failed = len(batch)
            self.log.ingestion_error(f"Error: {e}")
        return (ingested, updated, failed)

    async def run(self):
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        mode = "scrape only" if self.scrape_only else f"API: {self.api_base}"
        selected = self.get_categories()
        self.log.progress("Lazada TH Grocery Scraper starting...")
        self.log.progress(f"Mode: {mode}, Batch: {self.batch_size}, Delay: {self.delay}s")
        self.log.progress(f"Target: {self.target_products} products, Categories: {len(selected)}")
        start = time.time()
        tasks = [self.scrape_category(cat) for cat in selected]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start
        summary = {
            "elapsed_seconds": round(elapsed, 1),
            "total_scraped": self.total_scraped,
            "total_ingested": self.total_ingested,
            "total_updated": self.total_updated,
            "total_failed": self.total_failed,
            "output_file": self.products_outfile,
            "target": self.target_products,
        }
        self.log.progress(f"Scraper complete: {summary}")
        return summary

    async def close(self):
        await self.client.aclose()
        await self._close_playwright()

    @classmethod
    def add_cli_args(cls, parser):
        parser.add_argument("--api-key", default="", help="BuyWhere API key")
        parser.add_argument("--api-base", default="http://localhost:8000", help="API base URL")
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--delay", type=float, default=1.0)
        parser.add_argument("--data-dir", default=OUTPUT_DIR)
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--scrape-only", action="store_true")
        parser.add_argument("--max-concurrent", type=int, default=4)
        parser.add_argument("--target", type=int, default=25000)
        parser.add_argument("--max-pages", type=int, default=200)
        parser.add_argument("--scraperapi-key", default=None)
        parser.add_argument("--categories", default=None)
        parser.add_argument("--extract-gtin", action="store_true")

    @classmethod
    def from_args(cls, args):
        return cls(
            api_key=args.api_key,
            api_base=args.api_base,
            batch_size=args.batch_size,
            delay=args.delay,
            data_dir=args.data_dir,
            limit=args.limit,
            scrape_only=args.scrape_only,
            max_concurrent=args.max_concurrent,
            target_products=args.target,
            max_pages_per_category=args.max_pages,
            scraperapi_key=args.scraperapi_key,
            category_filter=args.categories,
        )


async def main():
    parser = argparse.ArgumentParser(description="Lazada TH Grocery Scraper")
    LazadaTHScraper.add_cli_args(parser)
    args = parser.parse_args()
    scraper = LazadaTHScraper.from_args(args)
    try:
        await scraper.run()
    finally:
        await scraper.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
