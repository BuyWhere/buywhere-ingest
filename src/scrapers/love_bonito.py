"""Scraper for Love Bonito Singapore."""

from typing import List
from .base_scraper import BaseScraper, Product

LOVE_BONITO_BASE = "https://www.lovebonito.com"


class LoveBonitoScraper(BaseScraper):
    def __init__(self):
        super().__init__("Love Bonito", LOVE_BONITO_BASE)

    async def _scrape_impl(self, products: List[Product]) -> None:
        from bs4 import BeautifulSoup
        html = await self.fetch(f"{self.base_url}/search?q=*&page=1")
        if not html:
            return

        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select(".product-item, .product-card"):
            products.append(Product(
                name=self._clean_text(item.select_one("h2, h3, .name") and item.select_one("h2, h3, .name").get_text()),
                price=self._clean_text(item.select_one(".price") and item.select_one(".price").get_text()),
                url=item.select_one("a")["href"] if item.select_one("a") else None,
            ))
