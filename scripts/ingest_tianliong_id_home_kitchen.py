#!/usr/bin/env python3
"""Ingest Toko Tian Liong Indonesia home/kitchen products via HTML scraping."""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products
BASE_URL = "https://tianliong.co.id"
MERCHANT_DEFAULTS = {"source": "tianliong_id", "merchant_id": "tianliong_id", "region": "ID", "country_code": "ID", "currency": "IDR", "platform": "phpmu", "is_active": True, "in_stock": True}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept": "text/html,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5"}
TIMEOUT = 30
MAX_WORKERS = 10
CATEGORY_SLUGS = ["chinaware", "coffee--barware", "glassware", "kitchenware--utensil", "operating-equipment", "sale"]
print('Constants OK')

def fetch(url, retries=2):
    for a in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.text
        except Exception:
            if a < retries - 1:
                time.sleep(1.5)
    return None

def get_product_urls():
    urls = set()
    html = fetch(BASE_URL)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            h = a["href"]
            if "/produk/detail/" in h:
                urls.add(h if h.startswith("http") else urljoin(BASE_URL, h))
    for cat in CATEGORY_SLUGS:
        html = fetch(f"{BASE_URL}/produk/kategori/{cat}")
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                h = a["href"]
                if "/produk/detail/" in h:
                    urls.add(h if h.startswith("http") else urljoin(BASE_URL, h))
    result = sorted(urls)
    print(f"Found {len(result)} product URLs", file=sys.stderr)
    return result

def scrape_detail(url):
    html = fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag else ""
    title = re.sub(r"\s*[-–]\s*Toko Tian Liong.*$", "", title).strip()
    price = None
    h4 = soup.find("h4", class_="price")
    if h4:
        m = re.search(r"Rp\s*([\d.,]+)", h4.get_text())
        if m:
            price = m.group(1).replace(".", "").replace(",", "")
    if not price:
        els = soup.find_all(class_=lambda c: c and "harga" in c.lower())
        for el in els:
            m = re.search(r"([\d.,]+)", el.get_text().replace(".", "").replace(",", ""))
            if m:
                price = m.group(1)
                break
    image_url = None
    og = soup.find("meta", property="og:image")
    if og:
        image_url = og.get("content", "")
        if image_url and not image_url.startswith("http"):
            image_url = f"{BASE_URL}{image_url}" if image_url.startswith("/") else f"{BASE_URL}/{image_url}"
    sku = url.rstrip("/").split("/")[-1] or str(hash(url))
    return {"sku": sku, "title": title, "price": price, "url": url, "brand": "Toko Tian Liong", "image_url": image_url, "category": "home_kitchen", "category_path": ["home_kitchen"], "in_stock": True, "source": "tianliong_id", "merchant_id": "tianliong_id"}

def scrape_all(urls):
    products = []
    total = len(urls)
    done = 0
    print(f"Scraping {total} products with {MAX_WORKERS} workers...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        fmap = {pool.submit(scrape_detail, u): u for u in urls}
        for fut in as_completed(fmap):
            done += 1
            try:
                p = fut.result()
                if p:
                    products.append(p)
            except Exception:
                pass
            if done % 20 == 0:
                print(f"  Progress: {done}/{total} (found {len(products)})", file=sys.stderr)
    print(f"Scraped {len(products)}/{total} products", file=sys.stderr)
    return products

def dedupe(products):
    seen = {}
    for p in products:
        k = p["sku"]
        if k not in seen:
            seen[k] = p
        elif not seen[k].get("title") and p.get("title"):
            seen[k] = p
    return list(seen.values())

def write_snapshot(products, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for p in products:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Toko Tian Liong ID home/kitchen ingestion")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "merchants" / "tianliong_id_home_kitchen_2026-06-19.ndjson")
    parser.add_argument("--skip-ingest", action="store_true")
    args = parser.parse_args()
    if not args.skip_ingest:
        assert_ingestion_allowed()
    targets = configured_database_targets()
    print("Targets:", json.dumps(targets, indent=2), file=sys.stderr)
    urls = get_product_urls()
    products = scrape_all(urls)
    deduped = dedupe(products)
    print(f"Deduped: {len(deduped)}", file=sys.stderr)
    write_snapshot(deduped, args.output)
    print(f"Snapshot: {args.output}", file=sys.stderr)
    ingested = 0
    if not args.skip_ingest:
        ingested = upsert_products(deduped, source="tianliong_id", merchant_id="tianliong_id", defaults=MERCHANT_DEFAULTS, metadata_tag={"script": "ingest_tianliong_id_home_kitchen.py"})
        print(f"Ingested: {ingested}", file=sys.stderr)
    result = {"merchant_id": "tianliong_id", "urls_found": len(urls), "scraped": len(products), "deduped": len(deduped), "ingested": ingested, "output": str(args.output)}
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
