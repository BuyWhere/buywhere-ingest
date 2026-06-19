#!/usr/bin/env python3
"""Toys"R"Us Thailand ingestion runner for BUY-53323.

Runs the ToysRUsTHScraper across all categories and outputs JSONL products.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.toysrus_th import ToysRUsTHScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("toysrus_th_ingest")

OUTPUT_DIR = Path(__file__).parent.parent / "data"


def save_products(merchant_name: str, products: list) -> str:
    """Save products to JSONL and return the file path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"toysrus_th_{timestamp}.ndjson"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w") as f:
        for product in products:
            record = {
                "name": product.name,
                "price": product.price,
                "url": product.url,
                "brand": product.brand,
                "image_url": product.image_url,
                "sku": product.sku,
                "category": product.category,
                "category_path": product.category_path,
                "in_stock": product.in_stock,
                "raw_data": product.raw_data,
                "merchant": merchant_name,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return str(filepath)


async def main():
    """Run ToysRUs Thailand scraper and save products."""
    logger.info("=" * 60)
    logger.info("Toys"R"Us Thailand Ingestion - BUY-53323")
    logger.info(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    scraper = ToysRUsTHScraper()
    async with scraper:
        products = await scraper.scrape()

    filepath = save_products("ToysRUs Thailand", products)
    logger.info(f"Total products: {len(products)}")
    logger.info(f"Output file: {filepath}")

    # Summary
    logger.info("=" * 60)
    logger.info(f"TOYS"R"US THAILAND INGESTION RESULTS")
    logger.info(f"  Products:     {len(products):>6}")
    logger.info(f"  Output:       {filepath}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
