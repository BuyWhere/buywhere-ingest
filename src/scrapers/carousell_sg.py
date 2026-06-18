"""Scraper for Carousell Singapore marketplace."""

import asyncio
import logging
import os
import re
from typing import List, Optional

from .base_scraper import BaseScraper, Product

CAROUSELL_SG_BASE = "https://www.carousell.sg"

logger = logging.getLogger(__name__)


class CarousellSGScraper(BaseScraper):
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2

    def __init__(self):
        super().__init__("Carousell SG", CAROUSELL_SG_BASE)
        # No proxy — Carousell SG blocks BrightData residential IPs with HTTP 402.
        # Direct Playwright connection works correctly (verified 2026-06-13).

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
        """Fetch URL using Playwright for JavaScript rendering (direct, no proxy)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None

        try:
            p = await async_playwright().start()
            try:
                launch_options: dict = {
                    "headless": True,
                    "args": [
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                    ],
                }
                # No proxy — Carousell SG works with direct connection and
                # blocks BrightData residential IPs with HTTP 402.
                browser = await p.chromium.launch(**launch_options)
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
                    await page.goto(url, wait_until="networkidle", timeout=45000)
                    await page.wait_for_timeout(5000)
                    html = await page.content()
                    return html
                except Exception:
                    return None
                finally:
                    await browser.close()
                    await p.stop()
            except Exception:
                await p.stop()
                return None
        except Exception:
            return None

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch URL with Playwright primary, ScraperAPI fallback for JavaScript rendering."""
        # Try Playwright first
        html = await self._fetch_with_playwright(url)
        if html:
            return html

        # Fallback to ScraperAPI if Playwright fails
        try:
            html = await self._fetch_with_scraperapi(url)
            if html:
                return html
        except Exception:
            pass

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

        search_url = f"{self.base_url}/search/?q=electronics&sort=date_created%3Adesc"
        html = await self.fetch(search_url)
        if not html:
            return

        soup = BeautifulSoup(html, "html.parser")

        # Product cards: <div class="D_crT M_cqE"><a class="D_mS"><content/></a></div>
        for card in soup.find_all("div", class_=lambda c: c and "D_crT" in c and "M_cqE" in c):
            link_elem = card.find("a", href=True)
            if not link_elem:
                continue

            link = link_elem.get("href", "")
            if not link.startswith("http"):
                link = f"{self.base_url}{link}"

            # Product name: <span style="--max-line:2">
            name_elem = card.find("span", style=lambda s: s and "--max-line:2" in str(s))
            name = self._clean_text(name_elem.get_text()) if name_elem else ""
            if not name or len(name) < 3:
                continue

            # Price: S$ text inside the card
            import re
            price = None
            price_match = re.search(r"S\$\s*([\d,]+\.?\d*)", str(card))
            if price_match:
                price = price_match.group(1).replace(",", "")

            # Image: first img inside the card
            img_elem = card.find("img")
            image_url = None
            if img_elem:
                image_url = img_elem.get("src") or img_elem.get("data-src")

            products.append(
                Product(
                    name=name,
                    price=price,
                    url=link,
                    image_url=image_url,
                    category="Marketplace",
                    category_path=["Marketplace", "Carousell SG"],
                    raw_data={
                        "source": "carousell_sg",
                        "scrape_url": search_url,
                    },
                )
            )

            if len(products) >= 100:
                break