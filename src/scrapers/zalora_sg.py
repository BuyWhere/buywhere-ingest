"""Scraper for Zalora Singapore.

Uses ScraperAPI with `render=true` to fetch the JS-rendered catalog page,
then parses the Next.js product card markup to extract SKUs, URLs, names,
brands, prices, and images.
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

ZALORA_SG_BASE = "https://www.zalora.sg"
SCRAPERAPI_BASE = "http://api.scraperapi.com"
logger = logging.getLogger(__name__)


def _scraperapi_key() -> Optional[str]:
    return os.environ.get("SCRAPERAPI_KEY") or os.environ.get("SCRAPER_API_KEY")


def _scraperapi_url(target_url: str, render: bool = True, country: str = "sg") -> Optional[str]:
    key = _scraperapi_key()
    if not key:
        return None
    params = [f"api_key={key}", f"url={target_url}"]
    if render:
        params.append("render=true")
    if country:
        params.append(f"country_code={country}")
    return f"{SCRAPERAPI_BASE}/?{'&'.join(params)}"


class ZaloraSGScraper(BaseScraper):
    """Scraper for Zalora Singapore fashion e-commerce.

    Zalora's catalog page is a Next.js SPA. Direct HTTP returns a shell.
    ScraperAPI `render=true` returns the fully rendered HTML with
    `<a data-test-id="productLink">` cards.
    """

    RETRY_ATTEMPTS = 6
    RETRY_DELAY = 5
    REQUEST_TIMEOUT = 90

    CATALOG_PATHS = [
        "/catalog",
    ]

    def __init__(self, max_products: int = 100):
        super().__init__("Zalora SG", ZALORA_SG_BASE)
        self.max_products = max_products
        self.search_url = f"{ZALORA_SG_BASE}/catalog"

    async def _scraperapi_get(self, target_url: str, country: str = "sg") -> Optional[str]:
        proxy_url = _scraperapi_url(target_url, render=True, country=country)
        if not proxy_url:
            logger.warning("SCRAPERAPI_KEY not set; cannot reach Zalora")
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
    def _normalize_price(price_text: Optional[str]) -> Optional[str]:
        if not price_text:
            return None
        text = unescape(price_text).replace("\xa0", " ")
        match = re.search(r"[\d,]+\.?\d*", text.replace("S$", "").replace("RM", ""))
        if match:
            return match.group(0).replace(",", "")
        return None

    @staticmethod
    def _parse_product_card(card_html: str) -> Optional[Product]:
        sku_match = re.search(r'data-sku="([^"]+)"', card_html)
        if not sku_match:
            return None
        sku = f"ZALORA_SG_{sku_match.group(1)}"

        href_match = re.search(r'href="(https?://[^"]+/p/[^"]+)"', card_html)
        product_url = href_match.group(1) if href_match else None
        if not product_url:
            return None

        name = None
        title_block = re.search(
            r'data-test-id="productTitle"[^>]*>\s*<h3[^>]*>(.*?)</h3>', card_html, re.DOTALL
        )
        if title_block:
            raw_title = re.sub(r"<[^>]+>", " ", title_block.group(1))
            raw_title = re.sub(r"S\$\s*[\d,.]+", "", raw_title)
            name = ZaloraSGScraper._clean_text(raw_title)
        if not name:
            img_block = re.search(r'<img[^>]*alt="([^"]+)"', card_html)
            if img_block:
                name = ZaloraSGScraper._clean_text(img_block.group(1))

        brand = None
        brand_block = re.search(
            r'data-test-id="productBrandName"[^>]*>(.*?)</div>', card_html, re.DOTALL
        )
        if brand_block:
            brand = ZaloraSGScraper._clean_text(re.sub(r"<[^>]+>", " ", brand_block.group(1)))

        price = None
        price_block = re.search(
            r'data-test-id="productPrice"[^>]*>(.*?)</span>', card_html, re.DOTALL
        )
        if price_block:
            price = ZaloraSGScraper._normalize_price(re.sub(r"<[^>]+>", "", price_block.group(1)))

        image_url = None
        img_match = re.search(r'<img[^>]*src="([^"]+)"', card_html)
        if img_match:
            image_url = img_match.group(1)

        if not name:
            return None

        return Product(
            name=name,
            price=price,
            url=product_url,
            sku=sku,
            brand=brand,
            image_url=image_url,
        )

    async def _scrape_impl(self, products: List[Product]) -> None:
        seen_skus: set[str] = set()
        for path in self.CATALOG_PATHS:
            if len(products) >= self.max_products:
                break
            url = urljoin(ZALORA_SG_BASE, path)
            html = await self._scraperapi_get(url, country="sg")
            if not html:
                logger.warning(f"Zalora SG: no HTML for {url}")
                continue

            cards = re.findall(
                r'<a [^>]*data-test-id="productLink"[^>]*>.*?</a>', html, re.DOTALL
            )
            logger.info(f"Zalora SG {path}: {len(cards)} cards in HTML")
            for card in cards:
                if len(products) >= self.max_products:
                    break
                product = self._parse_product_card(card)
                if not product or not product.sku:
                    continue
                if product.sku in seen_skus:
                    continue
                seen_skus.add(product.sku)
                products.append(product)
            await asyncio.sleep(0.5)


async def main():
    async with ZaloraSGScraper(max_products=20) as scraper:
        prods = await scraper.scrape()
        print(f"Zalora SG: {len(prods)} products")
        for p in prods[:5]:
            print(json.dumps({
                "sku": p.sku, "name": p.name, "price": p.price,
                "brand": p.brand, "url": p.url,
            }))


if __name__ == "__main__":
    asyncio.run(main())
