"""Scraper for FairPrice Singapore."""

import asyncio
from typing import List
from .base_scraper import BaseScraper, Product

FAIRPRICE_SG_BASE = "https://www.fairprice.com.sg"


class FairPriceScraper(BaseScraper):
    """Scraper for FairPrice Singapore."""

    def __init__(self):
        super().__init__("FairPrice", FAIRPRICE_SG_BASE)
        self.search_url = f"{FAIRPRICE_SG_BASE}/search"

    async def _scrape_impl(self, products: List[Product]) -> None:
        page = 1
        while True:
            url = f"{self.search_url}?query=*&page={page}"
            html = await self.fetch(url)
            if not html:
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select("[data-product-id], .product-item, .product-card")
            if not items:
                break

            for item in items:
                name_elem = item.select_one(".product-name, .product-title, h2, h3, [data-product-name]")
                price_elem = item.select_one(".price, .product-price, [data-product-price]")

                product = Product(
                    name=self._clean_text(name_elem.get_text()) if name_elem else None,
                    price=self._clean_text(price_elem.get_text()) if price_elem else None,
                    url=item.select_one("a")["href"] if item.select_one("a") else None,
                )
                products.append(product)

            page += 1
            await asyncio.sleep(1)


async def main():
    async with FairPriceScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"FairPrice: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
