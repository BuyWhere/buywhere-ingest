"""Scraper for Nguyen Kim Vietnam home/kitchen products."""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import List

from .base_scraper import BaseScraper, Product

_NK_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ingest_nguyen_kim_vn_home_kitchen.py"


class NguyenKimVNScraper(BaseScraper):
    """Scraper for Nguyen Kim Vietnam home/kitchen."""

    def __init__(self, max_products: int = 500):
        super().__init__("Nguyen Kim VN", "https://www.nguyenkim.com")
        self.max_products = max_products

    async def _scrape_impl(self, products: List[Product]) -> None:
        """Defer to the ingest script."""
        if not _NK_SCRIPT.exists():
            return
        import subprocess
        result = subprocess.run(
            [sys.executable, str(_NK_SCRIPT), "--skip-ingest"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return
        for line in result.stdout.strip().split("\n"):
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # result JSON only, actual products are in the ndjson snapshot
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
                                category=pdata.get("category", ""),
                                category_path=pdata.get("category_path"),
                                raw_data=pdata,
                            ))
                            if len(products) >= self.max_products:
                                return
                return


async def main():
    async with NguyenKimVNScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Nguyen Kim VN: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
