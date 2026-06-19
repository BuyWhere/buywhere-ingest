#!/usr/bin/env python3
"""Ingest Nguyen Kim Vietnam home/kitchen via category page scraping (dataRenderProduct.push)."""
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

BASE_URL = "https://www.nguyenkim.com"
SITEMAP_URLS = [
    "https://www.nguyenkim.com/sitemap-products-1.xml",
    "https://www.nguyenkim.com/sitemap-products-2.xml",
    "https://www.nguyenkim.com/sitemap-products-3.xml",
]
MERCHANT_DEFAULTS = {
    "source": "nguyen_kim_vn",
    "merchant_id": "nguyen_kim_vn",
    "region": "VN",
    "country_code": "VN",
    "currency": "VND",
    "platform": "cscart",
    "is_active": True,
    "in_stock": True,
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,*/*;q=0.8",
}
TIMEOUT = 45
MAX_WORKERS = 5

# Kitchen categories from sitemap + known slug patterns
CATEGORY_SLUGS = [
    "nha-bep", "noi-chao", "dung-cu-nha-bep", "may-pha-ca-phe",
    "bep-tu", "lo-nuong", "lo-vi-song", "am-dun", "am-sieu-toc",
    "com-dien", "noi-chien", "bep-dien", "bep-hong-ngoai",
    "may-xay-thit", "may-danh-trung", "may-ep-trai-cay",
    "bo-noi-tefal", "bo-noi-fissler", "bo-noi-fivestar", "bo-noi-supor",
    "thiet-bi-nha-bep", "dung-cu-nha-bep-delaware",
    "dien-gia-dung", "gia-dung",
]

def _session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def get_category_urls(session):
    """Get HK-specific URLs from sitemaps."""
    all_urls = []
    for surl in SITEMAP_URLS:
        for attempt in range(2):
            try:
                r = session.get(surl, timeout=TIMEOUT)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "xml")
                batch = [loc.get_text() for loc in soup.find_all("loc")]
                all_urls.extend(batch)
                break
            except Exception:
                time.sleep(2)
        time.sleep(1)
    # Filter to kitchen/home categories
    hk = [u for u in all_urls if any(s in u.lower() for s in CATEGORY_SLUGS)]
    print(f"Sitemap: {len(all_urls)} total, {len(hk)} HK", file=sys.stderr)
    return hk

def scrape_category_products(session, cat_slug, max_pages=5):
    """Scrape all products from a category page (pagination via ?page=N)."""
    products = []
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/{cat_slug}/" if page == 1 else f"{BASE_URL}/{cat_slug}/?page={page}"
        try:
            r = session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            html = r.text
        except Exception:
            break
        # Extract from dataRenderProduct.push JS calls
        items = re.findall(r'dataRenderProduct\.push\(\s*(\{.*?\})\s*\)\s*;', html, re.DOTALL)
        if not items:
            break
        for item_json in items:
            try:
                item = json.loads(item_json)
            except json.JSONDecodeError:
                continue
            pid = str(item.get("product_id", ""))
            name = (item.get("name") or "").strip()
            if not pid:
                continue
            list_price = item.get("list_price", "0")
            price = item.get("final_price") or item.get("price") or list_price
            if isinstance(price, str):
                price = price.replace(",", "")
            image_path = item.get("image_url", "") or ""
            if not image_path:
                detailed = item.get("main_pair", {}).get("detailed", {})
                image_path = detailed.get("image_path", "")
            if image_path and not image_path.startswith("http"):
                image_path = f"https:{image_path}"
            products.append({
                "sku": pid,
                "title": name,
                "price": price,
                "url": f"{BASE_URL}/{cat_slug}/",
                "image_url": image_path,
                "category": "home_kitchen",
                "category_path": ["home_kitchen"],
                "in_stock": True,
                "source": "nguyen_kim_vn",
                "merchant_id": "nguyen_kim_vn",
                "raw_data": item,
            })
        time.sleep(0.5)
    # Also get JSON-LD product names to fill in titles
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/{cat_slug}/" if page == 1 else f"{BASE_URL}/{cat_slug}/?page={page}"
        try:
            r = session.get(url, timeout=TIMEOUT)
            html = r.text
        except Exception:
            break
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(data, dict) or data.get("@type") != "Product":
                continue
            sku = data.get("sku", "")
            if sku and data.get("name"):
                # Try to match to our products (may have partial SKU match)
                for p in products:
                    if p["sku"] == sku or sku.endswith(p["sku"]):
                        p["title"] = data["name"]
                        if not p.get("brand"):
                            brand = data.get("brand", {})
                            if isinstance(brand, dict):
                                p["brand"] = brand.get("name")
                        if not p.get("image_url"):
                            img = data.get("image")
                            if isinstance(img, list) and img:
                                p["image_url"] = img[0]
                        break
        time.sleep(0.3)
    # Clean up: remove products without names
    return products

def scrape_all():
    s = _session()
    s.get(f"{BASE_URL}/robots.txt", timeout=15)
    all_products = []
    for slug in CATEGORY_SLUGS:
        cats = scrape_category_products(s, slug)
        print(f"  {slug}: {len(cats)} products", file=sys.stderr)
        all_products.extend(cats)
    return all_products

def dedupe(products):
    seen = {}
    for p in products:
        key = p["sku"]
        if key not in seen:
            seen[key] = p
        elif not seen[key].get("title") and p.get("title"):
            seen[key] = p
    return list(seen.values())

def write_snapshot(products, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for p in products:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Nguyen Kim VN home/kitchen")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "merchants" / "nguyen_kim_vn_home_kitchen_2026-06-19.ndjson")
    parser.add_argument("--skip-ingest", action="store_true")
    args = parser.parse_args()
    if not args.skip_ingest:
        assert_ingestion_allowed()
    targets = configured_database_targets()
    print("Targets:", json.dumps(targets, indent=2), file=sys.stderr)
    products = scrape_all()
    deduped = dedupe(products)
    print(f"Deduped: {len(deduped)}", file=sys.stderr)
    write_snapshot(deduped, args.output)
    print(f"Snapshot: {args.output}", file=sys.stderr)
    ingested = 0
    if not args.skip_ingest:
        ingested = upsert_products(deduped, source="nguyen_kim_vn", merchant_id="nguyen_kim_vn", defaults=MERCHANT_DEFAULTS, metadata_tag={"script": "ingest_nguyen_kim_vn_home_kitchen.py"})
        print(f"Ingested: {ingested}", file=sys.stderr)
    result = {"merchant_id": "nguyen_kim_vn", "scraped": len(products), "deduped": len(deduped), "ingested": ingested, "output": str(args.output)}
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
