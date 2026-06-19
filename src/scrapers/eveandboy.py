"""Scraper for EVEANDBOY Thailand using the public sitemap and PDP meta tags."""

import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, Product

EVEANDBOY_BASE = "https://eveandboy.com"
EVEANDBOY_SITEMAP = f"{EVEANDBOY_BASE}/sitemap.xml"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class EveandboyScraper(BaseScraper):
    """Scrape a bounded sample of EVEANDBOY products from the public sitemap."""

    def __init__(self, max_products: int = 100):
        super().__init__("EVEANDBOY Thailand", EVEANDBOY_BASE)
        self.max_products = max_products

    async def _scrape_impl(self, products: List[Product]) -> None:
        sitemap_xml = await self.fetch(EVEANDBOY_SITEMAP)
        if not sitemap_xml:
            return

        for product_url in self._extract_urls(sitemap_xml):
            if len(products) >= self.max_products:
                break
            if "/product/" not in product_url:
                continue

            product_html = await self.fetch(product_url)
            if not product_html:
                continue

            product = self._parse_product_page(product_html, product_url)
            if product and product.sku:
                products.append(product)

    def _extract_urls(self, sitemap_xml: str) -> List[str]:
        try:
            root = ET.fromstring(sitemap_xml)
        except ET.ParseError:
            return []

        urls = []
        for loc in root.findall(".//sm:url/sm:loc", SITEMAP_NS):
            value = (loc.text or "").strip()
            if value:
                urls.append(value)
        return urls

    def _parse_product_page(self, html: str, url: str) -> Optional[Product]:
        soup = BeautifulSoup(html, "html.parser")

        meta_title = self._meta_content(soup, "property", "og:title") or self._meta_content(
            soup, "name", "twitter:title"
        )
        name = self._meta_content(soup, "property", "og:image:alt")
        image_url = self._meta_content(soup, "property", "og:image") or self._meta_content(
            soup, "name", "twitter:image"
        )
        canonical_url = self._meta_content(soup, "property", "og:url") or url
        description = self._meta_content(soup, "name", "description")
        sku = self._extract_sku(canonical_url)
        brand = self._derive_brand(meta_title, name)
        in_stock = self._derive_stock_state(soup)

        if not name or not sku:
            return None

        return Product(
            name=self._clean_text(name),
            price=None,
            url=canonical_url,
            brand=self._clean_text(brand),
            image_url=image_url,
            sku=sku,
            category=None,
            category_path=None,
            in_stock=in_stock,
            raw_data={
                "meta_title": meta_title,
                "description": description,
                "image_url": image_url,
                "canonical_url": canonical_url,
                "sku": sku,
                "brand": brand,
            },
        )

    def _meta_content(self, soup: BeautifulSoup, attr: str, value: str) -> Optional[str]:
        node = soup.find("meta", attrs={attr: value})
        if not node:
            return None
        return self._clean_text(node.get("content"))

    def _extract_sku(self, url: str) -> Optional[str]:
        match = re.search(r"-([0-9]{8,})/?$", url)
        return match.group(1) if match else None

    def _derive_brand(self, meta_title: Optional[str], name: Optional[str]) -> Optional[str]:
        if not meta_title or not name:
            return None
        position = meta_title.find(name)
        if position <= 0:
            return None
        brand = meta_title[:position].strip(" -|:")
        return brand or None

    def _derive_stock_state(self, soup: BeautifulSoup) -> Optional[bool]:
        visible_text = soup.get_text(" ", strip=True).lower()
        if "sold out" in visible_text or "out of stock" in visible_text:
            return False
        return None
