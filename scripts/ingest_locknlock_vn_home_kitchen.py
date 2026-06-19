#!/usr/bin/env python3
"""Ingest LocknLock Vietnam home/kitchen products via sitemap + product page JSON-LD scraping."""
from __future__ import annotations
import argparse
import json
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

BASE_URL = "https://www.locknlock.vn"
SITEMAP_URL = f"{BASE_URL}/sitemap_0-product.xml"
MERCHANT_DEFAULTS = {
    "source": "locknlock_vn",
    "merchant_id": "locknlock_vn",
    "region": "VN",
    "country_code": "VN",
    "currency": "VND",
    "platform": "sfcc",
    "is_active": True,
    "in_stock": True,
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
TIMEOUT = 30
MAX_WORKERS = 10

def fetch(url, max_retries=2):
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.text
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
    return None

def get_product_urls():
    xml = fetch(SITEMAP_URL)
    if not xml:
        print("FATAL: could not fetch sitemap", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(xml, "xml")
    urls = [loc.get_text() for loc in soup.find_all("loc")]
    vi_urls = [u for u in urls if "/vi-vn/" in u]
    print(f"Sitemap: {len(urls)} total, {len(vi_urls)} vi-vn URLs", file=sys.stderr)
    return vi_urls

def extract_product(html, url):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict) or data.get("@type") != "Product":
            continue
        offers = data.get("offers", {})
        price = None
        low = offers.get("lowprice")
        if isinstance(low, dict):
            price = low.get("sales", {}).get("value")
        if not price:
            price = offers.get("price")
        sku = data.get("sku") or data.get("model") or ""
        if not sku:
            return None
        brand = None
        if isinstance(data.get("brand"), dict):
            brand = data["brand"].get("name")
        image = None
        img = data.get("image")
        if isinstance(img, list) and img:
            image = img[0]
        elif isinstance(img, str):
            image = img
        return {
            "title": data.get("name", ""),
            "price": price,
            "url": url,
            "brand": brand,
            "image_url": image,
            "sku": sku,
            "category": "home_kitchen",
            "category_path": ["home_kitchen"],
            "in_stock": True,
            "raw_data": data,
        }
    return None

def scrape_one(url):
    html = fetch(url)
    if not html:
        return None
    product = extract_product(html, url)
    if product:
        product["source"] = "locknlock_vn"
        product["merchant_id"] = "locknlock_vn"
    return product

def scrape_products(urls, max_products=None):
    products = []
    target = urls[:max_products] if max_products else urls
    print(f"Scraping {len(target)} products with {MAX_WORKERS} workers...", file=sys.stderr)
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        fut_map = {pool.submit(scrape_one, url): url for url in target}
        for fut in as_completed(fut_map):
            url = fut_map[fut]
            done += 1
            try:
                product = fut.result()
                if product:
                    products.append(product)
            except Exception as e:
                pass
            if done % 20 == 0:
                print(f"  Progress: {done}/{len(target)}", file=sys.stderr)
    print(f"Scraped {len(products)}/{len(target)} products", file=sys.stderr)
    return products

def dedupe(products):
    seen = {}
    for p in products:
        key = (p["sku"], p["url"])
        if key not in seen:
            seen[key] = p
    return list(seen.values())

def write_snapshot(products, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for p in products:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser(description="LocknLock VN home/kitchen ingestion")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "merchants" / "locknlock_vn_home_kitchen_2026-06-19.ndjson")
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--max-products", type=int, default=None)
    args = parser.parse_args()
    if not args.skip_ingest:
        assert_ingestion_allowed()
    targets = configured_database_targets()
    print("Targets:", json.dumps(targets, indent=2), file=sys.stderr)
    urls = get_product_urls()
    products = scrape_products(urls, max_products=args.max_products)
    deduped = dedupe(products)
    print(f"Deduped: {len(deduped)}", file=sys.stderr)
    write_snapshot(deduped, args.output)
    print(f"Snapshot: {args.output}", file=sys.stderr)
    ingested = 0
    if not args.skip_ingest:
        ingested = upsert_products(deduped, source="locknlock_vn", merchant_id="locknlock_vn", defaults=MERCHANT_DEFAULTS, metadata_tag={"script": "ingest_locknlock_vn_home_kitchen.py"})
        print(f"Ingested: {ingested}", file=sys.stderr)
    result = {"merchant_id": "locknlock_vn", "sitemap_urls": len(urls), "scraped": len(products), "deduped": len(deduped), "ingested": ingested, "output": str(args.output)}
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
