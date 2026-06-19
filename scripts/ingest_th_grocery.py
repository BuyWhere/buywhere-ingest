"""TH grocery merchant-direct ingestion runner for BUY-53269.

Runs Tops Online TH and Makro PRO TH scrapers, outputs JSONL products.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers import MakroProTHScraper, TopsTHScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("th_grocery_ingest")

OUTPUT_DIR = Path(__file__).parent.parent / "data"


def save_products(merchant_name: str, products: list) -> str:
    """Save products to JSONL and return the file path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{merchant_name.lower().replace(' ', '_')}_{timestamp}.ndjson"
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

async def run_makro() -> tuple:
    """Run Makro scraper and return (products, filepath)."""
    logger.info("=" * 60)
    logger.info("Starting Makro PRO TH scrape")
    logger.info("=" * 60)
    
    async with MakroProTHScraper() as scraper:
        products = await scraper.scrape()
    
    filepath = save_products("Makro PRO TH", products)
    logger.info(f"Makro PRO TH: {len(products)} products -> {filepath}")
    return products, filepath


async def run_tops() -> tuple:
    """Run Tops scraper and return (products, filepath)."""
    logger.info("=" * 60)
    logger.info("Starting Tops Online TH scrape")
    logger.info("=" * 60)
    
    scraper = TopsTHScraper()
    try:
        async with scraper:
            products = await scraper.scrape()
    finally:
        await scraper.close()
    
    filepath = save_products("Tops Online TH", products)
    logger.info(f"Tops Online TH: {len(products)} products -> {filepath}")
    return products, filepath


async def main():
    """Run both TH grocery scrapers."""
    logger.info("TH Grocery Ingestion Wave - BUY-53269")
    logger.info(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    
    # Run Makro first (accessible via HTTP, good baseline)
    makro_products, makro_path = await run_makro()
    
    # Then run Tops (Playwright-based, Cloudflare)
    tops_products, tops_path = await run_tops()
    
    total = len(makro_products) + len(tops_products)
    logger.info("=" * 60)
    logger.info(f"TH GROCERY INGESTION RESULTS")
    logger.info(f"  Makro PRO TH:  {len(makro_products):>6} products")
    logger.info(f"  Tops Online TH: {len(tops_products):>6} products")
    logger.info(f"  Total:          {total:>6} products")
    logger.info(f"  Makro file:     {makro_path}")
    logger.info(f"  Tops file:      {tops_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
