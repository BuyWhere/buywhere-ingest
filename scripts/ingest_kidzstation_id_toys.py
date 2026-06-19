#!/usr/bin/env python3
"""Ingest Kidz Station Indonesia toys products via Shopify products.json API.

Kidz Station (www.kidzstation.co.id) is a Shopify-based toy retailer
carrying LEGO, NERF, Play-Doh, Transformers, and other toy brands.
This script:
1. Fetches all products via /collections/all/products.json paginated API
2. Filters for toys category (product_type == "Toys")
3. Extracts SKU, title, price, images, brand, category
4. Deduplicates and snapshots to NDJSON, then upserts to catalog DB.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products

BASE_URL = "https://www.kidzstation.co.id"
MERCHANT_DEFAULTS = {
    "source": "kidzstation_id",
    "merchant_id": "kidzstation_id",
    "region": "ID",
    "country_code": "ID",
    "currency": "IDR",
    "platform": "shopify",
    "is_active": True,
    "in_stock": True,
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}
TIMEOUT = 30

def fetch_json(url: str) -> dict | None:
    """Fetch a JSON endpoint with retries."""
    for attempt in range(3):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            if attempt < 2:
                time.sleep(2)
    return None


def fetch_all_products() -> list[dict]:
    """Fetch all products via paginated products.json API."""
    products: list[dict] = []
    page = 1
    while True:
        url = f"{BASE_URL}/collections/all/products.json?limit=250&page={page}"
        data = fetch_json(url)
        if not data:
            break
        batch = data.get("products", [])
        if not batch:
            break
        products.extend(batch)
        print(f"  Page {page}: {len(batch)} products (total {len(products)})",
              file=sys.stderr)
        if len(batch) < 250:
            break
        page += 1
        time.sleep(0.3)
    print(f"Fetched {len(products)} total products from API", file=sys.stderr)
    return products

def parse_product(p: dict) -> dict[str, Any] | None:
    """Parse a single product from the Shopify products.json API response."""
    if not p.get("variants"):
        return None
    first_variant = p["variants"][0]
    images = p.get("images", [])
    image_url = images[0].get("src") if images else None
    sku = (first_variant.get("sku")
           or first_variant.get("barcode")
           or str(first_variant.get("id", "")))
    title = p.get("title", "")
    vendor = p.get("vendor", "")
    product_type = p.get("product_type", "")
    price = first_variant.get("price")
    # The product may have no explicit price string
    if price is not None:
        price = str(price)
    return {
        "sku": sku,
        "title": title,
        "price": price,
        "url": f"{BASE_URL}/products/{p.get('handle')}",
        "brand": vendor,
        "image_url": image_url,
        "category": product_type if product_type else "Toys",
        "category_path": [product_type] if product_type else ["Toys"],
        "in_stock": first_variant.get("available", True),
        "source": "kidzstation_id",
        "merchant_id": "kidzstation_id",
    }


def dedupe(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by SKU."""
    seen: dict[str, dict[str, Any]] = {}
    for pr in products:
        key = pr["sku"]
        if key not in seen:
            seen[key] = pr
        elif not seen[key].get("title") and pr.get("title"):
            seen[key] = pr
    return list(seen.values())


def write_snapshot(products: list[dict[str, Any]], path: Path) -> None:
    """Write products as NDJSON snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for pr in products:
            f.write(json.dumps(pr, ensure_ascii=False) + "\n")

def main() -> int:
    today = time.strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(
        description="Kidz Station Indonesia toys ingestion")
    parser.add_argument(
        "--output", type=Path,
        default=REPO_ROOT / "merchants"
                 / f"kidzstation_id_toys_{today}.ndjson")
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument(
        "--max-products", type=int, default=None,
        help="Limit total products (for testing)")
    args = parser.parse_args()

    if not args.skip_ingest:
        assert_ingestion_allowed()

    targets = configured_database_targets()
    print("Targets:", json.dumps(targets, indent=2), file=sys.stderr)

    # Step 1: Fetch all products from Shopify API
    raw_products = fetch_all_products()
    print(f"API returned {len(raw_products)} products", file=sys.stderr)

    # Step 2: Parse into our format
    parsed = []
    for p in raw_products:
        parsed_p = parse_product(p)
        if parsed_p:
            parsed.append(parsed_p)
    print(f"Parsed: {len(parsed)} products", file=sys.stderr)

    # Step 3: Limit if requested
    if args.max_products and len(parsed) > args.max_products:
        parsed = parsed[:args.max_products]
        print(f"Limited to {args.max_products}", file=sys.stderr)

    # Step 4: Deduplicate
    deduped = dedupe(parsed)
    print(f"Deduped: {len(deduped)}", file=sys.stderr)

    # Step 5: Write snapshot
    write_snapshot(deduped, args.output)
    print(f"Snapshot: {args.output}", file=sys.stderr)

    # Step 6: Ingest to catalog DB
    ingested = 0
    if not args.skip_ingest:
        ingested = upsert_products(
            deduped,
            source="kidzstation_id",
            merchant_id="kidzstation_id",
            defaults=MERCHANT_DEFAULTS,
            metadata_tag={"script": "ingest_kidzstation_id_toys.py"},
        )
        print(f"Ingested: {ingested}", file=sys.stderr)

    result = {
        "merchant_id": "kidzstation_id",
        "api_products": len(raw_products),
        "parsed": len(parsed),
        "deduped": len(deduped),
        "ingested": ingested,
        "output": str(args.output),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
