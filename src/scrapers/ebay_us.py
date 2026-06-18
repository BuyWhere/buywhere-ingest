"""eBay US marketplace scraper — target 200K products.

Uses Brightdata residential proxy + Playwright for JS rendering.
Target categories: electronics, fashion, collectibles, home, auto.
Focus on Buy It Now (LH_BIN=1) listings.
Tags: region=us, country_code=US, currency=USD.
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .base_scraper import BaseScraper, Product

logger = logging.getLogger(__name__)

EBAY_BASE = "https://www.ebay.com"
MERCHANT_ID = "ebay_us"
SOURCE = "ebay_us"
CURRENCY = "USD"
REGION = "us"
COUNTRY_CODE = "US"

CATEGORIES = [
    # Electronics
    {"id": "electronics_computers", "name": "Electronics", "keyword": "computers laptops", "max_pages": 100},
    {"id": "electronics_phones", "name": "Electronics", "keyword": "smartphone mobile phone", "max_pages": 100},
    {"id": "electronics_tablets", "name": "Electronics", "keyword": "tablets ipad e-reader", "max_pages": 100},
    {"id": "electronics_tv", "name": "Electronics", "keyword": "TV LED LCD television", "max_pages": 100},
    {"id": "electronics_cameras", "name": "Electronics", "keyword": "digital camera photography", "max_pages": 100},
    {"id": "electronics_gaming", "name": "Electronics", "keyword": "gaming console playstation xbox switch", "max_pages": 100},
    {"id": "electronics_headphones", "name": "Electronics", "keyword": "headphones earbuds wireless audio", "max_pages": 100},
    {"id": "electronics_watches", "name": "Electronics", "keyword": "smart watch fitness tracker", "max_pages": 100},
    # Fashion
    {"id": "fashion_women", "name": "Fashion", "keyword": "women clothing dress tops", "max_pages": 100},
    {"id": "fashion_men", "name": "Fashion", "keyword": "men clothing shirts pants", "max_pages": 100},
    {"id": "fashion_shoes", "name": "Fashion", "keyword": "shoes sneakers footwear", "max_pages": 100},
    {"id": "fashion_bags", "name": "Fashion", "keyword": "handbags purses bags", "max_pages": 100},
    {"id": "fashion_jewelry", "name": "Fashion", "keyword": "jewelry rings necklaces bracelet", "max_pages": 100},
    {"id": "fashion_watches", "name": "Fashion", "keyword": "watches wristwatches", "max_pages": 100},
    # Collectibles
    {"id": "collectibles_coins", "name": "Collectibles", "keyword": "coins collectible money", "max_pages": 100},
    {"id": "collectibles_cards", "name": "Collectibles", "keyword": "trading cards Pokemon Magic", "max_pages": 100},
    {"id": "collectibles_figurines", "name": "Collectibles", "keyword": "figurines anime collectibles", "max_pages": 100},
    {"id": "collectibles_vintage", "name": "Collectibles", "keyword": "vintage collectibles antiques", "max_pages": 100},
    # Home & Garden
    {"id": "home_furniture", "name": "Home & Garden", "keyword": "furniture home decor", "max_pages": 100},
    {"id": "home_kitchen", "name": "Home & Garden", "keyword": "kitchen appliances cookware", "max_pages": 100},
    # Auto
    {"id": "auto_parts", "name": "Auto", "keyword": "auto parts car accessories", "max_pages": 100},
]


def _load_residential_proxy() -> Optional[dict]:
    """Load Brightdata residential proxy dict for Playwright."""
    try:
        from .proxy_config import proxy_config_for_playwright, Zone
        return proxy_config_for_playwright(Zone.RESIDENTIAL_PROXY1)
    except Exception as e:
        logger.warning(f"Could not load Brightdata residential proxy: {e}")
        return None


KNOWN_BRANDS = [
    "Apple", "Samsung", "Sony", "LG", "Dell", "HP", "Lenovo", "Nike", "Adidas", "Zara",
    "H&M", "Uniqlo", "Canon", "Nikon", "Bose", "JBL", "Dyson", "KitchenAid", "Cuisinart",
    "Asus", "Acer", "Microsoft", "Google", "OnePlus", "Panasonic", "Sharp", "Toshiba",
    "Huawei", "Xiaomi", "Oppo", "Vivo", "Motorola", "TCL", "Hisense", "Polaroid",
    "Fujifilm", "Olympus", "GoPro", "DJI", "Fitbit", "Garmin", "Fossil", "Timex",
    "Seiko", "Casio", "Omega", "Rolex", "Levi's", "Champion", "Under Armour",
    "The North Face", "Patagonia", "Ralph Lauren", "Calvin Klein", "Tommy Hilfiger",
    "Michael Kors", "Coach", "kate spade", "Stuart Weitzman", "Vans", "Converse",
    "New Balance", "Puma", "Reebok", "ASICS", "Skechers", "Cole Haan", "Burberry",
    "Tiffany", "Cartier", "Pandora", "Swarovski", "Coleman", "Rover", "Kreg",
]


def _extract_brand(title: str) -> str:
    if not title:
        return ""
    title_lower = title.lower()
    for brand in KNOWN_BRANDS:
        if title_lower.startswith(brand.lower()) or f" {brand.lower()} " in title_lower or f" {brand.lower()}-" in title_lower:
            return brand
    return ""


class EbayUSScraper(BaseScraper):
    """Scraper for eBay US marketplace — Buy It Now listings."""

    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 3
    REQUEST_TIMEOUT = 60

    def __init__(self):
        super().__init__("eBay US", EBAY_BASE)
        self._proxy_config = _load_residential_proxy()
        self._products: List[Product] = []
        self._seen_ids: set[str] = set()
        self._total_scraped = 0
        self._outfile: Optional[str] = None
        self._output_dir = "/home/paperclip/buywhere-api/data/ebay_us"

    def _ensure_output_dir(self) -> None:
        import os
        os.makedirs(self._output_dir, exist_ok=True)

    @property
    def products_outfile(self) -> str:
        if self._outfile is None:
            self._ensure_output_dir()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._outfile = f"{self._output_dir}/ebay_us_{ts}.ndjson"
        return self._outfile

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        }

    async def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch URL using Playwright + Brightdata residential proxy."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed")
            return None

        proxy = self._proxy_config
        launch_options: Dict = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-web-security",
            ],
        }
        if proxy:
            launch_options["proxy"] = proxy

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(**launch_options)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                    viewport={"width": 1280, "height": 800},
                    locale="en-US",
                    extra_http_headers=self._get_headers(),
                )
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                    window.chrome = { runtime: {} };
                """)
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    await page.wait_for_timeout(3000)
                    html = await page.content()
                    return html
                except Exception as e:
                    logger.warning(f"Playwright navigation error for {url}: {e}")
                    return None
                finally:
                    await browser.close()
        except Exception as e:
            logger.warning(f"Playwright error for {url}: {e}")
            return None

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch URL with Playwright (JS rendering) + residential proxy."""
        for attempt in range(self.RETRY_ATTEMPTS):
            html = await self._fetch_with_playwright(url)
            if html and len(html) > 5000:
                return html
            logger.warning(f"Playwright attempt {attempt + 1} for {url} returned {len(html) if html else 0} bytes")
            if attempt < self.RETRY_ATTEMPTS - 1:
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
        return None

    def _extract_products_from_html(self, html: str, category: dict) -> List[dict]:
        """Extract products from eBay search results HTML using JSON-LD and regex patterns."""
        products = []

        # Try to extract from JSON-LD structured data
        jsonld_pattern = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)
        jsonld_matches = jsonld_pattern.findall(html)
        for match in jsonld_matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "ItemList":
                            for list_item in item.get("itemListElement", []):
                                product = self._parse_jsonld_product(list_item.get("item", {}), category)
                                if product:
                                    products.append(product)
                elif data.get("@type") == "Product":
                    product = self._parse_jsonld_product(data, category)
                    if product:
                        products.append(product)
            except (json.JSONDecodeError, Exception):
                continue

        # Fallback: extract from eBay's JavaScript data
        if not products:
            item_id_pattern = re.compile(r'"itemId"\s*:\s*"?(\d+)"?')
            title_pattern = re.compile(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"')
            price_pattern = re.compile(r'"price"\s*:\s*(\d+(?:\.\d+)?)')
            currency_pattern = re.compile(r'"currency"\s*:\s*"([A-Z]{3})"')
            url_pattern = re.compile(r'"productUrl"\s*:\s*"([^"]+)"')
            image_pattern = re.compile(r'"image"\s*:\s*"([^"]+)"')
            condition_pattern = re.compile(r'"condition"\s*:\s*"([^"]+)"')

            item_ids = item_id_pattern.findall(html)
            titles = title_pattern.findall(html)
            prices = price_pattern.findall(html)
            currencies = currency_pattern.findall(html)
            urls = url_pattern.findall(html)
            images = image_pattern.findall(html)
            conditions = condition_pattern.findall(html)

            for i in range(min(len(item_ids), 100)):
                try:
                    item_id = item_ids[i]
                    if item_id in self._seen_ids:
                        continue
                    self._seen_ids.add(item_id)

                    title = ""
                    if i < len(titles):
                        title = titles[i].replace('\\"', '"').replace('\\n', ' ').strip()
                    if not title:
                        title = f"eBay item {item_id}"

                    price = 0.0
                    if i < len(prices):
                        try:
                            price = float(prices[i])
                        except ValueError:
                            price = 0.0

                    currency = "USD"
                    if i < len(currencies):
                        currency = currencies[i]

                    url = f"{EBAY_BASE}/itm/{item_id}"
                    if i < len(urls) and urls[i]:
                        url = urls[i]

                    image_url = ""
                    if i < len(images) and images[i]:
                        image_url = images[i]

                    condition = "Unknown"
                    if i < len(conditions) and conditions[i]:
                        condition = conditions[i]

                    brand = _extract_brand(title)

                    products.append({
                        "sku": f"ebay_us_{item_id}",
                        "merchant_id": MERCHANT_ID,
                        "source": SOURCE,
                        "title": title,
                        "description": f"Condition: {condition}",
                        "price": price,
                        "currency": currency,
                        "url": url,
                        "image_url": image_url,
                        "category": category.get("name", ""),
                        "category_path": ["eBay US", category.get("name", "")],
                        "brand": brand,
                        "is_active": True,
                        "metadata": {
                            "item_id": item_id,
                            "condition": condition,
                            "listing_type": "FixedPrice",
                            "region": REGION,
                            "country_code": COUNTRY_CODE,
                        },
                    })
                except (IndexError, KeyError, ValueError):
                    continue

        return products

    def _parse_jsonld_product(self, data: dict, category: dict) -> Optional[dict]:
        """Parse a JSON-LD Product dict into catalog format."""
        try:
            item_id = str(data.get("sku") or data.get("productId", ""))
            if not item_id or item_id in self._seen_ids:
                return None
            # eBay item IDs are numeric
            if not item_id.isdigit():
                return None
            self._seen_ids.add(item_id)

            name = data.get("name", "")
            if not name:
                return None

            offers = data.get("offers", {})
            if isinstance(offers, dict):
                price = offers.get("price", 0)
                currency = offers.get("priceCurrency", "USD")
            else:
                price = 0
                currency = "USD"

            image = ""
            images = data.get("image", [])
            if isinstance(images, list) and images:
                image = str(images[0])
            elif isinstance(images, str):
                image = images

            url = data.get("url", f"{EBAY_BASE}/itm/{item_id}")
            brand = data.get("brand", {})
            if isinstance(brand, dict):
                brand = brand.get("name", _extract_brand(name))
            elif not brand:
                brand = _extract_brand(name)

            condition = data.get("description", "Unknown")

            return {
                "sku": f"ebay_us_{item_id}",
                "merchant_id": MERCHANT_ID,
                "source": SOURCE,
                "title": name,
                "description": str(condition),
                "price": float(price) if price else 0.0,
                "currency": str(currency),
                "url": str(url),
                "image_url": str(image),
                "category": category.get("name", ""),
                "category_path": ["eBay US", category.get("name", "")],
                "brand": str(brand) if brand else _extract_brand(name),
                "is_active": True,
                "metadata": {
                    "item_id": item_id,
                    "condition": str(condition),
                    "listing_type": "FixedPrice",
                    "region": REGION,
                    "country_code": COUNTRY_CODE,
                },
            }
        except Exception:
            return None

    def _write_products(self, products: List[dict]) -> None:
        """Append products to NDJSON output file."""
        if not products:
            return
        self._ensure_output_dir()
        with open(self.products_outfile, "a", encoding="utf-8") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")

    async def _scrape_impl(self, products: List[Product]) -> None:
        """Scrape all categories using Playwright."""
        proxy_status = "residential proxy configured" if self._proxy_config else "no proxy"
        logger.info(f"eBay US scraper starting ({proxy_status})")
        logger.info(f"Output: {self.products_outfile}")

        total = 0

        for cat in CATEGORIES:
            cat_name = cat["name"]
            keyword = cat["keyword"]
            max_pages = cat.get("max_pages", 100)
            page = 1
            consecutive_empty = 0
            category_products = 0

            logger.info(f"Scraping category: {cat_name} | keyword: {keyword}")

            while page <= max_pages:
                # Build Buy It Now search URL (LH_BIN=1 filters for Buy It Now)
                url = (
                    f"{EBAY_BASE}/sch/i.html"
                    f"?_nkw={keyword.replace(' ', '+')}"
                    f"&_pgn={page}"
                    f"&_ipg=60"
                    f"&LH_BIN=1"
                    f"&_sop=12"
                )

                html = await self.fetch(url)
                if not html:
                    consecutive_empty += 1
                    logger.warning(f"  {cat_name} page {page}: fetch failed")
                    if consecutive_empty >= 3:
                        logger.info(f"  {cat_name}: 3 consecutive failures, stopping")
                        break
                    page += 1
                    await asyncio.sleep(3)
                    continue

                page_products = self._extract_products_from_html(html, cat)

                if not page_products:
                    consecutive_empty += 1
                    logger.info(f"  {cat_name} page {page}: no products found")
                    if consecutive_empty >= 3:
                        logger.info(f"  {cat_name}: 3 consecutive empty pages, stopping")
                        break
                else:
                    consecutive_empty = 0
                    self._write_products(page_products)
                    products_raw = [Product(
                        name=p["title"],
                        price=str(p["price"]),
                        url=p["url"],
                        brand=p.get("brand"),
                        image_url=p.get("image_url"),
                        category=p.get("category"),
                        raw_data=p,
                    ) for p in page_products]
                    products.extend(products_raw)
                    category_products += len(page_products)
                    total += len(page_products)
                    self._total_scraped += len(page_products)
                    logger.info(f"  {cat_name} page {page}: +{len(page_products)} (category total: {category_products}, running total: {total})")

                    if total >= 200000:
                        logger.info(f"Reached 200K product target")
                        return

                page += 1
                await asyncio.sleep(2)  # Polite delay between pages

        logger.info(f"eBay US scraper complete: {total} products written to {self.products_outfile}")

    async def get_product_count(self) -> int:
        """Return total product count after scrape."""
        products = await self.scrape()
        return len(products)
