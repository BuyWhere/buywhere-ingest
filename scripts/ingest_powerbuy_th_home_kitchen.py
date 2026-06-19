#!/usr/bin/env python3
"""Power Buy Thailand home/kitchen ingestion.

Scrapes product data from Power Buy's sitemap + product page JSON-LD via
Brightdata residential proxy (required for Cloudflare bypass).

Usage:
    python scripts/ingest_powerbuy_th_home_kitchen.py --skip-ingest
    python scripts/ingest_powerbuy_th_home_kitchen.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from collections import Counter

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products

try:
    import httpx
except ImportError:
    httpx = None

PROXY_URL = (
    "http://brd-customer-hl_3ab737be-zone-residential:o3feuq72olm5"
    "@brd.superproxy.io:22225"
)
BASE_URL = "https://www.powerbuy.co.th"
PRODUCT_SITEMAP = f"{BASE_URL}/sitemap/product-sitemap-1.xml"

MERCHANT_DEFAULTS = {
    "source": "powerbuy_th",
    "merchant_id": "powerbuy_th",
    "region": "TH",
    "country_code": "TH",
    "currency": "THB",
    "platform": "nextjs",
    "is_active": True,
    "in_stock": True,
}

# Home/kitchen category keywords (applied to product URL slugs + JSON-LD breadcrumbs)
HK_KEYWORDS = [
    "kitchen", "appliance", "oven", "fridge", "refrigerator", "microwave",
    "cooker", "stove", "blender", "kettle", "grill", "air-fryer",
    "rice-cooker", "toaster", "juicer", "mixer", "dishwasher", "washing",
    "dryer", "vacuum", "cookware", "pan", "pot", "cutlery",
    "water-heater", "water-filter", "purifier", "fan", "heater",
    "air-conditioner", "iron", "steamer", "coffee-maker", "espresso",
    "slow-cooker", "pressure-cooker", "food-processor",
    "bread-maker", "waffle", "sandwich", "stand-mixer",
    "ice-cream", "water-dispenser", "air-cooler", "air-purifier",
    "humidifier", "dehumidifier", "garment-steamer",
    "mop", "robot-vacuum", "stick-vac", "handheld-vac",
    "curtain", "bedding", "pillow", "mattress", "towel",
    "food-storage", "kitchen-rack", "shelf",
]


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}


def _extract_jsonld(html: str) -> list[dict[str, Any]]:
    """Extract all JSON-LD blocks from a page."""
    results = []
    for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            results.append(data)
        except json.JSONDecodeError:
            continue
    return results


def _is_home_kitchen(product_slug: str, jsonld_data: dict | None = None) -> bool:
    """Determine if a product is home/kitchen based on slug + JSON-LD."""
    slug_lower = product_slug.lower()
    if any(kw in slug_lower for kw in HK_KEYWORDS):
        return True
    if jsonld_data:
        breadcrumbs = jsonld_data.get("breadcrumb", {})
        name = str(jsonld_data.get("name", "")).lower()
        desc = str(jsonld_data.get("description", "")).lower()
        cat_text = name + " " + desc
        if jsonld_data.get("@type") == "BreadcrumbList":
            for item in jsonld_data.get("itemListElement", []):
                item_name = str(item.get("name", "")).lower()
                cat_text += " " + item_name
        if any(kw in cat_text for kw in HK_KEYWORDS):
            return True
    return False

def _parse_product_from_jsonld(data: dict[str, Any], url: str) -> dict[str, Any] | None:
    """Build a normalized product dict from JSON-LD."""
    if data.get("@type") != "Product":
        return None
    offers = data.get("offers", {}) or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    brand = data.get("brand", {}) or {}
    if isinstance(brand, dict):
        brand_name = brand.get("name")
    else:
        brand_name = str(brand) if brand else None

    images = data.get("image") or []
    if isinstance(images, str):
        images = [images]

    sku = str(data.get("sku", ""))
    mpn = data.get("mpn", "")

    returns = data.get("hasMerchantReturnPolicy")
    if isinstance(returns, dict):
        return_policy = returns.get("name") or returns.get("description")
    else:
        return_policy = str(returns) if returns else None

    raw_data = {
        "jsonld": data,
        "mpn": mpn,
        "return_policy": return_policy,
    }

    return {
        "title": data.get("name", ""),
        "price": offers.get("price"),
        "url": url,
        "brand": brand_name,
        "image_url": images[0] if images else None,
        "sku": sku or mpn or url.split("-")[-1],
        "category": "home_kitchen",
        "category_path": ["home_kitchen"],
        "in_stock": offers.get("availability", "").endswith("InStock"),
        "currency": "THB",
        "raw_data": raw_data,
        **MERCHANT_DEFAULTS,
    }

async def fetch_sitemap_urls(client: httpx.AsyncClient) -> list[str]:
    """Fetch all product URLs from the Power Buy sitemap."""
    for attempt in range(5):
        try:
            r = await client.get(PRODUCT_SITEMAP, follow_redirects=True)
            if r.status_code == 200 and len(r.text) > 100000 and "cloudflare" not in r.text.lower()[:200]:
                urls = re.findall(r'<loc>(.*?)</loc>', r.text)
                print(f"Sitemap: {len(urls)} product URLs fetched", flush=True)
                return urls
            else:
                print(f"  Sitemap attempt {attempt + 1}: HTTP {r.status_code}, size={len(r.text)}", flush=True)
        except Exception as e:
            print(f"  Sitemap attempt {attempt + 1}: {e}", flush=True)
        await asyncio.sleep(5 * (attempt + 1))
    return []


def _categorize_url(url: str) -> str | None:
    """Extract category from URL slug. Returns category group or None."""
    slug = url.split("/th/product/")[-1] if "/th/product/" in url else url
    match = re.match(r"^(\d+)-", slug)
    return match.group(1) if match else None


async def discover_home_kitchen_urls(client: httpx.AsyncClient) -> list[str]:
    """Fetch sitemap and filter for home/kitchen products."""
    all_urls = await fetch_sitemap_urls(client)
    if not all_urls:
        print("WARNING: Could not fetch sitemap. Power Buy may be blocking.", flush=True)
        return []

    cats = Counter()
    for url in all_urls:
        cat = _categorize_url(url)
        if cat:
            cats[cat] += 1

    print(f"Categories found: {len(cats)}", flush=True)
    for cat, count in cats.most_common(10):
        print(f"  cat-{cat}: {count} products", flush=True)

    # Filter by home/kitchen keywords
    hk_urls = [url for url in all_urls if _is_home_kitchen(url.split("/th/product/")[-1])]
    print(f"Home/Kitchen products (slug match): {len(hk_urls)}", flush=True)
    return hk_urls

async def scrape_product_page(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any] | None:
    """Scrape a single product page and extract JSON-LD data."""
    async with semaphore:
        for attempt in range(3):
            try:
                r = await client.get(url, follow_redirects=True)
                if r.status_code == 200 and len(r.text) > 10000:
                    html = r.text
                    jsonlds = _extract_jsonld(html)
                    for data in jsonlds:
                        product = _parse_product_from_jsonld(data, url)
                        if product:
                            return product
                    print(f"  No Product JSON-LD at {url}", flush=True)
                    return None
                elif "cloudflare" in r.text.lower()[:200]:
                    await asyncio.sleep(5 * (attempt + 1))
                else:
                    return None
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(3 * (attempt + 1))
    return None


async def scrape_products(
    urls: list[str],
    max_concurrent: int = 5,
    max_products: int | None = None,
) -> list[dict[str, Any]]:
    """Scrape product pages in parallel with concurrency limit."""
    if not httpx:
        print("FATAL: httpx not installed", file=sys.stderr)
        return []

    proxy_url = os.environ.get("BRIGHTDATA_PROXY", PROXY_URL)
    semaphore = asyncio.Semaphore(max_concurrent)

    async with httpx.AsyncClient(
        proxy=proxy_url,
        timeout=30,
        verify=False,
        headers=HEADERS,
    ) as client:
        target = urls[:max_products] if max_products else urls
        products: list[dict[str, Any]] = []
        total = len(target)

        print(f"Scraping {total} product pages ({max_concurrent} concurrent)...", flush=True)
        start = time.time()

        for i in range(0, total, max_concurrent * 2):
            batch = target[i : i + max_concurrent * 2]
            tasks = [scrape_product_page(client, url, semaphore) for url in batch]
            results = await asyncio.gather(*tasks)

            for result in results:
                if result:
                    products.append(result)

            elapsed = time.time() - start
            rate = (i + len(batch)) / elapsed if elapsed > 0 else 0
            print(
                f"  Progress: {min(i + len(batch), total)}/{total} "
                f"({len(products)} found) "
                f"[{rate:.1f} products/s]",
                flush=True,
            )

        elapsed = time.time() - start
        print(
            f"Scraped {len(products)}/{total} products in {elapsed:.1f}s",
            flush=True,
        )
        return products

def write_snapshot(products: list[dict[str, Any]], path: Path) -> None:
    """Write products to NDJSON snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for p in products:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"Snapshot: {path} ({len(products)} products)", flush=True)


