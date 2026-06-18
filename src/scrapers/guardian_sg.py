"""Scraper for Guardian Singapore."""

import asyncio
import os
import re
from typing import List, Optional

from .base_scraper import BaseScraper, Product

GUARDIAN_SG_BASE = "https://www.guardian.com.sg"
BEAUTY_SUBCATEGORIES = (
    ("skin care", "Skin Care"),
    ("skincare", "Skin Care"),
    ("makeup", "Makeup"),
    ("hair care", "Hair Care"),
    ("haircare", "Hair Care"),
    ("personal care", "Personal Care"),
    ("fragrance", "Fragrance"),
    ("beauty", "Beauty"),
)


class GuardianSGScraper(BaseScraper):
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2

    def __init__(self):
        super().__init__("Guardian SG", GUARDIAN_SG_BASE)

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

    def _parse_category_path(self, item_text: Optional[str], link: Optional[str]) -> Optional[str]:
        candidates = []
        if item_text:
            candidates.append(self._clean_text(item_text))
        if link:
            path = self._clean_text(link).lower()
            candidates.append(path.replace("-", " "))
            candidates.append("/".join(path.strip("/").split("/")))

        for candidate in candidates:
            if not candidate:
                continue

            split = re.split(r"\s*(?:/|>|\|)\s*", candidate.lower())
            for piece in split:
                for key, label in BEAUTY_SUBCATEGORIES:
                    if key == "beauty":
                        continue
                    if re.search(rf"\b{re.escape(key)}\b", piece):
                        return label

            for key, label in BEAUTY_SUBCATEGORIES:
                if key == "beauty" and not re.search(r"\bbeauty\b", candidate.lower()):
                    continue
                if re.search(rf"\b{re.escape(key)}\b", candidate.lower()):
                    return label

        return None

    async def _scrape_impl(self, products: List[Product]) -> None:
        from bs4 import BeautifulSoup
        html = await self.fetch(f"{self.base_url}/search?q=beauty&page=1")
        if not html:
            return

        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select(".product-item, .product-card, [data-product], .grid-item, .col-product, div[class*='product']"):
            name_elem = item.select_one("h2, h3, .name, .product-name, [data-name]")
            price_elem = item.select_one(".price, .product-price, [data-price]")
            link_elem = item.select_one("a[href]")
            link = link_elem["href"] if link_elem else None

            if not name_elem or not link:
                continue

            category_text = self._clean_text(
                item.select_one(".product-category, .category, .breadcrumb a, .breadcrumbs a") and
                item.select_one(".product-category, .category, .breadcrumb a, .breadcrumbs a").get_text(" ", strip=True)
            )
            subcategory = self._parse_category_path(category_text, link or "")
            if not subcategory:
                continue

            products.append(Product(
                name=self._clean_text(name_elem.get_text()) if name_elem else None,
                price=self._clean_text(price_elem.get_text()) if price_elem else None,
                url=link,
                category=subcategory,
                category_path=["Beauty", subcategory],
            ))
