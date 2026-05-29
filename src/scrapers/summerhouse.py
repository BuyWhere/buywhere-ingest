"""Scraper for The Summerhouse (WooCommerce)."""

from typing import List
from .base_scraper import BaseScraper, Product

SUMMERHOUSE_BASE = "https://thesummerhouse.com.sg"


class SummerhouseScraper(BaseScraper):
    def __init__(self):
        super().__init__("The Summerhouse", SUMMERHOUSE_BASE)

    async def _scrape_impl(self, products: List[Product]) -> None:
        from bs4 import BeautifulSoup
        html = await self.fetch(f"{self.base_url}/shop/?page=1")
        if not html:
            return

        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select(".product, .product-item, .type-product"):
            name_elem = item.select_one("h2, h3, .woocommerce-loop-product__title")
            price_elem = item.select_one(".price, .amount")
            products.append(Product(
                name=self._clean_text(name_elem.get_text()) if name_elem else None,
                price=self._clean_text(price_elem.get_text()) if price_elem else None,
                url=item.select_one("a")["href"] if item.select_one("a") else None,
            ))
