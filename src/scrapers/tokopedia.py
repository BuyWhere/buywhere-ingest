"""Scraper for Tokopedia Indonesia.

Uses ScraperAPI with `render=true` and `premium=true` (Tokopedia is a
protected domain requiring premium tier) to fetch the JS-rendered search page,
then parses the product card markup.
"""

import asyncio
import json
import logging
import os
import re
from html import unescape
from typing import List, Optional
from urllib.parse import urljoin

import httpx

from .base_scraper import BaseScraper, Product

TOKOPEDIA_BASE = "https://www.tokopedia.com"
SCRAPERAPI_BASE = "http://api.scraperapi.com"
logger = logging.getLogger(__name__)


def _scraperapi_key() -> Optional[str]:
    return os.environ.get("SCRAPERAPI_KEY") or os.environ.get("SCRAPER_API_KEY")


def _scraperapi_url(target_url: str, render: bool = True, premium: bool = True, country: str = "id") -> Optional[str]:
    key = _scraperapi_key()
    if not key:
        return None
    params = [f"api_key={key}", f"url={target_url}"]
    if render:
        params.append("render=true")
    if premium:
        params.append("premium=true")
    if country:
        params.append(f"country_code={country}")
    return f"{SCRAPERAPI_BASE}/?{'&'.join(params)}"


class TokopediaScraper(BaseScraper):
    """Scraper for Tokopedia Indonesia e-commerce marketplace.

    Tokopedia is a protected domain on ScraperAPI requiring premium=true.
    The search page uses client-side GraphQL to load products, so render=true
    is essential.
    """

    RETRY_ATTEMPTS = 4
    RETRY_DELAY = 10
    REQUEST_TIMEOUT = 120

    def __init__(self, max_products: int = 100):
        super().__init__("Tokopedia ID", TOKOPEDIA_BASE)
        self.max_products = max_products
        self.search_url = f"{TOKOPEDIA_BASE}/search"

    async def _scraperapi_get(self, target_url: str) -> Optional[str]:
        proxy_url = _scraperapi_url(target_url, render=True, premium=True, country="id")
        if not proxy_url:
            logger.warning("SCRAPERAPI_KEY not set; cannot reach Tokopedia")
            return None
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self.REQUEST_TIMEOUT)
                ) as client:
                    response = await client.get(proxy_url, follow_redirects=True)
                if response.status_code == 200 and len(response.text) > 5000:
                    return response.text
                logger.warning(
                    f"ScraperAPI attempt {attempt + 1}/{self.RETRY_ATTEMPTS} "
                    f"got status={response.status_code} size={len(response.text)} for {target_url}"
                )
            except Exception as e:
                logger.warning(f"ScraperAPI attempt {attempt + 1}/{self.RETRY_ATTEMPTS} error for {target_url}: {e}")
            if attempt < self.RETRY_ATTEMPTS - 1:
                wait = self.RETRY_DELAY * (2 ** attempt)
                logger.info(f"Retrying in {wait}s...")
                await asyncio.sleep(wait)
        logger.error(f"All {self.RETRY_ATTEMPTS} ScraperAPI attempts failed for {target_url}")
        return None

    @staticmethod
    def _clean_text(text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        return unescape(" ".join(text.split()).strip())

    @staticmethod
    def _extract_price(price_text: Optional[str]) -> Optional[str]:
        if not price_text:
            return None
        text = unescape(price_text).replace("\xa0", " ")
        match = re.search(r"[\d,]+\.?\d*", text.replace("Rp", "").replace(".", "").replace(",", ""))
        if match:
            return match.group(0).replace(",", "")
        return None

    async def _scrape_impl(self, products: List[Product]) -> None:
        page = 1
        seen_urls: set[str] = set()
        while len(products) < self.max_products:
            url = f"{self.search_url}?q=*&page={page}"
            html = await self._scraperapi_get(url)
            if not html:
                logger.warning(f"Tokopedia ID: no HTML for page {page}")
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select(
                "[data-testid='product-card'], .product-card, .pc-all-product, "
                "article[data-testid='divProductWrapper'], .product-item, .goods-card"
            )
            if not items:
                items = soup.select(".product-item, .goods-card, .pdp-product-card")

            if not items:
                logger.info(f"Tokopedia ID page {page}: no product cards found, stopping")
                break

            for item in items:
                if len(products) >= self.max_products:
                    break

                name_elem = item.select_one(
                    "[data-testid='product-name'], .product-name, .goods-name, h3, h4"
                )
                price_elem = item.select_one(
                    "[data-testid='product-price'], .product-price, .price, .goods-price"
                )
                link_elem = item.select_one(
                    "a[href*='/p/'], a[href*='/product/'], a.product-link"
                )

                product_url = None
                if link_elem:
                    href = link_elem.get("href", "")
                    if href:
                        product_url = urljoin(self.base_url, href) if not href.startswith("http") else href

                if not product_url or product_url in seen_urls:
                    continue
                seen_urls.add(product_url)

                price_text = None
                if price_elem:
                    price_text = self._extract_price(price_elem.get_text())

                sku = None
                slug_match = re.search(r"/p/([^/]+)|/product/([^/]+)", product_url)
                if slug_match:
                    slug = slug_match.group(1) or slug_match.group(2)
                    sku = f"TOKOPEDIA_ID_{slug[:30]}"

                brand = None
                brand_elem = item.select_one(
                    "[data-testid='product-brand'], .product-brand, .goods-brand, .shop-badge"
                )
                if brand_elem:
                    brand = self._clean_text(brand_elem.get_text())

                image_url = None
                image_elem = item.select_one("img[src*='product'], img.product-image, .goods-image img")
                if image_elem:
                    image_url = image_elem.get("src") or image_elem.get("data-src")

                product = Product(
                    name=self._clean_text(name_elem.get_text()) if name_elem else None,
                    price=price_text,
                    url=product_url,
                    sku=sku,
                    brand=brand,
                    image_url=image_url,
                )
                products.append(product)

            page += 1
            await asyncio.sleep(1.0)


async def main():
    async with TokopediaScraper(max_products=20) as scraper:
        prods = await scraper.scrape()
        print(f"Tokopedia ID: {len(prods)} products")
        for p in prods[:5]:
            print(json.dumps({
                "sku": p.sku, "name": p.name, "price": p.price,
                "brand": p.brand, "url": p.url,
            }))


if __name__ == "__main__":
    asyncio.run(main())
