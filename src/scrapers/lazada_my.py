"""
Lazada Malaysia product scraper.

Scrapes Lazada MY categories and outputs structured NDJSON matching the
BuyWhere catalog schema for ingestion via POST /v1/ingest/products.

Usage:
    python -m scrapers.lazada_my --api-key <key> [--batch-size 100] [--delay 0.5]
    python -m scrapers.lazada_my --scrape-only  # save to NDJSON without ingesting

Categories covered across major verticals:
- Electronics: phones, laptops, TVs, audio, cameras, tablets, wearables, gaming
- Fashion: clothing, shoes, bags, watches, jewellery
- Home & Living: furniture, kitchen, bedding, decor, appliances
- Beauty & Health: skincare, makeup, personal care, supplements

Target: 50,000+ products across all categories, output as NDJSON.
"""

import argparse
import asyncio
import json
import os
import re
import time
from typing import Any

import httpx

try:
    import cloudscraper
except ModuleNotFoundError:
    cloudscraper = None

from .scraper_registry import register
from .scraper_logging import get_logger

MERCHANT_ID = "lazada_my"
SOURCE = "lazada_my"
BASE_URL = "https://www.lazada.com.my"
OUTPUT_DIR = "/home/paperclip/buywhere-api/data/lazada-my"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-MY,en;q=0.9",
    "Referer": "https://www.lazada.com.my/",
}

