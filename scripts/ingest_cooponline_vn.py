#!/usr/bin/env python3
"""Ingest Co.op Online Vietnam grocery products via sitemap + JSON-LD parsing."""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products

BASE_URL = "https://cooponline.vn"
SITEMAP_INDEX_URL = f"{BASE_URL}/sitemap-collection-products.xml"

MERCHANT_DEFAULTS = {
    "source": "cooponline_vn",
    "merchant_id": "cooponline_vn",
    "region": "VN",
    "country_code": "VN",
    "currency": "VND",
    "platform": "custom",
    "is_active": True,
    "in_stock": True,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

TIMEOUT = 30
MAX_WORKERS = 10


def fetch(url: str, retries: int = 2) -> str | None:
    for _ in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception:
            continue
    return None


def _parse_loc_urls(xml_text: str) -> list[str]:
    soup = BeautifulSoup(xml_text, "xml")
    return [node.get_text().strip() for node in soup.find_all("loc")]


def get_product_urls(max_sitemaps: int | None = None) -> list[str]:
    index_xml = fetch(SITEMAP_INDEX_URL)
    if not index_xml:
        print("FATAL: failed to fetch coop online sitemap index", file=sys.stderr)
        return []

    sitemap_urls = [
        url
        for url in _parse_loc_urls(index_xml)
        if "/sitemap-collection-products-" in url
    ]
    if not sitemap_urls:
        sitemap_urls = [
            url
            for url in _parse_loc_urls(index_xml)
            if "sitemap-collection" in url
            or "sitemap" in url
        ]

    if max_sitemaps:
        sitemap_urls = sitemap_urls[:max_sitemaps]

    print(f"Discovered {len(sitemap_urls)} collection sitemaps", file=sys.stderr)
    product_urls: list[str] = []
    seen: set[str] = set()
    for sitemap_url in sitemap_urls:
        xml = fetch(sitemap_url)
        if not xml:
            continue
        for url in _parse_loc_urls(xml):
            if not url.startswith(BASE_URL):
                continue
            if "googleusercontent.com" in url:
                continue
            if url in seen:
                continue
            seen.add(url)
            product_urls.append(url)
        print(f"  {sitemap_url}: {len(product_urls)} collected", file=sys.stderr)

    return product_urls


def _parse_price(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace(" ", "")
    return text


def extract_product(html: str, url: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        content = script.string
        if not content:
            continue
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict) or payload.get("@type") != "Product":
            continue

        brand = payload.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        offers = payload.get("offers", {})
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if not isinstance(offers, dict):
            offers = {}

        price = _parse_price(offers.get("price"))
        if price is None:
            for key in ("lowPrice", "highPrice", "listPrice"):
                if offers.get(key):
                    price = _parse_price(offers.get(key))
                    break
            if price is None:
                price = _parse_price(payload.get("price"))

        sku = payload.get("sku") or payload.get("mpn")
        if not sku:
            sku_match = re.search(r"--s(\d+)$", url)
            if sku_match:
                sku = sku_match.group(1)
        if not sku:
            return None

        image = payload.get("image")
        image_url = None
        if isinstance(image, list) and image:
            image_url = image[0]
        elif isinstance(image, str):
            image_url = image

        category = payload.get("category") or "grocery"
        category_path = None
        if isinstance(category, list):
            category_path = category
        elif category:
            category_path = [category]

        availability = offers.get("availability", "")
        in_stock = True
        if isinstance(availability, str):
            in_stock = "instock" in availability.lower()

        return {
            "sku": sku,
            "title": payload.get("name", ""),
            "price": price,
            "url": payload.get("url", url),
            "brand": brand,
            "image_url": image_url,
            "category": category,
            "category_path": category_path,
            "in_stock": in_stock,
            "source": "cooponline_vn",
            "merchant_id": "cooponline_vn",
            "raw_data": payload,
        }
    return None


def scrape_product(url: str) -> dict[str, Any] | None:
    html = fetch(url)
    if not html:
        return None
    return extract_product(html, url)


def scrape_products(urls: list[str]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    total = len(urls)
    done = 0
    print(f"Scraping {total} products with {MAX_WORKERS} workers", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(scrape_product, url): url for url in urls}
        for fut in as_completed(futures):
            done += 1
            try:
                product = fut.result()
            except Exception:
                product = None
            if product:
                products.append(product)
            if done % 100 == 0:
                print(f"  Progress: {done}/{total}", file=sys.stderr)
    print(f"Scraped {len(products)}/{total} product pages", file=sys.stderr)
    return products


def dedupe(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for product in products:
        key = str(product.get("sku") or product.get("url", ""))
        if key not in seen:
            seen[key] = product
    return list(seen.values())


def write_snapshot(products: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for product in products:
            file.write(json.dumps(product, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Co.op Online VN grocery ingestion")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "merchants" / "cooponline_vn_2026-06-19.ndjson",
    )
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--max-products", type=int, default=None)
    parser.add_argument("--max-sitemaps", type=int, default=None)
    args = parser.parse_args()

    if not args.skip_ingest:
        assert_ingestion_allowed()

    targets = configured_database_targets()
    print("Targets:", json.dumps(targets, indent=2), file=sys.stderr)

    product_urls = get_product_urls(max_sitemaps=args.max_sitemaps)
    print(f"Discovered product URLs: {len(product_urls)}", file=sys.stderr)
    if not product_urls:
        print(
            "FATAL: no product URLs discovered from Co.op sitemap source.",
            file=sys.stderr,
        )
        return 1

    urls = product_urls if args.max_products is None else product_urls[: args.max_products]
    products = scrape_products(urls)
    deduped = dedupe(products)
    print(f"Deduped: {len(deduped)}", file=sys.stderr)

    write_snapshot(deduped, args.output)
    print(f"Snapshot: {args.output}", file=sys.stderr)

    ingested = 0
    if not args.skip_ingest:
        ingested = upsert_products(
            deduped,
            source="cooponline_vn",
            merchant_id="cooponline_vn",
            defaults=MERCHANT_DEFAULTS,
            metadata_tag={"script": "ingest_cooponline_vn.py"},
        )
        print(f"Ingested: {ingested}", file=sys.stderr)

    result = {
        "merchant_id": "cooponline_vn",
        "sitemap_urls": len(product_urls),
        "scraped": len(products),
        "deduped": len(deduped),
        "ingested": ingested,
        "output": str(args.output),
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
