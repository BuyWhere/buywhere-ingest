"""Runner script to scrape all SG merchants and report product counts."""

import asyncio
import json
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers import SCRAPERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_all_scrapers():
    """Run all scrapers and report product counts."""
    results = {}

    for name, scraper_class in SCRAPERS.items():
        try:
            async with scraper_class() as scraper:
                logger.info(f"Scraping {scraper.merchant_name}...")
                products = await scraper.scrape()
                results[scraper.merchant_name] = {
                    "count": len(products),
                    "status": "success",
                }
                logger.info(f"{scraper.merchant_name}: {len(products)} products")
        except Exception as e:
            logger.error(f"{name} failed: {e}")
            results[name] = {
                "count": 0,
                "status": "failed",
                "error": str(e),
            }

    return results


async def main():
    results = await run_all_scrapers()

    print("\n" + "=" * 60)
    print("SCRAPER RESULTS")
    print("=" * 60)
    for name, result in sorted(results.items(), key=lambda x: x[1]["count"], reverse=True):
        status = "OK" if result["status"] == "success" else "FAIL"
        print(f"{result.get('merchant_name', name):<30} {result['count']:>6} products [{status}]")
    print("=" * 60)

    output_file = Path(__file__).parent.parent / "docs" / "scraper-results.md"
    with open(output_file, "w") as f:
        f.write("# Scraper Results\n\n")
        f.write("| Merchant | Product Count | Status |\n")
        f.write("|----------|---------------|--------|\n")
        for name, result in sorted(results.items(), key=lambda x: x[1]["count"], reverse=True):
            status = "OK" if result["status"] == "success" else "FAIL"
            f.write(f"| {result.get('merchant_name', name)} | {result['count']} | {status} |\n")

    print(f"\nResults written to {output_file}")
    return results


if __name__ == "__main__":
    asyncio.run(main())