CATEGORIES = [
    {"id": "phones", "name": "Electronics", "sub": "Mobile Phones", "url": "https://www.lazada.com.my/phones/", "target": 5000},
    {"id": "laptops", "name": "Electronics", "sub": "Laptops", "url": "https://www.lazada.com.my/laptops/", "target": 4000},
    {"id": "tvs", "name": "Electronics", "sub": "TVs", "url": "https://www.lazada.com.my/tvs/", "target": 3000},
    {"id": "tablets", "name": "Electronics", "sub": "Tablets", "url": "https://www.lazada.com.my/tablets/", "target": 3000},
    {"id": "audio", "name": "Electronics", "sub": "Audio & Headphones", "url": "https://www.lazada.com.my/audio-headphones/", "target": 4000},
    {"id": "cameras", "name": "Electronics", "sub": "Cameras", "url": "https://www.lazada.com.my/cameras/", "target": 2500},
    {"id": "wearables", "name": "Electronics", "sub": "Smart Wearables", "url": "https://www.lazada.com.my/smart-wearables/", "target": 3000},
    {"id": "gaming", "name": "Electronics", "sub": "Gaming", "url": "https://www.lazada.com.my/gaming/", "target": 3500},
    {"id": "mobile-accessories", "name": "Electronics", "sub": "Mobile Accessories", "url": "https://www.lazada.com.my/mobile-accessories/", "target": 4000},
    {"id": "computer-accessories", "name": "Electronics", "sub": "Computer Accessories", "url": "https://www.lazada.com.my/computer-accessories/", "target": 3500},
    {"id": "smart-home", "name": "Electronics", "sub": "Smart Home", "url": "https://www.lazada.com.my/smart-home/", "target": 2500},

    {"id": "women-tops", "name": "Fashion", "sub": "Women's Tops", "url": "https://www.lazada.com.my/women-tops/", "target": 3000},
    {"id": "women-dresses", "name": "Fashion", "sub": "Women's Dresses", "url": "https://www.lazada.com.my/women-dresses/", "target": 3000},
    {"id": "women-pants", "name": "Fashion", "sub": "Women's Pants & Shorts", "url": "https://www.lazada.com.my/women-pants-shorts/", "target": 2500},
    {"id": "women-shoes", "name": "Fashion", "sub": "Women's Shoes", "url": "https://www.lazada.com.my/women-shoes/", "target": 3000},
    {"id": "women-bags", "name": "Fashion", "sub": "Women's Bags", "url": "https://www.lazada.com.my/women-bags/", "target": 3000},
    {"id": "men-tops", "name": "Fashion", "sub": "Men's Tops", "url": "https://www.lazada.com.my/men-tops/", "target": 2500},
    {"id": "men-pants", "name": "Fashion", "sub": "Men's Pants", "url": "https://www.lazada.com.my/men-pants/", "target": 2500},
    {"id": "men-shoes", "name": "Fashion", "sub": "Men's Shoes", "url": "https://www.lazada.com.my/men-shoes/", "target": 2500},
    {"id": "men-watches", "name": "Fashion", "sub": "Men's Watches", "url": "https://www.lazada.com.my/men-watches/", "target": 2000},
    {"id": "jewellery", "name": "Fashion", "sub": "Jewellery", "url": "https://www.lazada.com.my/jewellery/", "target": 2000},
    {"id": "eyewear", "name": "Fashion", "sub": "Eyewear", "url": "https://www.lazada.com.my/eyewear/", "target": 2000},
    {"id": "luggage", "name": "Fashion", "sub": "Luggage & Travel", "url": "https://www.lazada.com.my/luggage/", "target": 2000},

    {"id": "furniture", "name": "Home & Living", "sub": "Furniture", "url": "https://www.lazada.com.my/furniture/", "target": 3000},
    {"id": "kitchen", "name": "Home & Living", "sub": "Kitchen & Dining", "url": "https://www.lazada.com.my/kitchen-dining/", "target": 3000},
    {"id": "bedding", "name": "Home & Living", "sub": "Bedding & Bath", "url": "https://www.lazada.com.my/bedding-bath/", "target": 2000},
    {"id": "home-decor", "name": "Home & Living", "sub": "Home Decor", "url": "https://www.lazada.com.my/home-decor/", "target": 2500},
    {"id": "home-appliances", "name": "Home & Living", "sub": "Home Appliances", "url": "https://www.lazada.com.my/home-appliances/", "target": 3000},
    {"id": "storage", "name": "Home & Living", "sub": "Storage & Organization", "url": "https://www.lazada.com.my/storage-organization/", "target": 2000},
    {"id": "cleaning", "name": "Home & Living", "sub": "Cleaning & Laundry", "url": "https://www.lazada.com.my/cleaning-laundry/", "target": 1500},

    {"id": "skincare", "name": "Beauty & Health", "sub": "Skincare", "url": "https://www.lazada.com.my/skincare/", "target": 3000},
    {"id": "makeup", "name": "Beauty & Health", "sub": "Makeup", "url": "https://www.lazada.com.my/makeup/", "target": 3000},
    {"id": "personal-care", "name": "Beauty & Health", "sub": "Personal Care", "url": "https://www.lazada.com.my/personal-care/", "target": 2000},
    {"id": "hair-care", "name": "Beauty & Health", "sub": "Hair Care", "url": "https://www.lazada.com.my/hair-care/", "target": 2000},
    {"id": "supplements", "name": "Beauty & Health", "sub": "Health Supplements", "url": "https://www.lazada.com.my/health-supplements/", "target": 2500},
    {"id": "fragrances", "name": "Beauty & Health", "sub": "Fragrances", "url": "https://www.lazada.com.my/fragrances/", "target": 1500},
    {"id": "bath-body", "name": "Beauty & Health", "sub": "Bath & Body", "url": "https://www.lazada.com.my/bath-body/", "target": 2000},
]


