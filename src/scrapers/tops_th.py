
"""Scraper for Tops Online Thailand (tops.co.th).

Tops uses Cloudflare WAF protection. We use Playwright with stealth
and Brightdata residential proxy to bypass the Cloudflare challenge.
"""

import asyncio
import logging
import os
import re
from typing import List, Optional, Set
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from .base_scraper import BaseScraper, Product
from .proxy_config import Zone, proxy_config_for_playwright

logger = logging.getLogger(__name__)

TOPS_BASE = "https://www.tops.co.th"
TOPS_EN = "https://www.tops.co.th/en"


class TopsTHScraper(BaseScraper):
    """Scraper for Tops Online Thailand via Brightdata proxy + Playwright."""

    MAX_PRODUCTS = 40000
    REQUEST_DELAY = 3.0

    def __init__(self):
        super().__init__("Tops Online TH", TOPS_BASE)
        self._browser = None
        self._context = None

    async def _ensure_browser(self):
        """Lazy-init Playwright browser with Brightdata proxy."""
        if self._browser:
            return
        proxy_cfg = proxy_config_for_playwright(Zone.BUYWHERE_RESI)
        logger.info(f"Launching Playwright with Brightdata {Zone.BUYWHERE_RESI.value} proxy")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            proxy=proxy_cfg,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Bangkok",
        )
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

    async def _fetch_page_playwright(self, url: str) -> Optional[str]:
        """Fetch page HTML using Playwright + Brightdata proxy + Stealth."""
        try:
            await self._ensure_browser()
            page = await self._context.new_page()
            await Stealth(page).apply_stealth()
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)
            html = await page.content()
            await page.close()
            if "tops" in html.lower() and len(html) > 5000:
                return html
            logger.warning(f"Page content suspicious ({len(html)} bytes)")
            return None
        except Exception as e:
            logger.warning(f"Playwright fetch failed: {e}")
            return None


    async def fetch(self, url: str) -> Optional[str]:
        """Fetch URL using Playwright with Brightdata proxy + retry."""
        for attempt in range(self.RETRY_ATTEMPTS):
            html = await self._fetch_page_playwright(url)
            if html:
                return html
            if attempt < self.RETRY_ATTEMPTS - 1:
                wait = self.RETRY_DELAY * (attempt + 1) * 5
                logger.info(f"Retry {attempt + 1}/{self.RETRY_ATTEMPTS} in {wait}s")
                await asyncio.sleep(wait)
        return None

    async def _fetch_search_page(self, query: str, page: int) -> Optional[str]:
        """Fetch a search results page."""
        url = f"{TOPS_EN}/search?q={query}&page={page}"
        return await self.fetch(url)

    def _parse_search_results(self, html: str, seen_urls: Set[str]) -> List[Product]:
        """Parse search result page for products."""
        soup = BeautifulSoup(html, "html.parser")
        products = []

        # Try various product item selectors
        items = soup.select(
            "[data-product-id], .product-item, .product-card, "
            ".product-tile, [class*='product-item'], article, "
            ".search-result-item, .product-grid-item, li[class*='product']"
        )

        if not items:
            items = soup.find_all(["div", "li", "article"],
                                  class_=re.compile(r"product|item|card|tile"))

        for item in items:
            link = item.select_one("a[href]")
            if not link:
                continue
            url = link.get("href", "")
            if not url.startswith("http"):
                url = urljoin(TOPS_BASE, url)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            name_elem = item.select_one(
                "h2, h3, .product-name, .name, [data-product-name], "
                ".product-title, [class*='title'], [class*='name']"
            )
            price_elem = item.select_one(
                ".price, .product-price, [data-price], "
                "[class*='price'], .current-price, .discount-price"
            )
            img_elem = item.select_one("img")
            img_url = img_elem.get("src") or img_elem.get("data-src") if img_elem else None
            if not name_elem:
                continue
            product = Product(
                name=self._clean_text(name_elem.get_text(strip=True)),
                price=self._clean_text(price_elem.get_text(strip=True)) if price_elem else None,
                url=url,
                image_url=img_url,
            )
            if product.name:
                products.append(product)
        return products


    async def _scrape_impl(self, products: List[Product]) -> None:
        """Scrape Tops by searching across broad grocery queries."""
        seen_urls: Set[str] = set()

        search_queries = [
            "*", "a", "e", "i", "o", "u",
            "coffee", "tea", "milk", "rice", "noodle",
            "oil", "sauce", "snack", "chip", "candy",
            "water", "juice", "soda", "sugar", "salt",
            "bread", "butter", "cheese", "egg", "yogurt",
            "chicken", "pork", "beef", "fish",
            "soap", "shampoo", "clean", "detergent",
            "baby", "pet", "paper", "tissue", "bag",
            "fresh", "frozen", "fruit", "vegetable",
        ]

        for query in search_queries:
            if len(products) >= self.MAX_PRODUCTS:
                break
            logger.info(f"Tops search '{query}' ({len(products)} so far)")
            page = 1
            empty_pages = 0
            while empty_pages < 3 and len(products) < self.MAX_PRODUCTS:
                html = await self._fetch_search_page(query, page)
                if not html:
                    break
                page_products = self._parse_search_results(html, seen_urls)
                if not page_products:
                    empty_pages += 1
                    page += 1
                    continue
                products.extend(page_products)
                empty_pages = 0
                page += 1
                await asyncio.sleep(self.REQUEST_DELAY)

            logger.info(
                f"  '{query}': "
                f"{len([p for p in products if query.lower() in (p.name or '').lower()])} matches, "
                f"{len(products)} total so far"
            )

        logger.info(f"Tops total: {len(products)} products")

    async def close(self):
        """Close Playwright resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if hasattr(self, '_playwright') and self._playwright:
            await self._playwright.stop()
            self._playwright = None
        if self.session:
            await self.session.aclose()
            self.session = None


async def main():
    """Quick test."""
    logging.basicConfig(level=logging.INFO)
    scraper = TopsTHScraper()
    try:
        async with scraper:
            products = await scraper.scrape()
            print(f"\nTops Online TH: {len(products)} products")
            if products:
                for p in products[:5]:
                    print(f"  {p.name} - {p.price}")
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
