#!/usr/bin/env python3
"""Ingest Ruparupa/Informa Indonesia home/kitchen products via
sitemap + __NEXT_DATA__ scraping.

Ruparupa (www.ruparupa.com) is a Next.js SSR marketplace carrying
AZKO, Informa, Toys Kingdom, and other home/living brands.
This script:
1. Downloads all 6 product sitemaps from sitemaps/sitemap_odi/
2. Filters URLs matching home/kitchen category patterns
3. Concurrently scrapes product pages for SSR-embedded __NEXT_DATA__
4. Extracts SKU, title, price, images, brand, category
5. Deduplicates and snapshots to NDJSON, then upserts to catalog DB.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products
BASE_URL = "https://www.ruparupa.com"
SITEMAP_URLS = [f"https://www.ruparupa.com/sitemaps/sitemap_odi/sitemap_product_{i}.xml.gz" for i in range(1, 7)]

MERCHANT_DEFAULTS = {
    "source": "ruparupa_id",
    "merchant_id": "ruparupa_id",
    "region": "ID",
    "country_code": "ID",
    "currency": "IDR",
    "platform": "nextjs",
    "is_active": True,
    "in_stock": True,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
}

TIMEOUT = 45
MAX_WORKERS = 8

def _scraperapi_url(target_url: str) -> str:
    key = os.environ.get("SCRAPERAPI_KEY") or os.environ.get("SCRAPER_API_KEY")
    if not key:
        return target_url
    params = {
        "api_key": key,
        "url": target_url,
        "country_code": "id",
    }
    return f"https://api.scraperapi.com/?api_key={key}&url={target_url}&country_code=id"


def _fetch(url: str) -> str | None:
    """Fetch a URL, falling back to ScraperAPI if direct access fails."""
    # Try direct first (sitemaps work with proper headers)
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    # Fallback to ScraperAPI for protected pages
    proxy_url = _scraperapi_url(url)
    if proxy_url != url:
        try:
            r = requests.get(proxy_url, timeout=TIMEOUT * 2)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
    return None
# Home/kitchen URL patterns (path segments that indicate home/kitchen categories)
HK_PATH_PATTERNS = [
    "dapur", "kitchen", "living-room", "ruang-makan", "ruang-keluarga",
    "perlengkapan-memasak", "perlengkapan-makan", "perlengkapan-dapur",
    "peralatan-makan", "peralatan-dapur", "alat-masak",
    "home-living", "home-furnishing", "home-decoration",
    "furniture", "furnitur",
    "organizer-dapur", "penyimpanan-dapur",
    "kebersihan-rumah", "household-cleaning",
    "dekorasi", "dekorasi-rumah",
    "small-appliances", "home-appliances",
    "homey", "cozy",
    "bedroom", "kamar-tidur",
    "home-renovation", "renovasi-rumah",
    "bathroom", "kamarmandi",
    "dining",
]
def _session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch_sitemap_urls() -> list[str]:
    """Download all product sitemaps and return all product URLs."""
    all_urls: list[str] = []
    for surl in SITEMAP_URLS:
        for attempt in range(2):
            try:
                r = requests.get(surl, headers=HEADERS, timeout=TIMEOUT)
                r.raise_for_status()
                xml = r.content
                # The CDN may serve gzipped content with application/octet-stream
                # Check magic bytes for gzip (1f 8b)
                import gzip
                if xml[:2] == b'\x1f\x8b':
                    xml = gzip.decompress(xml)
                soup = BeautifulSoup(xml, "xml")
                batch = [loc.get_text() for loc in soup.find_all("loc")]
                all_urls.extend(batch)
                break
            except Exception:
                if attempt < 1:
                    time.sleep(2)
        time.sleep(0.5)
    print(f"Sitemaps: {len(all_urls)} total product URLs", file=sys.stderr)
    return all_urls

def is_home_kitchen_url(url: str) -> bool:
    """Check if a product URL belongs to a home/kitchen category.
    Ruparupa URLs: /p/product-slug.html
    We inspect the slug for known HK patterns."""
    slug = url.lower()
    for pattern in HK_PATH_PATTERNS:
        if pattern in slug:
            return True
    return False
def extract_product(html: str, url: str) -> dict[str, Any] | None:
    """Extract product data from SSR-embedded __NEXT_DATA__ JSON."""
    m = re.search(r'__NEXT_DATA__" type="application/json">(.+?)</script>', html, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    page_props = data.get("props", {}).get("pageProps", {})
    results = page_props.get("results", {})
    detail = results.get("productDetail", {})
    if not detail:
        return None
    variants = detail.get("variants", [])
    if not variants:
        return None
    v0 = variants[0]
    sku = v0.get("sku", "")
    if not sku:
        return None
    prices = v0.get("prices", [])
    price = None
    if prices:
        price = prices[0].get("special_price") or prices[0].get("price")
    images = v0.get("images", [])
    image_url = None
    if images:
        img = images[0].get("image_url", "")
        if img and not img.startswith("http"):
            img = f"https://cdn.ruparupa.io{img}"
        image_url = img
    brand_data = detail.get("brand", {})
    brand = brand_data.get("name") if isinstance(brand_data, dict) else None
    categories = detail.get("categories_vendor", [])
    cat_names = [c.get("name", "") for c in categories] if categories else []
    category = "home_kitchen"
    if cat_names:
        category = cat_names[-1] if cat_names else "home_kitchen"
    title = v0.get("product_group", {}).get("name") or detail.get("name", "")
    if isinstance(title, dict):
        title = title.get("name", "")
    attr_sap = v0.get("attribute_sap", {})
    description = attr_sap.get("basic_data_text", "")
    in_stock = v0.get("is_in_stock", 1)
    return {
        "sku": sku,
        "title": title,
        "price": price,
        "url": url,
        "brand": brand,
        "image_url": image_url,
        "description": description,
        "category": category,
        "category_path": cat_names,
        "in_stock": bool(in_stock),
        "gtin": (v0.get("gtins") or [{}])[0].get("gtin") if v0.get("gtins") else None,
        "source": "ruparupa_id",
        "merchant_id": "ruparupa_id",
        "raw_data": detail,
    }

def scrape_product(url: str) -> dict[str, Any] | None:
    """Fetch a product page and extract structured data."""
    html = _fetch(url)
    if not html:
        return None
    product = extract_product(html, url)
    return product


def scrape_products(urls: list[str]) -> list[dict[str, Any]]:
    """Concurrently scrape product pages."""
    products: list[dict[str, Any]] = []
    total = len(urls)
    done = 0
    print(f"Scraping {total} products with {MAX_WORKERS} workers...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        fut_map = {pool.submit(scrape_product, url): url for url in urls}
        for fut in as_completed(fut_map):
            done += 1
            try:
                product = fut.result()
                if product:
                    products.append(product)
            except Exception:
                pass
            if done % 100 == 0:
                print(f"  Progress: {done}/{total} (found {len(products)})", file=sys.stderr)
    print(f"Scraped {len(products)}/{total} products", file=sys.stderr)
    return products


def dedupe(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by SKU."""
    seen: dict[str, dict[str, Any]] = {}
    for p in products:
        key = p["sku"]
        if key not in seen:
            seen[key] = p
        elif not seen[key].get("title") and p.get("title"):
            seen[key] = p
    return list(seen.values())


