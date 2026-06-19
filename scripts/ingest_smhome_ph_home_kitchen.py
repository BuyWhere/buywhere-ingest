#!/usr/bin/env python3
"""Ingest a targeted SM Home Philippines home/kitchen slice via Shopify JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products


BASE_URL = "https://smhome.ph"
COLLECTIONS: dict[str, str] = {
    "pots-and-pans": "cookware",
    "coffee-and-espresso-makers": "coffee_maker",
    "specialty-food-appliances": "air_fryer",
    "toasters-and-ovens": "breakfast_maker",
}
MERCHANT_DEFAULTS = {
    "source": "smhome_ph",
    "merchant_id": "smhome_ph",
    "region": "PH",
    "country_code": "PH",
    "currency": "PHP",
    "platform": "shopify",
    "is_active": True,
    "in_stock": True,
}


def fetch_collection_products(slug: str) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"{BASE_URL}/collections/{slug}/products.json?limit=250&page={page}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        batch = payload.get("products") or []
        if not batch:
            break
        products.extend(batch)
        if len(batch) < 250:
            break
        page += 1
    return products


def normalize_product(product: dict[str, Any], collection_slug: str, lane_query: str) -> dict[str, Any]:
    variants = product.get("variants") or []
    if not variants:
        raise ValueError(f"Product {product.get('id')} has no variants")
    first_variant = variants[0]
    images = product.get("images") or []
    image_url = images[0].get("src") if images else None
    metadata = {
        "shopify_product_id": product.get("id"),
        "shopify_handle": product.get("handle"),
        "collection_slug": collection_slug,
        "lane_query": lane_query,
    }
    return {
        "title": product.get("title"),
        "price": first_variant.get("price"),
        "url": f"{BASE_URL}/products/{product.get('handle')}",
        "brand": product.get("vendor"),
        "image_url": image_url,
        "sku": first_variant.get("sku") or first_variant.get("barcode") or str(first_variant.get("id")),
        "category": product.get("product_type"),
        "category_path": [product.get("product_type")] if product.get("product_type") else None,
        "in_stock": first_variant.get("available"),
        "metadata": metadata,
        "raw_data": product,
        **MERCHANT_DEFAULTS,
    }


def dedupe_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for product in products:
        key = (product["sku"], product["url"])
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = product
            continue
        existing_meta = existing.setdefault("metadata", {})
        existing_meta.setdefault("collection_slugs", [existing_meta.get("collection_slug")])
        existing_meta.setdefault("lane_queries", [existing_meta.get("lane_query")])
        if product["metadata"]["collection_slug"] not in existing_meta["collection_slugs"]:
            existing_meta["collection_slugs"].append(product["metadata"]["collection_slug"])
        if product["metadata"]["lane_query"] not in existing_meta["lane_queries"]:
            existing_meta["lane_queries"].append(product["metadata"]["lane_query"])
    return list(deduped.values())


def write_snapshot(products: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for product in products:
            handle.write(json.dumps(product, ensure_ascii=False))
            handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "merchants" / "smhome_ph_home_kitchen_2026-06-19.ndjson",
        help="Optional NDJSON snapshot path.",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Fetch and snapshot only; do not write to the catalog DB.",
    )
    args = parser.parse_args()

    if not args.skip_ingest:
        assert_ingestion_allowed()

    configured_targets = configured_database_targets()
    print("Configured targets:", json.dumps(configured_targets, indent=2))

    collected: list[dict[str, Any]] = []
    coverage: dict[str, int] = {}
    for slug, lane_query in COLLECTIONS.items():
        batch = fetch_collection_products(slug)
        coverage[slug] = len(batch)
        print(f"{slug}: fetched {len(batch)} products")
        for product in batch:
            collected.append(normalize_product(product, slug, lane_query))

    deduped = dedupe_products(collected)
    print(f"Deduped to {len(deduped)} products across {len(COLLECTIONS)} collections")

    write_snapshot(deduped, args.output)
    print(f"Wrote snapshot: {args.output}")

    ingested = 0
    if not args.skip_ingest:
        ingested = upsert_products(
            deduped,
            source="smhome_ph",
            merchant_id="smhome_ph",
            defaults=MERCHANT_DEFAULTS,
            metadata_tag={
                "script": "ingest_smhome_ph_home_kitchen.py",
                "coverage": coverage,
            },
        )
        print(f"Ingested {ingested} products into catalog DB")

    print(
        json.dumps(
            {
                "merchant_id": "smhome_ph",
                "collections": coverage,
                "collected_products": len(collected),
                "deduped_products": len(deduped),
                "ingested_products": ingested,
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
