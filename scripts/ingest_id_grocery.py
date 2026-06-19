"""ID grocery merchant-direct ingestion runner for BUY-53271.

Runs Alfagift + Klik Indomaret scrapers, outputs JSONL products.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrapers import AlfagiftIDScraper, KlikIndomaretScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("id_grocery_ingest")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"


def save_products(merchant_name: str, products: list) -> str:
    """Save products to JSONL and return the file path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = merchant_name.lower().replace(" ", "_").replace(".", "")
    filename = f"{safe_name}_{timestamp}.ndjson"
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

async def run_alfagift() -> tuple:
    """Run Alfagift scraper and return (products, filepath)."""
    logger.info("=" * 60)
    logger.info("Starting Alfagift ID scrape")
    logger.info("=" * 60)

    scraper = AlfagiftIDScraper()
    try:
        async with scraper:
            products = await scraper.scrape()
    finally:
        await scraper.close()

    filepath = save_products("Alfagift ID", products)
    logger.info(f"Alfagift ID: {len(products)} products -> {filepath}")
    return products, filepath


async def run_klik_indomaret() -> tuple:
    """Run Klik Indomaret scraper and return (products, filepath)."""
    logger.info("=" * 60)
    logger.info("Starting Klik Indomaret ID scrape")
    logger.info("=" * 60)

    scraper = KlikIndomaretScraper()
    try:
        async with scraper:
            products = await scraper.scrape()
    finally:
        await scraper.close()

    filepath = save_products("Klik Indomaret", products)
    logger.info(f"Klik Indomaret: {len(products)} products -> {filepath}")
    return products, filepath


async def main():
    """Run both ID grocery scrapers."""
    logger.info("ID Grocery Ingestion Wave - BUY-53271")
    logger.info(f"Started at: {datetime.now(timezone.utc).isoformat()}")

    alfagift_products, alfagift_path = await run_alfagift()

    klik_products, klik_path = await run_klik_indomaret()

    total = len(alfagift_products) + len(klik_products)
    logger.info("=" * 60)
    logger.info("ID GROCERY INGESTION RESULTS")
    logger.info(f"  Alfagift ID:      {len(alfagift_products):>6} products")
    logger.info(f"  Klik Indomaret:   {len(klik_products):>6} products")
    logger.info(f"  Total:            {total:>6} products")
    logger.info(f"  Alfagift output:  {alfagift_path}")
    logger.info(f"  Klik output:      {klik_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
