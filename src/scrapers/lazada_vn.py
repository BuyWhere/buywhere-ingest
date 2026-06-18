"""Scraper for Lazada Vietnam marketplace."""

import asyncio
import json
import re
import logging
from typing import List, Optional
from urllib.parse import urljoin, quote
from .base_scraper import BaseScraper, Product

LAZADA_VN_BASE = "https://www.lazada.vn"
logger = logging.getLogger(__name__)


class LazadaVNScraper(BaseScraper):
    """Scraper for Lazada Vietnam marketplace."""

    def __init__(self, max_products: int = 50):
        super().__init__("Lazada VN", LAZADA_VN_BASE)
        self.max_products = max_products

    async def _scrape_impl(self, products: List[Product]) -> None:
        page = 1
        seen_urls = set()
        while len(products) < self.max_products:
            search_url = f"{self.base_url}/catalog/search?q=*&page={page}"
            html = await self.fetch(search_url)
            if not html:
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select("[data-sku], .product-item, .goods-item")
            if not items:
                if page > 3:
                    break
                page += 1
                continue

            for item in items:
                if len(products) >= self.max_products:
                    break

                name_elem = item.select_one(".product-title, .goods-title, h3, [data-sku-name]")
                price_elem = item.select_one(".price, .product-price, .sale-price")
                link_elem = item.select_one("a")
                image_elem = item.select_one("img")
                sku_elem = item.select_one("[data-sku]")

                product_url = None
                if link_elem:
                    href = link_elem.get("href", "")
                    if href:
                        product_url = urljoin(self.base_url, href.split("?")[0].rstrip("/"))

                if product_url and product_url in seen_urls:
                    continue
                if product_url:
                    seen_urls.add(product_url)

                sku = None
                if sku_elem:
                    sku = sku_elem.get("data-sku") or sku_elem.get("data-product-id")

                price_text = None
                if price_elem:
                    price_text = self._clean_text(price_elem.get_text())
                    price_match = re.search(r"[\d,]+\.?\d*", price_text.replace("₫", "").replace(",", ""))
                    if price_match:
                        price_text = price_match.group(0)

                image_url = None
                if image_elem:
                    image_url = image_elem.get("src") or image_elem.get("data-src")

                product = Product(
                    name=self._clean_text(name_elem.get_text()) if name_elem else None,
                    price=price_text,
                    url=product_url,
                    sku=sku,
                    image_url=image_url,
                )
                products.append(product)

            page += 1
            if page > 10:
                break
            await asyncio.sleep(0.5)


async def main():
    async with LazadaVNScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Lazada VN: {count} products")


if __name__ == "__main__":
    asyncio.run(main())