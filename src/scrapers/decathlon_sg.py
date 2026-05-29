"""Scraper for Decathlon Singapore."""

import asyncio
from typing import List
from .base_scraper import BaseScraper, Product

DECATHLON_SG_BASE = "https://www.decathlon.com.sg"


class DecathlonSGScraper(BaseScraper):
    """Scraper for Decathlon Singapore."""

    def __init__(self):
        super().__init__("Decathlon SG", DECATHLON_SG_BASE)
        self.search_url = f"{DECATHLON_SG_BASE}/search"

    async def _scrape_impl(self, products: List[Product]) -> None:
        page = 1
        while True:
            url = f"{self.search_url}?q=*&page={page}"
            html = await self.fetch(url)
            if not html:
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select("[data-product-id], .product-item, .product-card, .product")
            if not items:
                break

            for item in items:
                name_elem = item.select_one(".product-title, .product-name, h2, h3, .title, [data-product-name]")
                price_elem = item.select_one(".price, .product-price, .current-price, [data-product-price]")

                product = Product(
                    name=self._clean_text(name_elem.get_text()) if name_elem else None,
                    price=self._clean_text(price_elem.get_text()) if price_elem else None,
                    url=item.select_one("a")["href"] if item.select_one("a") else None,
                )
                products.append(product)

            page += 1
            await asyncio.sleep(1)


async def main():
    async with DecathlonSGScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Decathlon SG: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
