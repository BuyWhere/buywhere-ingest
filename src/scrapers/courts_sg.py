"""Scraper for Courts Singapore."""

import asyncio
from typing import List, Optional
from .base_scraper import BaseScraper, Product

COURTS_SG_BASE = "https://www.courts.com.sg"


class CourtsSGScraper(BaseScraper):
    """Scraper for Courts Singapore."""

    def __init__(self):
        super().__init__("Courts SG", COURTS_SG_BASE)
        self.search_url = f"{COURTS_SG_BASE}/search"

    async def _scrape_impl(self, products: List[Product]) -> None:
        page = 1
        while True:
            url = f"{self.search_url}?q=*&page={page}"
            html = await self.fetch(url)
            if not html:
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select(".product-item")
            if not items:
                break

            for item in items:
                name_elem = item.select_one(".product-name, .product-title, h2, h3, .title")
                price_elem = item.select_one(".price, .product-price, .sale-price")

                product = Product(
                    name=self._clean_text(name_elem.get_text()) if name_elem else None,
                    price=self._clean_text(price_elem.get_text()) if price_elem else None,
                    url=item.select_one("a")["href"] if item.select_one("a") else None,
                )
                products.append(product)

            page += 1
            await asyncio.sleep(1)


async def main():
    async with CourtsSGScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Courts SG: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