def dedupe_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by (sku, url)."""
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for p in products:
        key = (str(p.get("sku", "")), str(p.get("url", "")))
        if key not in seen:
            seen[key] = p
    return list(seen.values())


async def main() -> int:
    parser = argparse.ArgumentParser(description="Power Buy TH home/kitchen ingestion")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "merchants" / f"powerbuy_th_home_kitchen_{time.strftime('%Y-%m-%d')}.ndjson",
    )
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--max-products", type=int, default=None)
    parser.add_argument("--max-concurrent", type=int, default=5)
    args = parser.parse_args()

    if not args.skip_ingest:
        assert_ingestion_allowed()

    targets = configured_database_targets()
    print("Targets:", json.dumps(targets, indent=2), file=sys.stderr)
    print("=" * 60, flush=True)

    proxy_url = os.environ.get("BRIGHTDATA_PROXY", PROXY_URL)
    async with httpx.AsyncClient(
        proxy=proxy_url,
        timeout=30,
        verify=False,
        headers=HEADERS,
    ) as client:
        print("Step 1: Discovering home/kitchen product URLs from sitemap...", flush=True)
        hk_urls = await discover_home_kitchen_urls(client)

        if not hk_urls:
            print("ERROR: No home/kitchen URLs discovered.", file=sys.stderr)
            print(json.dumps({"merchant_id": "powerbuy_th", "products": 0, "error": "sitemap_inaccessible"}))
            return 1

        print(f"\nStep 2: Scraping {len(hk_urls)} home/kitchen product pages...", flush=True)
        products = await scrape_products(hk_urls, max_concurrent=args.max_concurrent, max_products=args.max_products)

        if not products:
            print("WARNING: No products scraped from product pages.", file=sys.stderr)

    deduped = dedupe_products(products)
    print(f"\nDeduped: {len(deduped)} products", flush=True)

    write_snapshot(deduped, args.output)

    ingested = 0
    if not args.skip_ingest and deduped:
        ingested = upsert_products(
            deduped,
            source="powerbuy_th",
            merchant_id="powerbuy_th",
            defaults=MERCHANT_DEFAULTS,
            metadata_tag={"script": "ingest_powerbuy_th_home_kitchen.py", "urls_discovered": len(hk_urls)},
        )
        print(f"Ingested: {ingested}", flush=True)

    result = {
        "merchant_id": "powerbuy_th",
        "urls_discovered": len(hk_urls),
        "products_scraped": len(products),
        "deduped": len(deduped),
        "ingested": ingested,
        "output": str(args.output),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
