#!/usr/bin/env python3
"""Central Online TH home/kitchen via Algolia API."""
from __future__ import annotations
import argparse, asyncio, json, os, sys, time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products

AID = "JL22XXDCS9"
AKEY = "219108856fc945a087d091aebc7eebbb"
AURL = f"https://{AID}-dsn.algolia.net/1/indexes/cds_products/query"

MDEF = {"source":"central_th","merchant_id":"central_th","region":"TH","country_code":"TH","currency":"THB","platform":"nextjs","is_active":True,"in_stock":True}
HDRS = {"X-Algolia-Application-Id":AID,"X-Algolia-API-Key":AKEY,"Content-Type":"application/json"}
BSIZE = 1000

def build_product(hit):
    name = hit.get("name_th") or hit.get("name_en", "")
    price = hit.get("final_price")
    sku = hit.get("sku")
    if not name or not sku:
        return None
    brand = hit.get("brand_name")
    img = hit.get("image_url") or hit.get("thumbnail_url")
    url_key = hit.get("url_key", "")
    full_url = f"https://www.central.co.th/th/{url_key}" if url_key else ""
    cat_th = hit.get("category_th", {}) or {}
    cat_path = []
    for lvl in ["level0", "level1", "level2", "level3"]:
        vals = cat_th.get(lvl, [])
        for v in vals:
            cat_path.append(v.replace(" /// ", " > "))
        if vals:
            break
    return {
        "title": name,
        "price": str(price) if price is not None else None,
        "url": full_url,
        "brand": brand,
        "image_url": img,
        "sku": sku,
        "category": cat_path[-1] if cat_path else "home_kitchen",
        "category_path": cat_path or ["home_kitchen"],
        "in_stock": True,
        "currency": "THB",
        "raw_data": {"sku": sku, "brand": brand, "price": price},
        **MDEF,
    }
def dedupe(products):
    seen = {}
    for product in products:
        key = (str(product.get("sku","")), str(product.get("url","")))
        if key not in seen: seen[key] = product
    return list(seen.values())

def write_snapshot(products, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for product in products:
            f.write(json.dumps(product, ensure_ascii=False) + "\n")
async def fetch_page(client, filters, page):
    attrs = "name_th,name_en,sku,brand_name,final_price,url_key,image_url,thumbnail_url,category_th,category_en,category_uids"
    params = f"query=&hitsPerPage={1000}&page={page}&filters={filters}&attributesToRetrieve={attrs}"
    resp = await client.post(AURL, json={"params": params})
    resp.raise_for_status()
    return resp.json()

async def scrape_cat(client, filters, name, limit=None):
    products = []
    page = 0
    total = None
    while True:
        data = await fetch_page(client, filters, page)
        if total is None:
            total = data.get("nbHits", 0)
            print(f"  {name}: {total} total", flush=True)
        hits = data.get("hits", [])
        if not hits: break
        for h in hits:
            prod = build_product(h)
            if prod: products.append(prod)
        if limit and len(products) >= limit:
            products = products[:limit]
            break
        if len(hits) < 1000: break
        page += 1
    print(f"  {name}: scraped {len(products)}", flush=True)
    return products
async def main():
    parser = argparse.ArgumentParser(description="Central TH home/kitchen via Algolia")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "merchants" / f"central_th_home_kitchen_{time.strftime('%Y-%m-%d')}.ndjson")
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--max-products", type=int, default=1000, help="Per category")
    parser.add_argument("--max-total", type=int, default=None, help="Total")
    args = parser.parse_args()
    if not args.skip_ingest:
        assert_ingestion_allowed()
    targets = configured_database_targets()
    print("Targets:", json.dumps(targets, indent=2), file=sys.stderr)
    print("=" * 60, flush=True)

    import httpx
    async with httpx.AsyncClient(timeout=30, headers=HDRS) as client:
        filters = [
            ("home_appliances", "category_uids:0005"),
            ("home_lifestyle", "category_uids:0006"),
        ]
        all_products = []
        start = time.time()
        for name, filt in filters:
            if args.max_total and len(all_products) >= args.max_total:
                break
            rem = min(args.max_products, (args.max_total - len(all_products))) if args.max_total else args.max_products
            products = await scrape_cat(client, filt, name, limit=rem)
            all_products.extend(products)
        elapsed = time.time() - start
        print(f"\nTotal: {len(all_products)} in {elapsed:.1f}s", flush=True)

    deduped = dedupe(all_products)
    print(f"Deduped: {len(deduped)}")
    write_snapshot(deduped, args.output)

    ingested = 0
    if not args.skip_ingest and deduped:
        ingested = upsert_products(deduped, source="central_th", merchant_id="central_th", defaults=MDEF,
                                   metadata_tag={"script": "ingest_central_th_home_kitchen.py"})
        print(f"Ingested: {ingested}", flush=True)

    result = {"merchant_id":"central_th","products_scraped":len(all_products),"deduped":len(deduped),"ingested":ingested,"elapsed":round(elapsed,1),"output":str(args.output)}
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
