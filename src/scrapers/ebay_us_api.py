"""eBay US scraper — Finding API (production AppID) path.

Target 200K Buy-It-Now products. Uses the free eBay Finding API
(`findItemsAdvanced`) with the `SECURITY-APPNAME` query param.

Why this exists alongside `ebay_us.py` (Playwright + Brightdata):
  * No residential proxy, no Playwright deps, no rate-limit dance
  * 5,000 free calls/day on a production AppID; 20 keywords x 100 pages = 2,000
  * Returns clean JSON (vs HTML/JSON-LD scraping)
  * Activates only when `EBAY_APP_ID` env var is set; otherwise no-ops so the
    rest of `run_scrapers.py` keeps working.

Unblock: BUY-52338 (production AppID).
"""

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlencode

from .base_scraper import BaseScraper, Product

logger = logging.getLogger(__name__)

EBAY_FINDING_URL = "http://svcs.ebay.com/services/search/FindingService/v1"
MERCHANT_ID = "ebay_us_api"
SOURCE = "ebay_us_api"
CURRENCY = "USD"
REGION = "us"
COUNTRY_CODE = "US"

# Public eBay global ID for the US site.
GLOBAL_ID = "EBAY-US"

# Cap: 20 keywords * 100 pages = 2,000 calls (under 5,000/day production cap).
PAGES_PER_KEYWORD = 100
ENTRIES_PER_PAGE = 100  # max 100
TARGET_TOTAL = 200_000
KEYWORD_DELAY_SECONDS = 1.0  # polite

# Mirrors the categories from `ebay_us.py` so the catalog has the same shape
# regardless of which lane filled it. Each entry is a free-text keyword that
# `findItemsAdvanced` will run against Buy It Now listings.
KEYWORDS: List[Dict] = [
    {"id": "electronics_laptops", "name": "Electronics", "keyword": "laptop computer"},
    {"id": "electronics_phones", "name": "Electronics", "keyword": "smartphone mobile phone"},
    {"id": "electronics_tablets", "name": "Electronics", "keyword": "tablet ipad e-reader"},
    {"id": "electronics_tv", "name": "Electronics", "keyword": "television led lcd"},
    {"id": "electronics_cameras", "name": "Electronics", "keyword": "digital camera"},
    {"id": "electronics_gaming", "name": "Electronics", "keyword": "gaming console playstation xbox nintendo"},
    {"id": "electronics_headphones", "name": "Electronics", "keyword": "headphones earbuds wireless"},
    {"id": "electronics_watches", "name": "Electronics", "keyword": "smartwatch fitness tracker"},
    {"id": "fashion_women", "name": "Fashion", "keyword": "women clothing dress"},
    {"id": "fashion_men", "name": "Fashion", "keyword": "men clothing shirt"},
    {"id": "fashion_shoes", "name": "Fashion", "keyword": "shoes sneakers"},
    {"id": "fashion_bags", "name": "Fashion", "keyword": "handbag purse bag"},
    {"id": "fashion_jewelry", "name": "Fashion", "keyword": "jewelry ring necklace bracelet"},
    {"id": "fashion_watches", "name": "Fashion", "keyword": "wristwatch"},
    {"id": "collectibles_coins", "name": "Collectibles", "keyword": "collectible coin"},
    {"id": "collectibles_cards", "name": "Collectibles", "keyword": "trading card pokemon magic"},
    {"id": "collectibles_figurines", "name": "Collectibles", "keyword": "anime figurine collectible"},
    {"id": "collectibles_vintage", "name": "Collectibles", "keyword": "vintage antique collectible"},
    {"id": "home_furniture", "name": "Home & Garden", "keyword": "furniture home decor"},
    {"id": "home_kitchen", "name": "Home & Garden", "keyword": "kitchen appliance cookware"},
]

