"""Scraper for WooCommerce-based stores using product sitemap."""

import json
import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from .base_scraper import BaseScraper, Product

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class WooCommerceScraper(BaseScraper):
    """Scrape a bounded sample of WooCommerce store products from sitemap."""

    def __init__(self, base_url: str, max_products: int = 10):
        super().__init__("WooCommerce Store", base_url)
        self.max_products = max_products

    async def _scrape_impl(self, products: List[Product]) -> None:
        sitemap_xml = await self.fetch(f"{self.base_url}/wp-sitemap.xml")
        if not sitemap_xml:
            sitemap_xml = await self.fetch(f"{self.base_url}/sitemap.xml")
        if not sitemap_xml:
            return

        product_urls = self._extract_product_urls(sitemap_xml)
        for product_url in product_urls:
            if len(products) >= self.max_products:
                break
            if "/product/" not in product_url and "/shop/" not in product_url:
                continue

            product_html = await self.fetch(product_url)
            if not product_html:
                continue

            product = self._parse_product_page(product_html, product_url)
            if product:
                products.append(product)

    def _extract_product_urls(self, sitemap_xml: str) -> List[str]:
        try:
            root = ET.fromstring(sitemap_xml)
        except ET.ParseError:
            return []
        urls = []
        for loc in root.findall(".//sm:url/sm:loc", SITEMAP_NS):
            value = (loc.text or "").strip()
            if value:
                urls.append(value)
        if not urls:
            for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                value = (loc.text or "").strip()
                if value:
                    urls.append(value)
        return urls

    def _parse_product_page(self, html: str, url: str) -> Optional[Product]:
        payload = self._extract_product_json_ld(html)
        if not payload:
            return None

        offers = payload.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict) and "price" in offers:
            price = offers.get("price")
        else:
            price = None

        image = payload.get("image")
        if isinstance(image, list):
            image = image[0] if image else None

        brand = payload.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        category = payload.get("category")
        category_path = None
        if isinstance(category, str) and category:
            category_path = [category]
        elif isinstance(category, list) and category:
            category_path = [str(c) for c in category]

        return Product(
            name=self._clean_text(payload.get("name")),
            price=self._clean_text(str(price)) if price is not None else None,
            url=payload.get("url") or url,
            brand=self._clean_text(brand),
            image_url=image,
            sku=self._clean_text(payload.get("sku") or payload.get("gtin")),
            category=self._clean_text(category) if isinstance(category, str) else None,
            category_path=category_path,
            raw_data=payload,
        )

    def _extract_product_json_ld(self, html: str) -> Optional[dict]:
        patterns = [
            r'<script type="application/ld\+json"[^>]*>\s*(\{.*?"@type":"Product".*?\})\s*</script>',
            r'<script type="application/ld\+json"[^>]*>\s*(\{.*?\})\s*</script>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if not match:
                continue
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("@type") == "Product":
                return payload
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item
        return None