#!/usr/bin/env python3
"""Ingest first 100 confirmed US Shopify merchants via /products.json."""
from __future__ import annotations
import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products
from src.scrapers.shopify_store import ShopifyScraper
VALIDATED_FILE = REPO_ROOT / 'data/us_shopify_validated.json'
MERCHANT_DEFAULTS = {'region': 'US', 'country_code': 'US', 'currency': 'USD', 'platform': 'shopify', 'is_active': True, 'in_stock': True}
def load_confirmed_merchants(limit=100):
    with open(VALIDATED_FILE) as f:
        data = json.load(f)
    confirmed = [r for r in data['results'] if r.get('signal') == 'products_json']
    return confirmed[:limit]
async def ingest_merchant(merchant, max_products=50):
    domain = merchant['domain']
    base_url = f'https://{domain}'
    merchant_id = domain.replace('.', '_')
    defaults = dict(MERCHANT_DEFAULTS, merchant_id=merchant_id)
    print(f'  [{domain}] scraping up to {max_products} products...')
    try:
        scraper = ShopifyScraper(base_url, max_products=max_products)
        async with scraper:
            products = await scraper.scrape()
        if not products:
            print(f'  [{domain}] no products found')
            return 0
        product_dicts = [asdict(p) for p in products]
        ingesting = upsert_products(product_dicts, defaults=defaults)
        print(f'  [{domain}] scraped {len(products)}, ingested {ingesting}')
        return ingesting
    except Exception as e:
        print(f'  [{domain}] FAILED: {e}')
        return 0
async def main():
    merchants = load_confirmed_merchants(100)
    print(f'Loading {len(merchants)} confirmed Shopify merchants...')
    total_ingested = 0
    successful = 0
    failed = 0
    for i, merchant in enumerate(merchants):
        print(f'[{i+1}/{len(merchants)}] {merchant["domain"]}')
        count = await ingest_merchant(merchant)
        if count > 0:
            successful += 1
            total_ingested += count
        else:
            failed += 1
        await asyncio.sleep(0.3)
    print(f'Done: {successful} merchants successful, {failed} failed, {total_ingested} products ingested')
if __name__ == '__main__':
    asyncio.run(main())
