"""Scraper for Shopify-based stores using the /products.json API endpoint."""

import asyncio
import json
from typing import List, Optional

from .base_scraper import BaseScraper, Product


class ShopifyScraper(BaseScraper):
    """Scrape a Shopify store products from /products.json with pagination."""

    def __init__(self, base_url: str, max_products: int = 100):
        merchant_name = base_url.replace("https://", "").replace("http://", "").split("/")[0]
        super().__init__(merchant_name, base_url)
        self.max_products = max_products

    async def _scrape_impl(self, products: List[Product]) -> None:
        page = 1
        while len(products) < self.max_products:
            url = f"{self.base_url}/products.json?limit=250&page={page}"
            data = await self._fetch_products(url)
            if not data or not data.get("products"):
                break
            for product_data in data["products"]:
                if len(products) >= self.max_products:
                    break
                product = self._parse_product(product_data)
                if product:
                    products.append(product)
            if len(data["products"]) < 250:
                break
            page += 1
            await asyncio.sleep(0.5)

    async def _fetch_products(self, url: str) -> Optional[dict]:
        response = await self.fetch(url)
        if not response:
            return None
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return None

    def _parse_product(self, data: dict) -> Optional[Product]:
        if not data.get("variants"):
            return None
        first_variant = data["variants"][0]
        images = data.get("images", [])
        image_url = images[0].get("src") if images else None
        return Product(
            name=self._clean_text(data.get("title")),
            price=self._clean_text(str(first_variant.get("price"))) if first_variant.get("price") else None,
            url=f"{self.base_url}/products/{data.get('handle')}",
            brand=self._clean_text(data.get("vendor")),
            image_url=image_url,
            sku=self._clean_text(first_variant.get("sku") or first_variant.get("barcode") or str(first_variant.get("id", ""))),
            category=self._clean_text(data.get("product_type")),
            category_path=[self._clean_text(data.get("product_type"))] if data.get("product_type") else None,
            raw_data=data,
        )
