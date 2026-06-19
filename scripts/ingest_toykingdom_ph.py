#!/usr/bin/env python3
"""Toy Kingdom Philippines ingestion runner for BUY-53324.

Runs the ToyKingdomPHScraper (Shopify products.json API) across all
product pages and outputs JSONL products for the PH toys lane.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.toykingdom_ph import ToyKingdomPHScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("toykingdom_ph_ingest")

OUTPUT_DIR = Path(__file__).parent.parent / "data"


def save_products(merchant_name: str, products: list) -> str:
    """Save products to JSONL and return the file path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"toykingdom_ph_{timestamp}.ndjson"
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
    """Run Toy Kingdom Philippines scraper and save products."""
    logger.info("=" * 60)
    logger.info("Toy Kingdom Philippines Ingestion - BUY-53324")
    logger.info(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    scraper = ToyKingdomPHScraper()
    async with scraper:
        products = await scraper.scrape()

    filepath = save_products("Toy Kingdom Philippines", products)
    logger.info(f"Total products: {len(products)}")
    logger.info(f"Output file: {filepath}")

    # Summary
    logger.info("=" * 60)
    logger.info("TOY KINGDOM PHILIPPINES INGESTION RESULTS")
    logger.info(f"  Products:     {len(products):>6}")
    logger.info(f"  Output:       {filepath}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
