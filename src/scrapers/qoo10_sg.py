"""Scraper for Qoo10 Singapore marketplace."""

import asyncio
import os
import re
from typing import List, Optional

from .base_scraper import BaseScraper, Product

QOO10_SG_BASE = "https://www.qoo10.sg"


class Qoo10SGScraper(BaseScraper):
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2

    def __init__(self):
        super().__init__("Qoo10 SG", QOO10_SG_BASE)

    async def _fetch_with_scraperapi(self, url: str) -> Optional[str]:
        """Fetch URL using ScraperAPI to render JavaScript."""
        scraperapi_key = os.environ.get("SCRAPERAPI_KEY")
        if not scraperapi_key:
            return None

        try:
            resp = await self.session.get(
                "http://api.scraperapi.com",
                params={
                    "api_key": scraperapi_key,
                    "url": url,
                    "render": "true",
                },
                timeout=60.0,
            )
            if resp.status_code == 200:
                return resp.text
            return None
        except Exception:
            return None

    async def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch URL using Playwright to render JavaScript."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-SG",
                )
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-SG', 'en'] });
                """)
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                    html = await page.content()
                    return html
                except Exception:
                    return None
                finally:
                    await browser.close()
        except Exception:
            return None

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch URL with ScraperAPI/Playwright fallback for JavaScript rendering."""
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                html = await self._fetch_with_scraperapi(url)
                if html:
                    return html
            except Exception:
                pass

            try:
                html = await self._fetch_with_playwright(url)
                if html:
                    return html
            except Exception:
                pass

            if attempt < self.RETRY_ATTEMPTS - 1:
                await asyncio.sleep(self.RETRY_DELAY)

        return None

    def _parse_price(self, price_text: Optional[str]) -> Optional[str]:
        """Extract numeric price from text like 'S$ 25.00'."""
        if not price_text:
            return None
        match = re.search(r"S?\$?\s*([\d,]+(?:\.\d{2})?)", price_text.replace(",", ""))
        if match:
            return match.group(1)
        return None

    async def _scrape_impl(self, products: List[Product]) -> None:
        from bs4 import BeautifulSoup

        search_url = f"{self.base_url}/search?keyword=electronics"
        html = await self.fetch(search_url)
        if not html:
            return

        soup = BeautifulSoup(html, "html.parser")

        for item in soup.select(
            ".item, .goods-item, [class*='product'], [class*='item'], "
            ".list-item, div[class*='goods'], article[class*='item']"
        ):
            name_elem = item.select_one(
                ".goods_name, .name, .title, h3, h4, [class*='name'], "
                "[class*='title'], [data-name], [data-title]"
            )
            price_elem = item.select_one(
                ".price, [class*='price'], [data-price], .goods_price, .s_price"
            )
            link_elem = item.select_one("a[href]")
            image_elem = item.select_one("img[src], img[data-original]")
            brand_elem = item.select_one(
                ".brand, [class*='brand'], .maker, [class*='maker']"
            )

            if not name_elem:
                continue

            name = self._clean_text(name_elem.get_text())
            if not name or len(name) < 3:
                continue

            link = link_elem["href"] if link_elem else None
            if link and not link.startswith("http"):
                link = f"{self.base_url}{link}"

            price = self._parse_price(
                self._clean_text(price_elem.get_text()) if price_elem else None
            )

            image_url = None
            if image_elem:
                image_url = image_elem.get("src") or image_elem.get("data-original")

            brand = self._clean_text(brand_elem.get_text()) if brand_elem else None

            products.append(
                Product(
                    name=name,
                    price=price,
                    url=link,
                    image_url=image_url,
                    brand=brand,
                    category="E-commerce",
                    category_path=["E-commerce", "Qoo10 SG"],
                    raw_data={
                        "source": "qoo10_sg",
                        "scrape_url": search_url,
                    },
                )
            )

            if len(products) >= 100:
                break