"""Scraper for Shopify product detail pages to extract inventory/stock status."""

import asyncio
import json
import re
from typing import List, Optional

from .base_scraper import BaseScraper, Product


class ShopifyProductPageScraper(BaseScraper):
    """Scrape individual Shopify product pages for inventory data."""

    def __init__(self, base_url: str):
        merchant_name = base_url.replace("https://", "").replace("http://", "").split("/")[0]
        super().__init__(merchant_name, base_url)
        self.products: List[Product] = []

    async def scrape_products(self, product_handles: List[str]) -> List[Product]:
        """Scrape multiple product pages by handles."""
        self.products = []
        for handle in product_handles:
            url = f"{self.base_url}/products/{handle}"
            await self._scrape_product_page(url, handle)
            await asyncio.sleep(0.3)
        return self.products

    async def scrape_product(self, handle: str) -> Optional[Product]:
        """Scrape a single product page by handle."""
        url = f"{self.base_url}/products/{handle}"
        product = await self._fetch_and_parse_product(url, handle)
        return product

    async def _scrape_product_page(self, url: str, handle: str) -> None:
        product = await self._fetch_and_parse_product(url, handle)
        if product:
            self.products.append(product)

    async def _scrape_impl(self, products: List[Product]) -> None:
        """Required by ABC - use scrape_product(s) directly instead."""
        pass

    async def _fetch_and_parse_product(self, url: str, handle: str) -> Optional[Product]:
        html = await self.fetch(url)
        if not html:
            return None

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return None

        soup = BeautifulSoup(html, "html.parser")

        in_stock = self._parse_inventory_status(soup)
        price = self._parse_price(soup)
        name = self._parse_name(soup)
        sku = self._parse_sku(soup)
        image_url = self._parse_image(soup)

        return Product(
            name=name,
            price=price,
            url=url,
            sku=sku,
            image_url=image_url,
            in_stock=in_stock,
            raw_data={"handle": handle, "url": url},
        )

    def _parse_inventory_status(self, soup) -> Optional[bool]:
        """Parse inventory status from product page HTML."""
        scripts = soup.find_all("script")
        for script in scripts:
            if not script.string:
                continue
            if "product" in script.string.lower():
                try:
                    match = re.search(r'var\s+product\s*=\s*(\{.*?\});', script.string, re.DOTALL)
                    if match:
                        product_json = json.loads(match.group(1))
                        variants = product_json.get("variants", [])
                        if variants:
                            first_variant = variants[0]
                            available = first_variant.get("available")
                            if available is not None:
                                return bool(available)
                except (json.JSONDecodeError, KeyError):
                    continue

        in_stock_elem = soup.find(["span", "div", "p"], class_=re.compile(r"stock|inventory|availability", re.I))
        if in_stock_elem:
            text = in_stock_elem.get_text().lower()
            if "out of stock" in text or "sold out" in text or "unavailable" in text:
                return False
            if "in stock" in text or "available" in text:
                return True

        add_to_cart_btn = soup.find("button", string=re.compile(r"add to cart|add to basket", re.I))
        if add_to_cart_btn:
            disabled = add_to_cart_btn.get("disabled")
            if disabled:
                return False
            return True

        return None

    def _parse_price(self, soup) -> Optional[str]:
        """Parse price from product page."""
        price_elem = soup.find(["span", "div"], class_=re.compile(r"price", re.I))
        if price_elem:
            price_text = price_elem.get_text()
            match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
            if match:
                return match.group(0)
        return None

    def _parse_name(self, soup) -> Optional[str]:
        """Parse product name from page."""
        title_elem = soup.find("h1")
        if title_elem:
            return self._clean_text(title_elem.get_text())
        return None

    def _parse_sku(self, soup) -> Optional[str]:
        """Parse SKU from product page."""
        scripts = soup.find_all("script")
        for script in scripts:
            if not script.string:
                continue
            if "product" in script.string.lower():
                match = re.search(r'var\s+product\s*=\s*(\{.*?\});', script.string, re.DOTALL)
                if match:
                    try:
                        product_json = json.loads(match.group(1))
                        variants = product_json.get("variants", [])
                        if variants and variants[0].get("sku"):
                            return self._clean_text(variants[0].get("sku"))
                    except (json.JSONDecodeError, KeyError):
                        continue

        sku_elem = soup.find(["span", "div"], class_=re.compile(r"sku|article", re.I))
        if sku_elem:
            return self._clean_text(sku_elem.get_text())
        return None

    def _parse_image(self, soup) -> Optional[str]:
        """Parse main image URL from product page."""
        img_elem = soup.find("img", class_=re.compile(r"product|featured", re.I))
        if img_elem and img_elem.get("src"):
            return img_elem["src"]
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]
        return None
