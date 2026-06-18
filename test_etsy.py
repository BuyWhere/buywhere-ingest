#!/usr/bin/env python3
"""Test script for Etsy scraper."""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

# Import directly without __init__.py
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'scrapers'))

from etsy_us import EtsyUSScraper

async def main():
    async with EtsyUSScraper() as scraper:
        print('Starting Etsy US scraper...')
        products = await scraper.scrape()
        print(f'Scraped {len(products)} products')
        if products:
            print('First 5 products:')
            for i, p in enumerate(products[:5]):
                print(f'  {i+1}. {p.name} - ${p.price} - {p.category}')

        # Write to JSONL file
        with open('etsy_products.jsonl', 'w') as f:
            import json
            for p in products:
                f.write(json.dumps({
                    'name': p.name,
                    'price': p.price,
                    'url': p.url,
                    'brand': p.brand,
                    'image_url': p.image_url,
                    'category': p.category,
                    'category_path': p.category_path,
                    'raw_data': p.raw_data
                }) + '\n')
        print(f'Products saved to etsy_products.jsonl')

if __name__ == "__main__":
    asyncio.run(main())