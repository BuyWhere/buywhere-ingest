"""Scraper for Harvey Norman Singapore."""

import asyncio
from typing import List
from .base_scraper import BaseScraper, Product

HARVEY_NORMAN_SG_BASE = "https://www.harveynorman.com.sg"


class HarveyNormanSGScraper(BaseScraper):
    """Scraper for Harvey Norman Singapore."""

    def __init__(self):
        super().__init__("Harvey Norman SG", HARVEY_NORMAN_SG_BASE)
        self.search_url = f"{HARVEY_NORMAN_SG_BASE}/search"

    async def _scrape_impl(self, products: List[Product]) -> None:
        page = 1
        while True:
            url = f"{self.search_url}?q=*&page={page}"
            html = await self.fetch(url)
            if not html:
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select(".product-item, .product-card, .product-grid-item")
            if not items:
                break

            for item in items:
                name_elem = item.select_one(".product-name, .product-title, h2, h3")
                price_elem = item.select_one(".price, .product-price, .sales-price")

                product = Product(
                    name=self._clean_text(name_elem.get_text()) if name_elem else None,
                    price=self._clean_text(price_elem.get_text()) if price_elem else None,
                    url=item.select_one("a")["href"] if item.select_one("a") else None,
                )
                products.append(product)

            page += 1
            await asyncio.sleep(1)


async def main():
    async with HarveyNormanSGScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Harvey Norman SG: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
