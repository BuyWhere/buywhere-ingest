#!/usr/bin/env python3
"""Retry failed Shopify merchants that had duplicate SKU issues."""
from __future__ import annotations
import asyncio
import sys
from dataclasses import asdict
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from src.catalog_ingest import upsert_products
from src.scrapers.shopify_store import ShopifyScraper

FAILED = [
    'naturium.com', 'dermalogica.com', 'soldejaneiro.com',
    'glowrecipe.com', 'sugarcosmetics.com', 'plumgoodness.com',
    'masterdynamic.com', 'mezeaudio.com', 'vertagear.com',
]

MERCHANT_DEFAULTS = {'region': 'US', 'country_code': 'US', 'currency': 'USD', 'platform': 'shopify', 'is_active': True, 'in_stock': True}

async def ingest_merchant(domain, max_products=50):
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
        # Deduplicate by SKU within the batch
        seen_skus = set()
        deduped = []
        for pd in product_dicts:
            sku = str(pd.get("sku", ""))
            if sku and sku not in seen_skus:
                seen_skus.add(sku)
                deduped.append(pd)
        if len(deduped) < len(product_dicts):
            print(f'  [{domain}] deduped {len(product_dicts)} -> {len(deduped)} products')
        ingesting = upsert_products(deduped, defaults=defaults)
        print(f'  [{domain}] scraped {len(products)}, deduped {len(deduped)}, ingested {ingesting}')
        return ingesting
    except Exception as e:
        print(f'  [{domain}] FAILED: {e}')
        return 0

async def main():
    print(f'Retrying {len(FAILED)} failed merchants...')
    results = {}
    for i, domain in enumerate(FAILED):
        print(f'[{i+1}/{len(FAILED)}] {domain}')
        count = await ingest_merchant(domain)
        results[domain] = count
        await asyncio.sleep(0.3)
    
    successful = sum(1 for v in results.values() if v > 0)
    total = sum(results.values())
    print(f'Retry done: {successful}/{len(FAILED)} succeeded, {total} products ingested')

if __name__ == '__main__':
    asyncio.run(main())
