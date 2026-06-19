"""Scraper for Klik Indomaret Indonesia (klikindomaret.com).

Klik Indomaret is behind Cloudflare WAF. We use Playwright with Brightdata
residential proxy and stealth to bypass the Cloudflare challenge.
"""

import asyncio
import json
import logging
import re
from typing import List, Optional, Set

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from .base_scraper import BaseScraper, Product
from .proxy_config import Zone, proxy_config_for_playwright

logger = logging.getLogger(__name__)

KI_BASE = "https://www.klikindomaret.com"

class KlikIndomaretScraper(BaseScraper):
    """Scraper for Klik Indomaret via Playwright + Brightdata."""

    MAX_PRODUCTS = 15000
    REQUEST_DELAY = 3.0

    def __init__(self):
        super().__init__("Klik Indomaret", KI_BASE)
        self._browser = None
        self._context = None
        self._playwright = None

    async def _ensure_browser(self):
        """Lazy-init Playwright browser with Brightdata residential proxy."""
        if self._browser:
            return
        proxy_cfg = proxy_config_for_playwright(Zone.RESIDENTIAL_PROXY1)
        logger.info("Launching Playwright with Brightdata residential proxy")
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
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            ignore_https_errors=True,
        )
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

    async def _fetch_page_playwright(self, url: str) -> Optional[str]:
        """Fetch page HTML using Playwright + Brightdata + Stealth."""
        try:
            await self._ensure_browser()
            page = await self._context.new_page()
            st = Stealth()
            await st.apply_stealth_async(page)
            await page.goto(url, wait_until="networkidle", timeout=90000)
            await asyncio.sleep(5)
            html = await page.content()
            await page.close()
            if "klikindomaret" in html.lower() and len(html) > 5000:
                return html
            logger.warning(f"Page content suspicious ({len(html)} bytes)")
            return None
        except Exception as e:
            logger.warning(f"Playwright fetch failed: {e}")
            return None

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch URL using Playwright + retry."""
        for attempt in range(self.RETRY_ATTEMPTS):
            html = await self._fetch_page_playwright(url)
            if html:
                return html
            if attempt < self.RETRY_ATTEMPTS - 1:
                wait = self.RETRY_DELAY * (attempt + 1) * 5
                logger.info(f"Retry {attempt + 1}/{self.RETRY_ATTEMPTS} in {wait}s")
                await asyncio.sleep(wait)
        return None

    def _parse_products_from_html(self, html: str, seen_urls: Set[str]) -> List[Product]:
        """Extract products from rendered HTML."""
        products = []

        # Try __NEXT_DATA__ first (if site uses Next.js)
        nd_match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html, re.DOTALL
        )
        if nd_match:
            try:
                nd = json.loads(nd_match.group(1))
                page_props = nd.get("props", {}).get("pageProps", {})
                # Klik Indomaret might use different structures
                for key in ("products", "items", "productList", "searchResult", "data"):
                    items = page_props.get(key, [])
                    if isinstance(items, dict):
                        items = items.get("items") or items.get("products") or items.get("data") or []
                    if items:
                        for item in items:
                            p = self._item_to_product(item, seen_urls)
                            if p:
                                products.append(p)
                        if products:
                            return products
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: parse HTML for product cards
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(
            "[class*='product'], [class*='produk'], [class*='item'], "
            "[data-product], article, .goods-item"
        )

        for card in cards:
            link = card.select_one("a[href*='product'], a[href*='produk'], a[href*='detail']")
            if not link:
                link = card.select_one("a[href]")
            if not link:
                continue
            url = link.get("href", "")
            if not url.startswith("http"):
                url = KI_BASE + url if url.startswith("/") else url
            if not url or url in seen_urls:
                continue
            if "/product/" not in url and "/produk/" not in url and "/detail/" not in url:
                continue
            seen_urls.add(url)

            name_elem = card.select_one(
                "h2, h3, h4, [class*='name'], [class*='title'], [class*='judul']"
            )
            price_elem = card.select_one(
                "[class*='price'], [class*='harga'], .current-price"
            )
            img_elem = card.select_one("img[src*='product'], img[src*='produk']")
            if not img_elem:
                img_elem = card.select_one("img")

            name = name_elem.get_text(strip=True) if name_elem else None
            if not name:
                continue

            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r"[\d,.]+", price_text.replace(".", "").replace(",", "."))
                if price_match:
                    price = f"Rp{price_match.group(0)}"

            img_url = None
            if img_elem:
                img_url = img_elem.get("src") or img_elem.get("data-src")

            products.append(Product(
                name=self._clean_text(name),
                price=price,
                url=url,
                image_url=img_url,
            ))

        return products

    def _item_to_product(self, item: dict, seen_urls: Set[str]) -> Optional[Product]:
        """Convert a Klik Indomaret product dict to Product."""
        name = item.get("name") or item.get("productName") or item.get("product_name")
        if not name:
            return None

        sku = item.get("sku") or item.get("id") or item.get("productId")
        slug = item.get("slug") or item.get("url") or item.get("productUrl")

        url = None
        if slug and slug.startswith("http"):
            url = slug
        elif sku:
            url = f"{KI_BASE}/product/detail/{sku}"
        elif slug:
            url = f"{KI_BASE}/{slug.lstrip('/')}"

        if url and url in seen_urls:
            return None
        if url:
            seen_urls.add(url)

        price_raw = item.get("price") or item.get("salePrice") or item.get("listPrice")
        price = None
        if price_raw is not None:
            if isinstance(price_raw, (int, float)):
                price = f"Rp{int(price_raw):,}"
            else:
                price = str(price_raw)

        brand = item.get("brand") or item.get("brandName")
        images = item.get("images") or item.get("imageUrls") or []
        image_url = None
        if isinstance(images, list) and images:
            image_url = images[0] if isinstance(images[0], str) else (images[0].get("url") or images[0].get("src"))
        elif isinstance(images, str):
            image_url = images

        category = item.get("category") or item.get("categoryName")
        in_stock = item.get("inStock") or item.get("stockStatus") or item.get("available")
        if in_stock is None:
            in_stock = True

        return Product(
            name=self._clean_text(name),
            price=price,
            url=url,
            brand=self._clean_text(brand),
            image_url=image_url,
            sku=str(sku) if sku else None,
            category=category,
            in_stock=in_stock,
            raw_data=item,
        )

    async def _fetch_category(self, cat_slug: str, page: int = 1) -> Optional[str]:
        """Fetch a category page."""
        url = f"{KI_BASE}/category/{cat_slug}?page={page}"
        return await self.fetch(url)

    async def _scrape_impl(self, products: List[Product]) -> None:
        """Scrape Klik Indomaret across grocery categories."""
        seen_urls: Set[str] = set()

        categories = [
            "makanan", "minuman", "sembako", "bumbu-dapur",
            "snack", "mie", "beras", "gula", "minyak-goreng",
            "susu", "kopi", "teh", "kecap", "saos",
            "perawatan-tubuh", "kebersihan", "perlengkapan-bayi",
            "kebutuhan-rumah", "alat-dapur", "kertas-tisu",
            "kesehatan", "vitamin", "obat",
            "makanan-beku", "daging", "ikan", "sayuran", "buah",
            "minuman-serbuk", "minuman-siap-saji", "jus",
        ]

        for cat in categories:
            if len(products) >= self.MAX_PRODUCTS:
                break
            logger.info(f"Klik Indomaret category '{cat}' ({len(products)} so far)")

            for page in range(1, 10):  # up to 10 pages per category
                if len(products) >= self.MAX_PRODUCTS:
                    break
                html = await self._fetch_category(cat, page)
                if not html:
                    break

                page_products = self._parse_products_from_html(html, seen_urls)
                if not page_products:
                    break

                products.extend(page_products)
                logger.debug(f"  cat={cat} page={page}: {len(page_products)} products")
                await asyncio.sleep(self.REQUEST_DELAY)

            logger.info(f"  '{cat}': {len(products)} total so far")

        logger.info(f"Klik Indomaret total: {len(products)} products")

    async def close(self):
        """Close Playwright resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        if self.session:
            await self.session.aclose()
            self.session = None


async def main():
    """Quick test."""
    logging.basicConfig(level=logging.INFO)
    scraper = KlikIndomaretScraper()
    try:
        async with scraper:
            products = await scraper.scrape()
            print(f"\nKlik Indomaret: {len(products)} products")
            if products:
                for p in products[:5]:
                    print(f"  {p.name} - {p.price} [{p.brand}]")
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