def write_snapshot(products: list[dict[str, Any]], path: Path) -> None:
    """Write products as NDJSON snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for p in products:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

def main() -> int:
    parser = argparse.ArgumentParser(description="Ruparupa/Informa ID home/kitchen ingestion")
    parser.add_argument("--output", type=Path,
        default=REPO_ROOT / "merchants" / "ruparupa_id_home_kitchen_2026-06-19.ndjson")
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--max-products", type=int, default=None,
        help="Limit total products to scrape (for testing)")
    args = parser.parse_args()

    if not args.skip_ingest:
        assert_ingestion_allowed()

    targets = configured_database_targets()
    print("Targets:", json.dumps(targets, indent=2), file=sys.stderr)

    # Step 1: Get all product URLs from sitemaps
    all_urls = fetch_sitemap_urls()

    # Step 2: Filter for home/kitchen
    hk_urls = [u for u in all_urls if is_home_kitchen_url(u)]
    print(f"HK filtered: {len(hk_urls)}/{len(all_urls)}", file=sys.stderr)

    if args.max_products:
        hk_urls = hk_urls[:args.max_products]

    # Step 3: Scrape products
    products = scrape_products(hk_urls)

    # Step 4: Deduplicate
    deduped = dedupe(products)
    print(f"Deduped: {len(deduped)}", file=sys.stderr)

    # Step 5: Write snapshot
    write_snapshot(deduped, args.output)
    print(f"Snapshot: {args.output}", file=sys.stderr)

    # Step 6: Ingest to catalog DB
    ingested = 0
    if not args.skip_ingest:
        ingested = upsert_products(deduped,
            source="ruparupa_id",
            merchant_id="ruparupa_id",
            defaults=MERCHANT_DEFAULTS,
            metadata_tag={"script": "ingest_ruparupa_id_home_kitchen.py"})
        print(f"Ingested: {ingested}", file=sys.stderr)

    result = {
        "merchant_id": "ruparupa_id",
        "sitemap_urls": len(all_urls),
        "hk_urls": len(hk_urls),
        "scraped": len(products),
        "deduped": len(deduped),
        "ingested": ingested,
        "output": str(args.output),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
