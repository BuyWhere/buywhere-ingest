"""Scraper for Central Online Thailand home/kitchen products."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import List

from .base_scraper import BaseScraper, Product

_CT_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ingest_central_th_home_kitchen.py"


class CentralTHScraper(BaseScraper):
    """Scraper for Central Online Thailand home/kitchen."""

    def __init__(self, max_products: int = 500):
        super().__init__("Central Online TH", "https://www.central.co.th")
        self.max_products = max_products

    async def _scrape_impl(self, products: List[Product]) -> None:
        if not _CT_SCRIPT.exists():
            self.log.error("Central TH script not found")
            return
        result = subprocess.run(
            [sys.executable, str(_CT_SCRIPT), "--skip-ingest", f"--max-products={self.max_products}"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            self.log.error(f"Central TH script failed: {result.stderr[:500]}")
            return
        for line in result.stdout.strip().split("\n"):
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                snapshot = Path(data.get("output", ""))
                if snapshot.exists():
                    with open(snapshot) as f:
                        for pline in f:
                            pdata = json.loads(pline)
                            products.append(Product(
                                name=pdata.get("title", ""),
                                price=str(pdata.get("price", "")),
                                url=pdata.get("url", ""),
                                sku=str(pdata.get("sku", "")),
                                image_url=pdata.get("image_url", ""),
                                brand=pdata.get("brand", ""),
                                category=pdata.get("category", "home_kitchen"),
                                category_path=pdata.get("category_path"),
                                raw_data=pdata,
                            ))
                            if len(products) >= self.max_products:
                                return
                return


async def main():
    async with CentralTHScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Central Online TH: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
