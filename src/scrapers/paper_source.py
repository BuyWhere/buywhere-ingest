"""Scraper for Paper Source using public product sitemaps."""

import json
import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from .base_scraper import BaseScraper, Product

PAPER_SOURCE_BASE = "https://www.papersource.com"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class PaperSourceScraper(BaseScraper):
    """Scrape a bounded sample of Paper Source products from sitemap-linked pages."""

    def __init__(self, max_products: int = 20):
        super().__init__("Paper Source", PAPER_SOURCE_BASE)
        self.max_products = max_products

    async def _scrape_impl(self, products: List[Product]) -> None:
        sitemap_index = await self.fetch(f"{self.base_url}/sitemap.xml")
        if not sitemap_index:
            return

        product_sitemaps = self._extract_product_sitemaps(sitemap_index)
        for sitemap_url in product_sitemaps:
            if len(products) >= self.max_products:
                break

            sitemap_xml = await self.fetch(sitemap_url)
            if not sitemap_xml:
                continue

            product_urls = self._extract_urls(sitemap_xml)
            for product_url in product_urls:
                if len(products) >= self.max_products:
                    break
                if "/products/" not in product_url:
                    continue

                product_html = await self.fetch(product_url)
                if not product_html:
                    continue

                product = self._parse_product_page(product_html, product_url)
                if product:
                    products.append(product)

    def _extract_product_sitemaps(self, sitemap_index: str) -> List[str]:
        root = ET.fromstring(sitemap_index)
        urls = []
        for loc in root.findall(".//sm:loc", SITEMAP_NS):
            value = (loc.text or "").strip()
            if "sitemap_products_" in value:
                urls.append(value)
        return urls

    def _extract_urls(self, sitemap_xml: str) -> List[str]:
        root = ET.fromstring(sitemap_xml)
        urls = []
        for loc in root.findall(".//sm:url/sm:loc", SITEMAP_NS):
            value = (loc.text or "").strip()
            if value:
                urls.append(value)
        return urls

    def _parse_product_page(self, html: str, url: str) -> Optional[Product]:
        payload = self._extract_product_json_ld(html)
        if not payload:
            return None

        offers = payload.get("offers") or {}
        brand = payload.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        category_path = None
        category = payload.get("category")
        if isinstance(category, str) and category:
            category_path = [category]

        return Product(
            name=self._clean_text(payload.get("name")),
            price=self._clean_text(str(offers.get("price"))) if offers.get("price") is not None else None,
            url=payload.get("url") or url,
            brand=self._clean_text(brand),
            image_url=payload.get("image"),
            sku=self._clean_text(payload.get("sku") or payload.get("gtin")),
            category=self._clean_text(category) if isinstance(category, str) else None,
            category_path=category_path,
            raw_data=payload,
        )

    def _extract_product_json_ld(self, html: str) -> Optional[dict]:
        match = re.search(
            r'<script type="application/ld\+json" id="googleRichSnippet">\s*(\{.*?\})\s*</script>',
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
        return payload