KNOWN_BRANDS = [
    "Apple", "Samsung", "Sony", "LG", "Dell", "HP", "Lenovo", "Nike", "Adidas",
    "Zara", "H&M", "Uniqlo", "Canon", "Nikon", "Bose", "JBL", "Dyson",
    "KitchenAid", "Cuisinart", "Asus", "Acer", "Microsoft", "Google", "OnePlus",
    "Panasonic", "Sharp", "Toshiba", "Huawei", "Xiaomi", "Oppo", "Vivo",
    "Motorola", "TCL", "Hisense", "Polaroid", "Fujifilm", "Olympus", "GoPro",
    "DJI", "Fitbit", "Garmin", "Fossil", "Timex", "Seiko", "Casio", "Omega",
    "Rolex", "Champion", "Under Armour", "North Face", "Patagonia",
    "Ralph Lauren", "Calvin Klein", "Tommy Hilfiger", "Michael Kors", "Coach",
    "kate spade", "Vans", "Converse", "New Balance", "Puma", "Reebok", "ASICS",
    "Skechers", "Burberry", "Tiffany", "Cartier", "Pandora", "Swarovski",
]


def _extract_brand(title: str) -> str:
    if not title:
        return ""
    title_lower = title.lower()
    for brand in KNOWN_BRANDS:
        bl = brand.lower()
        if title_lower.startswith(bl) or f" {bl} " in title_lower or f" {bl}-" in title_lower:
            return brand
    return ""


