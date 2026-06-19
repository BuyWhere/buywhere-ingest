"""Scraper for Co.op Online Vietnam grocery products."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import List

from .base_scraper import BaseScraper, Product

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ingest_cooponline_vn.py"


class CoopOnlineVNScraper(BaseScraper):
    """Scraper for Co.op Online Vietnam."""

    def __init__(self, max_products: int = 500):
        super().__init__("Co.op Online VN", "https://cooponline.vn")
        self.max_products = max_products

    async def _scrape_impl(self, products: List[Product]) -> None:
        if not _SCRIPT.exists():
            return

        cmd = [sys.executable, str(_SCRIPT), "--skip-ingest"]
        if self.max_products:
            cmd.extend(["--max-products", str(self.max_products)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            return

        for line in result.stdout.strip().split("\n"):
            if not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            snapshot = Path(data.get("output", ""))
            if not snapshot.exists():
                continue
            with snapshot.open() as handle:
                for pline in handle:
                    product_data = json.loads(pline)
                    products.append(
                        Product(
                            name=product_data.get("title", ""),
                            price=str(product_data.get("price", "")),
                            url=product_data.get("url", ""),
                            sku=str(product_data.get("sku", "")),
                            image_url=product_data.get("image_url", ""),
                            brand=product_data.get("brand", ""),
                            category=product_data.get("category", ""),
                            category_path=product_data.get("category_path"),
                            in_stock=product_data.get("in_stock"),
                            raw_data=product_data,
                        )
                    )
                    if len(products) >= self.max_products:
                        return
