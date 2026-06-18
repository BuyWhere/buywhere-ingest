"""Scraper for Shopee Singapore marketplace."""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode, urljoin
from .base_scraper import BaseScraper, Product

SHOPEE_SG_BASE = "https://shopee.sg"
logger = logging.getLogger(__name__)


class ShopeeSGScraper(BaseScraper):
    """Scraper for Shopee Singapore marketplace.

    Note: Shopee uses heavy JavaScript rendering. This adapter attempts to use
    Shopee's internal API when available, with HTML parsing as fallback.
    Access credentials or API keys may be required for sustained scraping.
    """

    def __init__(self, max_products: int = 50):
        super().__init__("Shopee SG", SHOPEE_SG_BASE)
        self.max_products = max_products
        self.shopee_api_base = "https://shopee.sg/api/v4"

    def _get_shopee_headers(self) -> Dict[str, str]:
        """Generate Shopee-compatible headers."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{self.base_url}/",
            "X-Shopee-Language": "en",
            "X-Requested-With": "XMLHttpRequest",
        }

    async def fetch_json(self, url: str) -> Optional[Dict]:
        """Fetch JSON response from Shopee API."""
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                response = await self.session.get(url, headers=self._get_shopee_headers(), follow_redirects=True)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
        return None

    async def _scrape_via_search_api(self, products: List[Product]) -> bool:
        """Attempt to scrape via Shopee's search API."""
        page_size = 50
        skip = 0
        while len(products) < self.max_products and skip < 500:
            search_url = f"{self.shopee_api_base}/search/search?keyword=*&limit={page_size}&offset={skip}&newest={skip}"
            data = await self.fetch_json(search_url)
            if not data or not data.get("data"):
                return False

            items = data.get("data", {}).get("items", [])
            if not items:
                return True

            for item in items:
                if len(products) >= self.max_products:
                    break

                price = item.get("price", 0)
                if price:
                    price = str(price / 100000)

                product = Product(
                    name=self._clean_text(item.get("title")),
                    price=price,
                    url=f"{self.base_url}/product/-/{item.get('shopid', '')}/{item.get('itemid', '')}",
                    sku=f"SHOPEE_{item.get('itemid', '')}",
                    brand=self._clean_text(item.get("brand", {}).get("name")) if isinstance(item.get("brand"), dict) else None,
                    image_url=f"https://cf.shopee.sg/file/{item.get('image', '')}",
                )
                products.append(product)

            skip += page_size
            await asyncio.sleep(0.3)

        return True

    async def _scrape_via_html(self, products: List[Product]) -> None:
        """Fallback: scrape via HTML parsing."""
        page = 1
        seen_urls = set()
        while len(products) < self.max_products and page <= 5:
            search_url = f"{self.base_url}/search?keyword=*&page={page}"
            html = await self.fetch(search_url)
            if not html:
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select(".shopee-item-card, .product-item, [data-sold=], [data-itemid]")
            if not items:
                break

            for item in items:
                if len(products) >= self.max_products:
                    break

                name_elem = item.select_one(".product-name, .item-title, h3, [data-sqp-type='title']")
                price_elem = item.select_one(".price, .item-price, [data-sqp-type='price']")
                link_elem = item.select_one("a")
                image_elem = item.select_one("img")

                product_url = None
                if link_elem:
                    href = link_elem.get("href", "")
                    if href:
                        product_url = urljoin(self.base_url, href.split("?")[0].rstrip("/"))

                if product_url and product_url in seen_urls:
                    continue
                if product_url:
                    seen_urls.add(product_url)

                image_url = None
                if image_elem:
                    image_url = image_elem.get("src") or image_elem.get("data-src")

                price_text = None
                if price_elem:
                    price_text = self._clean_text(price_elem.get_text())
                    import re as re_module
                    price_match = re_module.search(r"[\d,]+\.?\d*", price_text.replace("S$", "").replace(",", ""))
                    if price_match:
                        price_text = price_match.group(0)

                product = Product(
                    name=self._clean_text(name_elem.get_text()) if name_elem else None,
                    price=price_text,
                    url=product_url,
                    image_url=image_url,
                )
                products.append(product)

            page += 1
            await asyncio.sleep(0.5)

    async def _scrape_impl(self, products: List[Product]) -> None:
        """Main scraping implementation with API-first, HTML fallback."""
        if not await self._scrape_via_search_api(products):
            logger.info("Search API unavailable, falling back to HTML parsing")
            await self._scrape_via_html(products)


async def main():
    async with ShopeeSGScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Shopee SG: {count} products")


if __name__ == "__main__":
    asyncio.run(main())