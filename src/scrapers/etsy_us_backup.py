"""Etsy US marketplace scraper — target 100K+ handmade and vintage products.

Uses Brightdata buywhere_resi residential proxy + requests + BeautifulSoup.
Target categories: jewelry, clothing, home_and_living, vintage.
"""

import warnings
warnings.filterwarnings("ignore", message=".*Unverified HTTPS request.*")

import asyncio
import logging
import re
from typing import Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from .base_scraper import BaseScraper, Product
from .scraper_registry import register

logger = logging.getLogger(__name__)

@register("etsy_us")
ETSY_BASE = "https://www.etsy.com"

CATEGORIES = [
    {"id": "jewelry", "name": "Jewelry", "path": "/c/jewelry"},
    {"id": "clothing", "name": "Clothing", "path": "/c/clothing"},
    {"id": "home_and_living", "name": "Home & Living", "path": "/c/home-and-living"},
    {"id": "vintage", "name": "Vintage", "path": "/c/vintage"},
]


def _load_proxy() -> Optional[dict]:
    """Load Brightdata buywhere residential proxy dict for requests."""
    try:
        from .proxy_config import proxy_url, Zone
        return proxy_url(Zone.BUYWHERE_RESI)
    except Exception as e:
        logger.warning(f"Could not load Brightdata proxy: {e}")
        return None


def _sync_fetch(url: str, proxy: str, headers: dict, max_retries: int = 5) -> Optional[str]:
    """Fetch URL synchronously using requests with proxy and retry on 502/429/503."""
    import time
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url,
                proxies={"http": proxy, "https": proxy},
                headers=headers,
                timeout=30,
                verify=False,
            )
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code in (502, 503, 429):
                wait = min(2 ** attempt * 5, 60)
                logger.warning(f"HTTP {resp.status_code} for {url}, retry {attempt + 1}/{max_retries} in {wait}s")
                time.sleep(wait)
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
                return None
        except RequestException as e:
            logger.error(f"Request error for {url} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


class EtsyUSScraper(BaseScraper):
    """Scraper for Etsy US marketplace."""

    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2
    REQUEST_TIMEOUT = 30

    def __init__(self):
        super().__init__("Etsy US", ETSY_BASE)
        self._proxy = _load_proxy()
        self._products: List[Product] = []

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        }

    def _extract_products_from_html(self, html: str, category: str, seen_ids: Set[str]) -> List[Product]:
        """Extract products from HTML using BeautifulSoup."""
        products = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("[data-listing-id]")

            for card in cards:
                listing_id = card.get("data-listing-id", "")
                if not listing_id or listing_id in seen_ids:
                    continue
                seen_ids.add(listing_id)

                # Get URL
                href = card.get("href", "")
                if not href:
                    link = card.select_one("a.listing-link, a[href*='/listing/']")
                    href = link.get("href", "") if link else ""

                # Get title
                title = card.get("title", "")
                if not title:
                    link = card.select_one("a.listing-link, a[href*='/listing/']")
                    if link:
                        title = link.get("title", "") or link.get_text(strip=True)

                # Get price
                price = ""
                price_elem = card.select_one(".currency, .price, [class*='price']")
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # Extract dollar amount
                    m = re.search(r'\$([\d,]+\.?\d*)', price_text)
                    if m:
                        price = m.group(1)
                    elif price_text.strip():
                        price = price_text.strip()

                # Get image
                img_url = ""
                img = card.select_one("img")
                if img:
                    img_url = img.get("src") or img.get("data-src") or ""

                # Get seller from link text or parent
                seller = ""
                shop_elem = card.select_one(".shop-name, .shop, [class*='shop']")
                if shop_elem:
                    seller = shop_elem.get_text(strip=True)

                products.append(Product(
                    name=title.strip() if title else "",
                    price=price,
                    url=href,
                    brand=seller,
                    image_url=img_url,
                    category=category,
                    category_path=["Etsy US", category],
                    raw_data={
                        "listing_id": listing_id,
                    },
                ))
        except Exception as e:
            logger.error(f"Error parsing products: {e}")

        return products

    async def _scrape_impl(self, products: List[Product]) -> None:
        """Scrape all categories using requests + BeautifulSoup."""
        proxy_status = "buywhere_resi" if self._proxy else "none"
        logger.info(f"Etsy US scraper starting (proxy: {proxy_status})")

        headers = self._get_headers()
        seen_ids: Set[str] = set()

        for cat in CATEGORIES:
            cat_name = cat["name"]
            cat_path = cat["path"]
            page = 1
            consecutive_empty = 0
            category_products = 0

            logger.info(f"Scraping category: {cat_name}")

            while True:
                url = f"{ETSY_BASE}{cat_path}?page={page}&ref=search_ns"

                html = _sync_fetch(url, self._proxy, headers)
                if not html:
                    logger.warning(f"Failed to fetch {cat_name} page {page}")
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        logger.info(f"No response from {cat_name} after 3 attempts, stopping")
                        break
                    page += 1
                    continue

                page_products = self._extract_products_from_html(html, cat_name, seen_ids)

                if not page_products:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        logger.info(f"No more products in {cat_name} at page {page}")
                        break
                else:
                    consecutive_empty = 0
                    products.extend(page_products)
                    category_products += len(page_products)
                    logger.info(f"  {cat_name} page {page}: +{len(page_products)} (total: {category_products})")

                    if len(products) >= 100000:
                        logger.info(f"Reached 100K product cap")
                        return

                page += 1
                import time
                time.sleep(5)  # Polite delay to avoid rate limiting

        logger.info(f"Etsy US scraper complete: {len(products)} products")
