"""Scraper for Floor & Decor using product sitemap pages."""

import json
import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from .base_scraper import BaseScraper, Product

FLOOR_AND_DECOR_BASE = "https://www.flooranddecor.com"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class FloorAndDecorScraper(BaseScraper):
    """Scrape a bounded sample of Floor & Decor product pages from the PDP sitemap."""

    def __init__(self, max_products: int = 10):
        super().__init__("Floor & Decor", FLOOR_AND_DECOR_BASE)
        self.max_products = max_products

    async def _scrape_impl(self, products: List[Product]) -> None:
        sitemap_xml = await self.fetch(f"{self.base_url}/sitemap-PDP.xml")
        if not sitemap_xml:
            return

        for product_url in self._extract_urls(sitemap_xml):
            if len(products) >= self.max_products:
                break

            product_html = await self.fetch(product_url)
            if not product_html:
                continue

            product = self._parse_product_page(product_html)
            if product:
                products.append(product)

    def _extract_urls(self, sitemap_xml: str) -> List[str]:
        root = ET.fromstring(sitemap_xml)
        urls = []
        for loc in root.findall(".//sm:url/sm:loc", SITEMAP_NS):
            value = (loc.text or "").strip()
            if value:
                urls.append(value)
        return urls

    def _parse_product_page(self, html: str) -> Optional[Product]:
        payload = self._extract_product_json_ld(html)
        if not payload:
            return None

        image = payload.get("image")
        if isinstance(image, list):
            image = image[0] if image else None

        return Product(
            name=self._clean_text(payload.get("name")),
            price=self._clean_text(str((payload.get("offers") or {}).get("price"))) if (payload.get("offers") or {}).get("price") is not None else None,
            url=payload.get("url"),
            brand=self._clean_text(payload.get("brand")),
            image_url=image,
            sku=self._clean_text(payload.get("sku") or payload.get("gtin")),
            category=None,
            category_path=None,
            raw_data=payload,
        )

    def _extract_product_json_ld(self, html: str) -> Optional[dict]:
        match = re.search(
            r'<script type="application/ld\+json">\s*(\{"@context":"https://schema\.org/".*?"@type":"Product".*?\})\s*</script>',
            html,
            re.DOTALL,
        )
        if not match:
            return None

        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

        if payload.get("@type") != "Product":
            return None

        brand = payload.get("brand")
        if isinstance(brand, dict):
            payload["brand"] = brand.get("name")
        return payload
