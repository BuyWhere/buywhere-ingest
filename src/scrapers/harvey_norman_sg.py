"""Scraper for Harvey Norman Singapore using ScraperAPI/Playwright bypass."""

import asyncio
import json
import os
import time
from typing import List, Optional
from .base_scraper import BaseScraper, Product

HARVEY_NORMAN_SG_BASE = "https://www.harveynorman.com.sg"
OUTPUT_DIR = "/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/4b4739f7-c7f5-42d3-b6ab-f7b58687c9d3/_default/data/harvey-norman"


class HarveyNormanSGScraper(BaseScraper):
    """Scraper for Harvey Norman Singapore with Cloudflare bypass."""

    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2
    REQUEST_TIMEOUT = 30

    def __init__(self):
        super().__init__("Harvey Norman SG", HARVEY_NORMAN_SG_BASE)
        self.search_url = f"{HARVEY_NORMAN_SG_BASE}/search"

    async def _fetch_with_scraperapi(self, url: str) -> Optional[str]:
        """Fetch URL using ScraperAPI to bypass Cloudflare."""
        import os
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
        """Fetch URL using Playwright to bypass Cloudflare."""
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
        """Fetch URL with multiple fallback strategies."""
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

    async def _scrape_impl(self, products: List[Product]) -> None:
        """Scrape products using ScraperAPI/Playwright."""
        page = 1
        max_pages = 10

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        outfile = os.path.join(OUTPUT_DIR, f"products_{int(time.time())}.jsonl")

        while page <= max_pages:
            url = f"{self.search_url}?q=*&page={page}"
            html = await self.fetch(url)

            if not html:
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            items = soup.select(".product-item, .product-card, .product-grid-item, [class*='product']")
            if not items:
                break

            page_products = []
            for item in items:
                name_elem = item.select_one(".product-name, .product-title, h2, h3, [class*='name']")
                price_elem = item.select_one(".price, .product-price, .sales-price, [class*='price']")

                product = Product(
                    name=self._clean_text(name_elem.get_text()) if name_elem else None,
                    price=self._clean_text(price_elem.get_text()) if price_elem else None,
                    url=item.select_one("a")["href"] if item.select_one("a") else None,
                )
                products.append(product)
                page_products.append({
                    "name": product.name,
                    "price": product.price,
                    "url": product.url,
                })

            if page_products:
                with open(outfile, "a", encoding="utf-8") as f:
                    for p in page_products:
                        f.write(json.dumps(p, ensure_ascii=False) + "\n")

            page += 1
            await asyncio.sleep(2)

        print(f"Harvey Norman SG: Wrote {len(products)} products to {outfile}")


async def main():
    async with HarveyNormanSGScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Harvey Norman SG: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
