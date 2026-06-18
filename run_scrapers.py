"""Runner script to scrape all SG merchants and report product counts."""

import asyncio
import json
import os
import sys
import logging
import argparse
from pathlib import Path

# Ensure Playwright system deps are on the library path (BUY-37375)
_pw_deps = "/home/paperclip/playwright-deps/lib"
if _pw_deps not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = f"{_pw_deps}:{os.environ.get('LD_LIBRARY_PATH', '')}"

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


async def run_cycle(cycle_number):
    """Run a single scraping cycle and return results."""
    logger.info(f"Starting cycle {cycle_number}")
    results = await run_all_scrapers()

    # Print results to stdout
    print("\n" + "=" * 60)
    print(f"SCRAPER RESULTS - Cycle {cycle_number}")
    print("=" * 60)
    for name, result in sorted(results.items(), key=lambda x: x[1]["count"], reverse=True):
        status = "OK" if result["status"] == "success" else "FAIL"
        print(f"{result.get('merchant_name', name):<30} {result['count']:>6} products [{status}]")
    print("=" * 60)

    # Write JSONL output to data directory
    jsonl_dir = Path(__file__).parent.parent / "data"
    jsonl_dir.mkdir(exist_ok=True)
    jsonl_file = jsonl_dir / f"carousell_sg_cycle_{cycle_number}.jsonl"

    # Write each merchant's result as a separate JSON line
    for name, result in results.items():
        entry = {
            "cycle": cycle_number,
            "timestamp": asyncio.get_event_loop().time(),
            "merchant": result.get("merchant_name", name),
            "product_count": result["count"],
            "status": result["status"]
        }
        if result["status"] == "failed":
            entry["error"] = result.get("error", "Unknown error")

        with open(jsonl_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    logger.info(f"Cycle {cycle_number} completed. Results saved to {jsonl_file}")
    return results

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Carousell SG Scrapers Runner")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--refresh-interval", type=int, default=3600, help="Refresh interval in seconds")
    args = parser.parse_args()

    cycle_number = 1

    if args.continuous:
        logger.info(f"Running in continuous mode with {args.refresh_interval}s interval")
        while True:
            await run_cycle(cycle_number)
            logger.info(f"Waiting {args.refresh_interval} seconds before next cycle...")
            await asyncio.sleep(args.refresh_interval)
            cycle_number += 1
    else:
        # Single run mode
        await run_cycle(cycle_number)


if __name__ == "__main__":
    asyncio.run(main())