class EbayUSApiScraper(BaseScraper):
    """Scraper for eBay US via the Finding API.

    Reads `EBAY_APP_ID` from the environment on construction. If it is missing
    or empty, the scraper logs a single warning and `_scrape_impl` becomes a
    no-op (zero products). This is intentional: the rest of `run_scrapers.py`
    keeps running and the unblock owner (Rich) sees a clear "credential
    missing" log line.
    """

    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 3
    REQUEST_TIMEOUT = 30

    def __init__(self):
        super().__init__("eBay US (Finding API)", EBAY_FINDING_URL)
        self._app_id: Optional[str] = os.environ.get("EBAY_APP_ID", "").strip() or None
        self._products: List[Product] = []
        self._seen_ids: set[str] = set()
        self._total_scraped = 0
        self._outfile: Optional[str] = None
        self._output_dir = "/home/paperclip/buywhere-api/data/ebay_us_api"
        if not self._app_id:
            logger.warning(
                "EBAY_APP_ID not set — ebay_us_api scraper will be a no-op. "
                "Unblock: BUY-52338 (production AppID)."
            )

    @property
    def is_active(self) -> bool:
        """True when the AppID is configured and the scraper can run."""
        return bool(self._app_id)

    def _ensure_output_dir(self) -> None:
        import os
        os.makedirs(self._output_dir, exist_ok=True)

    @property
    def products_outfile(self) -> str:
        if self._outfile is None:
            self._ensure_output_dir()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._outfile = f"{self._output_dir}/ebay_us_api_{ts}.ndjson"
        return self._outfile

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.15",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _build_request_url(self, keyword: str, page: int) -> str:
        params = {
            "OPERATION-NAME": "findItemsAdvanced",
            "SECURITY-APPNAME": self._app_id or "",
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "",
            "globalId": GLOBAL_ID,
            "keywords": keyword,
            "paginationInput.entriesPerPage": str(ENTRIES_PER_PAGE),
            "paginationInput.pageNumber": str(page),
            # Buy It Now only — mirrors the Playwright path's `LH_BIN=1`.
            "itemFilter(0).name": "ListingType",
            "itemFilter(0).value(0)": "FixedPrice",
            # US-only site exposure.
            "itemFilter(1).name": "Site",
            "itemFilter(1).value(0)": "US",
            # Hide auction noise that some categories leak through.
            "itemFilter(2).name": "HideDuplicateItems",
            "itemFilter(2).value(0)": "true",
        }
        # urlencode keeps the brackets intact.
        return f"{EBAY_FINDING_URL}?{urlencode(params)}"

    async def _call_finding_api(self, keyword: str, page: int) -> Optional[dict]:
        """Call the Finding API with retries. Returns parsed JSON or None."""
        if not self._app_id:
            return None
        url = self._build_request_url(keyword, page)
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                if self.session is None:
                    # BaseScraper only opens the session in __aenter__; in
                    # case someone calls .scrape() directly, fall back to a
                    # one-off client.
                    import httpx
                    async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT, headers=self._get_headers()) as client:
                        resp = await client.get(url, follow_redirects=True)
                else:
                    resp = await self.session.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    return resp.json()
                # The Finding API quota errors come back as 5xx with an
                # ack=Failure envelope; treat as retryable.
                logger.warning(
                    "Finding API HTTP %s for keyword=%r page=%d (attempt %d/%d)",
                    resp.status_code, keyword, page, attempt + 1, self.RETRY_ATTEMPTS,
                )
                if resp.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                return None
            except Exception as e:
                logger.warning(
                    "Finding API error for keyword=%r page=%d (attempt %d/%d): %s",
                    keyword, page, attempt + 1, self.RETRY_ATTEMPTS, e,
                )
                if attempt < self.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
        return None

    @staticmethod
    def _parse_items(payload: dict) -> List[dict]:
        """Pull the item array out of the Finding API envelope."""
        if not payload:
            return []
        try:
            resp = (
                payload.get("findItemsAdvancedResponse", [{}])[0]
                if isinstance(payload.get("findItemsAdvancedResponse"), list)
                else payload.get("findItemsAdvancedResponse", {})
            )
            search_result = (
                resp.get("searchResult", [{}])[0]
                if isinstance(resp.get("searchResult"), list)
                else resp.get("searchResult", {})
            )
            items = search_result.get("item", [])
            if isinstance(items, list):
                return items
            return [items] if items else []
        except (AttributeError, TypeError):
            return []

    def _normalize_item(self, item: dict, category: Dict) -> Optional[Dict]:
        """Map a Finding API item to the catalog row shape."""
        try:
            item_id = str(item.get("itemId", [""])[0] if isinstance(item.get("itemId"), list) else item.get("itemId", ""))
            if not item_id or item_id in self._seen_ids:
                return None
            self._seen_ids.add(item_id)

            title = (
                item.get("title", [""])[0]
                if isinstance(item.get("title"), list) else item.get("title", "")
            )
            if not title:
                return None

            url = (
                item.get("viewItemURL", [""])[0]
                if isinstance(item.get("viewItemURL"), list) else item.get("viewItemURL", "")
            )

            gallery = (
                item.get("galleryURL", [""])[0]
                if isinstance(item.get("galleryURL"), list) else item.get("galleryURL", "")
            )

            selling_status = item.get("sellingStatus", [])
            if not isinstance(selling_status, list):
                selling_status = [selling_status]
            current = selling_status[0] if selling_status else {}
            current_price = current.get("currentPrice", [{}])[0] if isinstance(current.get("currentPrice"), list) else current.get("currentPrice", {})
            if not isinstance(current_price, dict):
                current_price = {}
            price_val = current_price.get("__value__", "0")
            currency = current_price.get("@currencyId", "USD")
            try:
                price = float(price_val)
            except (TypeError, ValueError):
                price = 0.0

            condition = (
                (item.get("condition", [{}])[0] if isinstance(item.get("condition"), list) else item.get("condition", {}))
                .get("conditionDisplayName", [""])[0]
                if isinstance((item.get("condition", [{}])[0] if isinstance(item.get("condition"), list) else item.get("condition", {})).get("conditionDisplayName"), list)
                else (item.get("condition", [{}])[0] if isinstance(item.get("condition"), list) else item.get("condition", {})).get("conditionDisplayName", "")
            ) or "Unknown"

            primary_cat = item.get("primaryCategory", [{}])[0] if isinstance(item.get("primaryCategory"), list) else item.get("primaryCategory", {})
            primary_cat_id = primary_cat.get("categoryId", [""])[0] if isinstance(primary_cat.get("categoryId"), list) else primary_cat.get("categoryId", "")
            primary_cat_name = primary_cat.get("categoryName", [""])[0] if isinstance(primary_cat.get("categoryName"), list) else primary_cat.get("categoryName", "")

            brand = _extract_brand(title)

            return {
                "sku": f"ebay_us_api_{item_id}",
                "merchant_id": MERCHANT_ID,
                "source": SOURCE,
                "title": str(title),
                "description": f"Condition: {condition}",
                "price": price,
                "currency": str(currency) or "USD",
                "url": str(url),
                "image_url": str(gallery),
                "category": category["name"],
                "category_path": ["eBay US (Finding API)", category["name"], str(primary_cat_name)] if primary_cat_name else ["eBay US (Finding API)", category["name"]],
                "brand": brand,
                "is_active": True,
                "metadata": {
                    "item_id": item_id,
                    "condition": str(condition),
                    "listing_type": "FixedPrice",
                    "region": REGION,
                    "country_code": COUNTRY_CODE,
                    "primary_category_id": str(primary_cat_id),
                    "ingest_via": "ebay_finding_api",
                },
            }
        except Exception as e:
            logger.debug("Failed to normalize item: %s", e)
            return None

    def _write_products(self, products: List[Dict]) -> None:
        if not products:
            return
        self._ensure_output_dir()
        with open(self.products_outfile, "a", encoding="utf-8") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")

    async def _scrape_impl(self, products: List[Product]) -> None:
        if not self._app_id:
            logger.info(
                "Skipping eBay Finding API run: EBAY_APP_ID not set (BUY-52338 unblock pending)."
            )
            return

        logger.info(
            "eBay Finding API scraper starting (AppID length=%d, target=%d, output=%s)",
            len(self._app_id), TARGET_TOTAL, self.products_outfile,
        )

        total = 0
        for cat in KEYWORDS:
            keyword = cat["keyword"]
            cat_name = cat["name"]
            consecutive_empty = 0
            keyword_total = 0

            logger.info("Finding API: keyword=%r (%s)", keyword, cat_name)

            for page in range(1, PAGES_PER_KEYWORD + 1):
                payload = await self._call_finding_api(keyword, page)
                items = self._parse_items(payload)

                if not items:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        logger.info(
                            "Finding API: keyword=%r hit 3 empty pages, ending keyword early",
                            keyword,
                        )
                        break
                    # Also bail early if the API returned an ack=Failure envelope
                    # signalling a quota or input error; an envelope-less response
                    # is one of the cheapest signals that this keyword is exhausted.
                    if payload and not items:
                        ack_list = payload.get("findItemsAdvancedResponse", [{}])
                        ack = ack_list[0].get("ack", ["Success"])[0] if isinstance(ack_list, list) and ack_list else "Success"
                        if isinstance(ack, list):
                            ack = ack[0] if ack else "Success"
                        if str(ack).lower() != "success":
                            logger.warning(
                                "Finding API ack=%s for keyword=%r page=%d, ending keyword",
                                ack, keyword, page,
                            )
                            break
                    continue

                consecutive_empty = 0
                page_rows: List[Dict] = []
                for raw in items:
                    row = self._normalize_item(raw, cat)
                    if row:
                        page_rows.append(row)

                if not page_rows:
                    continue

                self._write_products(page_rows)
                products.extend(
                    Product(
                        name=p["title"],
                        price=str(p["price"]),
                        url=p["url"],
                        brand=p.get("brand"),
                        image_url=p.get("image_url"),
                        category=p.get("category"),
                        raw_data=p,
                    )
                    for p in page_rows
                )
                total += len(page_rows)
                keyword_total += len(page_rows)
                self._total_scraped += len(page_rows)
                logger.info(
                    "Finding API: %s p%d (+%d, kw=%d, total=%d)",
                    cat_name, page, len(page_rows), keyword_total, total,
                )

                if total >= TARGET_TOTAL:
                    logger.info("Reached %d-product target", TARGET_TOTAL)
                    return

                await asyncio.sleep(KEYWORD_DELAY_SECONDS)

            # Short pause between keywords regardless of early exit.
            await asyncio.sleep(0.5)

        logger.info(
            "eBay Finding API scraper complete: %d products written to %s",
            total, self.products_outfile,
        )

    async def get_product_count(self) -> int:
        products = await self.scrape()
        return len(products)


# Cheap smoke check (no AppID = no network).
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = EbayUSApiScraper()
    print("active:", s.is_active)
    if s.is_active:
        asyncio.run(s.get_product_count())
