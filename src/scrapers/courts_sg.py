"""Scraper for Courts Singapore."""

import asyncio
import json
import re
from urllib.parse import urljoin
from typing import List, Optional
from .base_scraper import BaseScraper, Product

COURTS_SG_BASE = "https://www.courts.com.sg"


class CourtsSGScraper(BaseScraper):
    """Scraper for Courts Singapore."""

    def __init__(self):
        super().__init__("Courts SG", COURTS_SG_BASE)
        self.search_url = f"{COURTS_SG_BASE}/catalogsearch/result"

    def _find_brand_in_json(self, obj):
        if isinstance(obj, dict):
            for key in ("brand", "manufacturer"):
                value = obj.get(key)
                if isinstance(value, str) and value.strip():
                    return self._clean_text(value)
                if isinstance(value, dict):
                    name = value.get("name")
                    if isinstance(name, str) and name.strip():
                        return self._clean_text(name)

            for value in obj.values():
                found = self._find_brand_in_json(value)
                if found:
                    return found

        elif isinstance(obj, list):
            for item in obj:
                found = self._find_brand_in_json(item)
                if found:
                    return found
        return None

    async def _extract_brand(self, product_html: Optional[str]) -> Optional[str]:
        if not product_html:
            return None

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(product_html, "html.parser")

        brand_selectors = [
            "[itemprop='brand']",
            "meta[property='product:brand']",
            "meta[name='product_brand']",
            ".product-brand",
            ".product-info-main .product-brand",
            ".manufacturer span",
            ".manufacturer",
            ".brand",
        ]
        for selector in brand_selectors:
            node = soup.select_one(selector)
            if not node:
                continue

            if node.name == "meta":
                value = node.get("content", "").strip()
            else:
                value = node.get_text(" ", strip=True)

            if value:
                return self._clean_text(value)

        # JSON-LD structured data often stores product brand as a nested object
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            raw = script.string
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue

            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                brand = entry.get("brand")
                if isinstance(brand, dict):
                    name = brand.get("name")
                    if name:
                        return self._clean_text(str(name))
                if isinstance(brand, str) and brand.strip():
                    return self._clean_text(brand)

        # Magento product details scripts can expose brand in the action payload.
        for script in soup.find_all("script"):
            if "brand" not in (script.string or "").lower():
                continue

            script_text = (script.string or "").strip()
            if not script_text:
                continue

            try:
                payload = json.loads(script_text)
            except Exception:
                # Avoid hard parse failure for non-JSON inline blocks.
                pass
            else:
                brand = self._find_brand_in_json(payload)
                if brand:
                    return brand

            match = re.search(r'\"brand\"\\s*:\\s*\"([^\"]{1,80})\"', script_text)
            if match:
                return self._clean_text(match.group(1))

        return None

    async def _fetch_product_brand(self, product_url: Optional[str]) -> Optional[str]:
        if not product_url:
            return None
        product_html = await self.fetch(product_url)
        return await self._extract_brand(product_html)

    async def _scrape_impl(self, products: List[Product]) -> None:
        max_pages = 5
        page = 1
        while page <= max_pages:
            url = f"{self.search_url}/?q=*&page={page}"
            html = await self.fetch(url)
            if not html:
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select(".product-item")
            if not items:
                break

            for item in items:
                name_elem = item.select_one(".product-name, .product-title, h2, h3, .title")
                price_elem = item.select_one(".price")

                product = Product(
                    name=self._clean_text(name_elem.get_text()) if name_elem else None,
                    price=self._clean_text(price_elem.get_text()) if price_elem else None,
                )
                products.append(product)

            page += 1
            await asyncio.sleep(0.5)


async def main():
    async with CourtsSGScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Courts SG: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