@register("lazada_my")
class LazadaMYScraper:
    MERCHANT_ID = MERCHANT_ID
    SOURCE = SOURCE
    BASE_URL = BASE_URL
    DEFAULT_HEADERS = HEADERS

    def __init__(
        self,
        api_key: str,
        api_base: str = "http://localhost:8000",
        batch_size: int = 100,
        delay: float = 0.5,
        data_dir: str = OUTPUT_DIR,
        limit: int = 0,
        scrape_only: bool = False,
        max_concurrent: int = 4,
        target_products: int = 50000,
        max_pages_per_category: int = 200,
        scraperapi_key: str | None = None,
        extract_gtin: bool = False,
        category_filter: str | None = None,
    ):
        self.max_concurrent = max_concurrent
        self.target_products = target_products
        self.max_pages_per_category = max_pages_per_category
        self.scraperapi_key = scraperapi_key or os.environ.get("SCRAPERAPI_KEY")
        self.extract_gtin = extract_gtin
        self._category_filter = self._normalize_category_filter(category_filter)
        self._semaphore: asyncio.Semaphore | None = None
        self._products_outfile: str | None = None
        self._playwright = None
        self._browser = None
        self._scraper: Any | None = None
        self.api_key = api_key
        self.api_base = api_base
        self.batch_size = batch_size
        self.delay = delay
        self.limit = limit
        self.log = get_logger(SOURCE)
        self.scrape_only = scrape_only
        self.client = httpx.AsyncClient(timeout=30.0, headers=self.DEFAULT_HEADERS)
        self.total_scraped = 0
        self.total_ingested = 0
        self.total_updated = 0
        self.total_failed = 0
        self._ensure_output_dir()
        if cloudscraper is None:
            if not self.scraperapi_key:
                self.log.progress("cloudscraper is unavailable and no scraperapi key is configured; API fetches will be skipped.")
        else:
            self._scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "desktop": True},
                delay=10,
            )

    @staticmethod
    def _normalize_category_filter(raw: str | None) -> list[str]:
        if not raw:
            return []
        values: list[str] = []
        for item in raw.replace(";", ",").split(","):
            normalized = item.strip().lower()
            if normalized:
                values.append(normalized)
        return values

    def _category_matches_filter(self, category: dict) -> bool:
        if not self._category_filter:
            return True
        candidates = {
            str(category.get("id", "")).lower(),
            str(category.get("name", "")).lower(),
            str(category.get("sub", "")).lower(),
            str(category.get("slug", "")).lower(),
        }
        return any(f in c for c in candidates for f in self._category_filter) or any(
            f in candidates for f in self._category_filter
        )

    async def _init_playwright(self):
        if self._playwright is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)

    async def _close_playwright(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def _ensure_output_dir(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._products_outfile = os.path.join(OUTPUT_DIR, f"products_{ts}.ndjson")

    @property
    def products_outfile(self) -> str:
        if self._products_outfile is None:
            ts = time.strftime("%Y%m%d_%H%M%S")
            self._products_outfile = os.path.join(OUTPUT_DIR, f"products_{ts}.ndjson")
        return self._products_outfile

    def get_categories(self) -> list[dict]:
        if not self._category_filter:
            return CATEGORIES
        selected = [category for category in CATEGORIES if self._category_matches_filter(category)]
        if not selected:
            self.log.progress(
                "No categories matched category filter: "
                + ", ".join(self._category_filter)
            )
        return selected

    def _build_scraperapi_url(self, url: str, params: dict | None = None) -> str:
        import urllib.parse
        if params:
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
        else:
            full_url = url
        encoded_url = urllib.parse.quote(full_url, safe="")
        proxy_url = f"http://api.scraperapi.com?api_key={self.scraperapi_key}&url={encoded_url}&render=true"
        return proxy_url

    async def _get_with_retry_cloudscraper(
        self,
        url: str,
        params: dict | None = None,
    ) -> str | None:
        if self._scraper is None and not self.scraperapi_key:
            self.log.progress("Skipping HTTP fetch: cloudscraper is not configured and no ScraperAPI key is set.")
            return None
        if self.scraperapi_key:
            return await self._get_with_scraperapi(url, params)
        for attempt in range(self.max_retries):
            try:
                if params:
                    resp = self._scraper.get(url, params=params)
                else:
                    resp = self._scraper.get(url)
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code in (429, 503):
                    wait = 2 ** attempt * 5
                    self.log.progress(f"Rate limited (HTTP {resp.status_code}), waiting {wait}s")
                    time.sleep(wait)
                else:
                    self.log.request_failed(url, attempt, f"HTTP {resp.status_code}")
                    if attempt < self.max_retries - 1:
                        wait = 2 ** attempt
                        time.sleep(wait)
                    else:
                        return None
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
                else:
                    self.log.network_error(url, str(e))
                    return None
        return None

    async def _get_with_scraperapi(self, url: str, params: dict | None = None) -> str | None:
        proxy_url = self._build_scraperapi_url(url, params)
        for attempt in range(self.max_retries):
            try:
                resp = self._scraper.get(proxy_url)
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code in (429, 503):
                    wait = 2 ** attempt * 5
                    self.log.progress(f"ScraperAPI rate limited (HTTP {resp.status_code}), waiting {wait}s")
                    time.sleep(wait)
                else:
                    self.log.request_failed(proxy_url, attempt, f"HTTP {resp.status_code}")
                    if attempt < self.max_retries - 1:
                        wait = 2 ** attempt
                        time.sleep(wait)
                    else:
                        return None
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
                else:
                    self.log.network_error(proxy_url, str(e))
                    return None
        return None

    async def _fetch_with_playwright(self, url: str, params: dict | None = None) -> str | None:
        try:
            await self._init_playwright()
            full_url = url
            if params:
                import urllib.parse
                query = urllib.parse.urlencode(params)
                full_url = f"{url}?{query}"
            page = await self._browser.new_page()
            await page.goto(full_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            content = await page.content()
            await page.close()
            return content
        except Exception as e:
            self.log.progress(f"Playwright unavailable for {url}: {e}")
            return None

    async def fetch_page(self, category: dict, page: int) -> list[dict]:
        url = f"{BASE_URL}/cat/geelhoed?ajax=true&page={page}"
        params = {
            "categoryId": category["id"],
            "page": page,
        }
        text = await self._fetch_with_playwright(url, params)
        if text:
            try:
                data = json.loads(text)
                return self._extract_products_from_response(data, category)
            except json.JSONDecodeError:
                pass
        text = await self._get_with_retry_cloudscraper(url, params)
        if text:
            try:
                data = json.loads(text)
                return self._extract_products_from_response(data, category)
            except json.JSONDecodeError:
                return self._extract_products_from_html(text, category)
        return await self._fetch_search_api_fallback(category, page)

    async def _fetch_search_api_fallback(self, category: dict, page: int = 1) -> list[dict]:
        url = f"{BASE_URL}/search"
        params = {
            "q": category["sub"].replace("&", ""),
            "page": page,
        }
        try:
            text = await self._get_with_retry_cloudscraper(url, params=params)
            if text is None:
                return []
            return self._extract_products_from_html(text, category)
        except Exception:
            return []

    def _extract_products_from_response(self, data: dict, category: dict) -> list[dict]:
        products = []
        try:
            items = data.get("data", {}).get("products", [])
            if items:
                for item in items:
                    products.append(item)
                return products
        except (KeyError, TypeError):
            pass
        try:
            items = data.get("products", [])
            if items:
                for item in items:
                    products.append(item)
                return products
        except (KeyError, TypeError):
            pass
        try:
            items = data.get("mods", {}).get("productItems", [])
            if items:
                for item in items:
                    products.append(item)
                return products
        except (KeyError, TypeError):
            pass
        try:
            items = data.get("items", [])
            if items:
                for item in items:
                    products.append(item)
                return products
        except (KeyError, TypeError):
            pass
        return products

    def _extract_products_from_html(self, html: str, category: dict) -> list[dict]:
        products = []
        script_pattern = r'window\.DS\.conf\s*=\s*(\{.*?\});'
        match = re.search(script_pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                items = data.get("data", {}).get("products", [])
                for item in items:
                    products.append(item)
                if items:
                    return products
            except (json.JSONDecodeError, KeyError):
                pass
        script_pattern2 = r'"products":\s*(\[.*?\])'
        match = re.search(script_pattern2, html, re.DOTALL)
        if match:
            try:
                items = json.loads(match.group(1))
                for item in items:
                    products.append(item)
                if items:
                    return products
            except json.JSONDecodeError:
                pass
        script_pattern3 = r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});'
        match = re.search(script_pattern3, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                items = data.get("products", {}).get("products", [])
                for item in items:
                    products.append(item)
                if items:
                    return products
            except (json.JSONDecodeError, KeyError):
                pass
        return products

    def transform(self, raw: dict, category: dict) -> dict[str, Any] | None:
        try:
            sku = str(raw.get("productId", "") or raw.get("sku", "") or raw.get("itemId", "") or "")
            if not sku:
                return None

            name = raw.get("name", "") or raw.get("title", "") or raw.get("productTitle", "") or ""
            if not name:
                return None

            price = raw.get("price", 0.0)
            if isinstance(price, str):
                price = float(price.replace("RM", "").replace("$", "").replace(",", "") or 0)
            elif isinstance(price, int):
                price = float(price) / 100000.0 if price > 100000 else float(price)
            original_price = raw.get("originalPrice", price)
            if isinstance(original_price, str):
                original_price = float(original_price.replace("RM", "").replace("$", "").replace(",", "") or 0)
            elif isinstance(original_price, int) and original_price > 100000:
                original_price = float(original_price) / 100000.0

            discount = raw.get("discount", "0")
            if discount:
                discount = int(str(discount).replace("%", "") or 0)
            else:
                discount = 0

            images = raw.get("images", []) or raw.get("imageUrl", "") or []
            image_url = ""
            if isinstance(images, list) and images:
                image_url = images[0] if isinstance(images[0], str) else ""
            elif isinstance(images, str) and images:
                image_url = images

            product_url = raw.get("productUrl", "") or raw.get("url", "") or raw.get("product_url", "")
            if product_url and not product_url.startswith("http"):
                product_url = BASE_URL + product_url

            brand = raw.get("brand", "") or raw.get("brandName", "") or raw.get("productBrand", "") or ""
            rating = float(raw.get("rating", 0.0) or 0)
            review_count = int(raw.get("review", 0) or raw.get("reviewCount", 0) or raw.get("ratingCount", 0) or 0)

            primary_category = category["name"]
            sub_category = category["sub"]
            category_path = [category["name"], category["sub"]]

            seller = raw.get("seller", {}) or raw.get("sellerInfo", {}) or {}
            if isinstance(seller, dict):
                seller_name = seller.get("name", "") or seller.get("shopName", "") or seller.get("sellerName", "") or ""
            else:
                seller_name = str(seller) if seller else ""

            location = raw.get("location", "") or raw.get("location", "") or ""

            return {
                "sku": sku,
                "gtin": raw.get("gtin13") or raw.get("gtin") or "",
                "mpn": raw.get("mpn") or "",
                "merchant_id": MERCHANT_ID,
                "title": name,
                "description": raw.get("description", "") or raw.get("productDescription", "") or "",
                "price": price,
                "currency": "MYR",
                "url": product_url,
                "image_url": image_url,
                "category": primary_category,
                "category_path": category_path,
                "brand": brand,
                "is_active": True,
                "metadata": {
                    "original_price": original_price,
                    "discount_pct": discount,
                    "rating": rating,
                    "review_count": review_count,
                    "subcategory": sub_category,
                    "seller_name": seller_name,
                    "location": location,
                    "lazada_category_id": raw.get("categoryId", ""),
                    "vertical": primary_category,
                    "source": SOURCE,
                },
            }
        except Exception:
            return None

    async def scrape_category(self, category: dict) -> dict[str, int]:
        async with self._semaphore:
            cat_id = category["id"]
            cat_name = category["name"]
            sub_name = category["sub"]
            target = category.get("target", 2000)

            self.log.progress(f"[{cat_name} / {sub_name}] Starting scrape... (target: {target})")
            counts: dict[str, int] = {"scraped": 0, "ingested": 0, "updated": 0, "failed": 0, "pages": 0}
            page = 1
            batch: list[dict] = []
            consecutive_empty = 0

            while consecutive_empty < 5 and page <= self.max_pages_per_category:
                if self.limit > 0 and self.total_scraped >= self.limit:
                    self.log.progress(f"Product limit {self.limit} reached!")
                    break
                if self.total_scraped >= self.target_products:
                    self.log.progress(f"Target total {self.target_products} reached!")
                    break

                products_raw = await self.fetch_page(category, page)

                if not products_raw:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        self.log.progress(f"No products for 3 consecutive pages, ending pagination for {cat_id}")
                        break
                    page += 1
                    await asyncio.sleep(self.delay)
                    continue

                consecutive_empty = 0
                counts["pages"] += 1

                for raw in products_raw:
                    if self.limit > 0 and self.total_scraped >= self.limit:
                        break
                    if self.total_scraped >= self.target_products:
                        break
                    try:
                        transformed = self.transform(raw, category)
                    except Exception as e:
                        self.log.transform_error(None, f"{type(e).__name__}: {e}")
                        continue

                    if transformed:
                        batch.append(transformed)
                        counts["scraped"] += 1
                        self.total_scraped += 1

                        if len(batch) >= self.batch_size:
                            i, u, f = await self.ingest_batch(batch)
                            counts["ingested"] += i
                            counts["updated"] += u
                            counts["failed"] += f
                            self.total_ingested += i
                            self.total_updated += u
                            self.total_failed += f
                            batch = []
                            await asyncio.sleep(self.delay)

                self.log.progress(f"  page={page}, scraped={counts['scraped']}, total={self.total_scraped}")

                if len(products_raw) < 40:
                    break

                page += 1
                await asyncio.sleep(self.delay)

            if batch:
                i, u, f = await self.ingest_batch(batch)
                counts["ingested"] += i
                counts["updated"] += u
                counts["failed"] += f
                self.total_ingested += i
                self.total_updated += u
                self.total_failed += f

            self.log.progress(f"[{cat_name} / {sub_name}] Done: {counts}")
            return counts

    async def run(self) -> dict[str, Any]:
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        mode = "scrape only" if self.scrape_only else f"API: {self.api_base}"
        selected_categories = self.get_categories()
        self.log.progress(f"Lazada MY Scraper starting...")
        self.log.progress(f"Mode: {mode}")
        self.log.progress(f"Batch size: {self.batch_size}, Delay: {self.delay}s, Max concurrent: {self.max_concurrent}")
        self.log.progress(f"Output: {self.products_outfile}")
        self.log.progress(f"Categories selected: {len(selected_categories)}")
        if self._category_filter:
            self.log.progress("Category filter: " + ", ".join(self._category_filter))
        self.log.progress(f"Target: {self.target_products} products")

        start = time.time()

        tasks = [self.scrape_category(cat) for cat in selected_categories]
        await asyncio.gather(*tasks)

        elapsed = time.time() - start

        summary = {
            "elapsed_seconds": round(elapsed, 1),
            "total_scraped": self.total_scraped,
            "total_ingested": self.total_ingested,
            "total_updated": self.total_updated,
            "total_failed": self.total_failed,
            "output_file": self.products_outfile,
            "target": self.target_products,
            "categories_covered": len(selected_categories),
        }

        self.log.progress(f"Scraper complete: {summary}")
        return summary

    async def close(self) -> None:
        await self._close_playwright()
        await self.client.aclose()

    async def _scrape_impl(self, products: list) -> None:
        """Not used — LazadaMYScraper uses its own run() method."""
        pass

    @classmethod
    def add_cli_args(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--api-key", required=True, help="BuyWhere API key")
        parser.add_argument("--api-base", default="http://localhost:8000", help="BuyWhere API base URL")
        parser.add_argument("--batch-size", type=int, default=100, help="Batch size for ingestion")
        parser.add_argument("--delay", type=float, default=0.5, help="Delay between pages (seconds)")
        parser.add_argument("--data-dir", default=OUTPUT_DIR, help="Directory to save scraped NDJSON data")
        parser.add_argument("--limit", type=int, default=0, help="Maximum number of products to scrape (0 = unlimited)")
        parser.add_argument("--scrape-only", action="store_true", help="Save to NDJSON without ingesting")
        parser.add_argument("--max-concurrent", type=int, default=4, help="Max concurrent category scrapes")
        parser.add_argument("--target", type=int, default=50000, help="Target number of products")
        parser.add_argument("--max-pages", type=int, default=200, help="Max pages per category")
        parser.add_argument("--scraperapi-key", default=None, help="ScraperAPI key for anti-bot bypass (or set SCRAPERAPI_KEY env var)")
        parser.add_argument(
            "--categories",
            default=None,
            help="Comma or semicolon-separated category filters (match category id/name/sub).",
        )
        parser.add_argument("--extract-gtin", action="store_true", help="Fetch product pages to extract GTIN/EAN/UPC from JSON-LD")

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "LazadaMYScraper":
        return cls(
            api_key=args.api_key,
            api_base=args.api_base,
            batch_size=args.batch_size,
            delay=args.delay,
            data_dir=args.data_dir,
            limit=args.limit,
            scrape_only=args.scrape_only,
            max_concurrent=args.max_concurrent,
            target_products=args.target,
            max_pages_per_category=args.max_pages,
            scraperapi_key=args.scraperapi_key,
            extract_gtin=args.extract_gtin,
            category_filter=args.categories,
        )


async def main():
    parser = argparse.ArgumentParser(description="Lazada MY Scraper")
    LazadaMYScraper.add_cli_args(parser)
    args = parser.parse_args()
    scraper = LazadaMYScraper.from_args(args)
    try:
        await scraper.run()
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
