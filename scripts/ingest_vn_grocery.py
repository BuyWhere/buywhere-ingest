"""VN grocery ingestion runner for Bách hoá XANH + Co.op Online."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers import BachHoaXanhVNScraper, CoopOnlineVNScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vn_grocery_ingest")

OUTPUT_DIR = Path(__file__).parent.parent / "data"


def save_products(merchant_name: str, products: list) -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{merchant_name.lower().replace(' ', '_')}_{timestamp}.ndjson"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w") as handle:
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
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(filepath)


async def run_bach(max_products: int | None) -> tuple[list, str]:
    logger.info("=" * 60)
    logger.info("Starting BACH HOA XANH VN scrape")
    logger.info("=" * 60)
    kwargs = {"max_products": max_products} if max_products else {}
    async with BachHoaXanhVNScraper(**kwargs) as scraper:
        products = await scraper.scrape()
    filepath = save_products("Bach Hoa Xanh VN", products)
    logger.info(f"Bach Hoa Xanh VN: {len(products)} products -> {filepath}")
    return products, filepath


async def run_coop(max_products: int | None) -> tuple[list, str]:
    logger.info("=" * 60)
    logger.info("Starting CO.OP ONLINE VN scrape")
    logger.info("=" * 60)
    kwargs = {"max_products": max_products} if max_products else {}
    async with CoopOnlineVNScraper(**kwargs) as scraper:
        products = await scraper.scrape()
    filepath = save_products("Coop Online VN", products)
    logger.info(f"Coop Online VN: {len(products)} products -> {filepath}")
    return products, filepath


async def main() -> int:
    parser = argparse.ArgumentParser(description="VN grocery ingestion wave")
    parser.add_argument("--max-products", type=int, default=None)
    args = parser.parse_args()
    logger.info("VN Grocery Ingestion Wave - BUY-53272")
    logger.info(f"Started at: {datetime.now(timezone.utc).isoformat()}")

    bach_products, bach_path = await run_bach(args.max_products)
    coop_products, coop_path = await run_coop(args.max_products)

    total = len(bach_products) + len(coop_products)
    logger.info("=" * 60)
    logger.info("VN GROCERY INGESTION RESULTS")
    logger.info(f"  Bach Hoa Xanh VN: {len(bach_products):>6} products")
    logger.info(f"  Co.op Online VN:   {len(coop_products):>6} products")
    logger.info(f"  Total:             {total:>6} products")
    logger.info(f"  Bach output:       {bach_path}")
    logger.info(f"  Coop output:       {coop_path}")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
