"""Scraper for Alfagift Indonesia (alfagift.id).

Alfagift is a Nuxt.js SPA with a Spring Boot API backend at
webcommerce-gw.alfagift.id. Product data is accessible via direct
HTTP API calls with the correct headers (fingerprint, devicemodel, etc.)
No Playwright or JS rendering needed for the API layer.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Set

import httpx

from .base_scraper import BaseScraper, Product

logger = logging.getLogger(__name__)

API_BASE = "https://webcommerce-gw.alfagift.id/v2"
ALFAGIFT_BASE = "https://alfagift.id"
# Static fingerprint/trxid values that work with the Alfagift API
# These can be any consistent values - the API just needs them present
API_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "id",
    "DeviceModel": "other",
    "DeviceType": "Web",
    "fingerprint": "7EIWJiEUre+diMfeUstRNzpM21ob2u15dP6K5jKf5mG2IOYK/wI9IaBDAK7g748l",
    "latitude": "0",
    "longitude": "0",
    "Referer": "https://alfagift.id/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

class AlfagiftIDScraper(BaseScraper):
    """Scraper for Alfagift Indonesia via direct HTTP API."""

    MAX_PRODUCTS = 20000

    def __init__(self):
        super().__init__("Alfagift ID", API_BASE)
        self._categories: List[dict] = []
        self._seen_skus: Set[str] = set()

    def _get_headers(self) -> Dict[str, str]:
        h = dict(API_HEADERS)
        h["trxid"] = str(int(time.time() * 1000) % 10000000000)
        return h

    async def _fetch_json(self, url: str) -> Optional[dict]:
        """Fetch a URL and parse JSON response."""
        headers = self._get_headers()
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                response = await self.session.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
        return None

    async def _load_categories(self) -> List[dict]:
        """Fetch the full category tree."""
        result = await self._fetch_json(f"{API_BASE}/categories")
        if not result:
            return []
        return result.get("categories", [])

    def _collect_leaf_categories(self, cats: List[dict], parent_name: str = "") -> List[dict]:
        """Recursively collect all leaf (grocery-relevant) categories."""
        leaves = []
        grocery_parents = {
            "kebutuhan dapur", "makanan", "minuman", "produk segar & beku",
            "kebutuhan ibu & anak", "kebutuhan rumah", "personal care",
            "kebutuhan kesehatan", "bahan masakan",
        }

        for c in cats:
            name = c.get("categoryName", "")
            cid = c.get("categoryId", "")
            subs = c.get("subCategories") or []

            is_grocery = parent_name.lower() in grocery_parents or name.lower() in grocery_parents

            if subs:
                child_leaves = self._collect_leaf_categories(subs, name)
                leaves.extend(child_leaves)
            elif is_grocery and cid:
                leaves.append(c)
        return leaves


    def _api_product_to_product(self, item: dict) -> Optional[Product]:
        """Convert an Alfagift API product dict to Product."""
        name = item.get("productName")
        if not name:
            return None

        sku = item.get("sku") or str(item.get("productId", ""))
        if sku in self._seen_skus:
            return None
        self._seen_skus.add(sku)

        price = item.get("finalPrice") or item.get("basePrice")
        price_str = f"Rp{int(price):,}" if price else None

        product_id = item.get("productId", "")
        url = f"{ALFAGIFT_BASE}/product/{product_id}" if product_id else None

        image = item.get("image", "")
        brand = item.get("brandName") or item.get("brand")

        category_lv0 = item.get("categoryNameLvl0", "")
        category_lv1 = item.get("categoryNameLvl1", "")
        category_path = [c for c in [category_lv0, category_lv1] if c]

        stock = item.get("stock", 0)
        in_stock = stock is None or stock > 0

        return Product(
            name=self._clean_text(name),
            price=price_str,
            url=url,
            brand=self._clean_text(brand),
            image_url=image,
            sku=sku,
            category=category_lv1 or category_lv0,
            category_path=category_path or None,
            in_stock=in_stock,
            raw_data=item,
        )

    async def _scrape_category(self, cat_id: str, products: List[Product]) -> None:
        """Scrape all products from a single category via pagination."""
        start = 0
        limit = 60
        total_pages = None

        while total_pages is None or start // limit < total_pages:
            if len(products) >= self.MAX_PRODUCTS:
                break

            url = f"{API_BASE}/products/category/{cat_id}?sortDirection=asc&start={start}&limit={limit}"
            result = await self._fetch_json(url)
            if not result:
                break

            if total_pages is None:
                total_pages = result.get("totalPage", 0)
                total_data = result.get("totalData", 0)
                logger.debug(f"Category {cat_id}: {total_data} products, {total_pages} pages")

            items = result.get("products", [])
            if not items:
                break

            for item in items:
                p = self._api_product_to_product(item)
                if p:
                    products.append(p)

            start += limit
            await asyncio.sleep(0.3)


    async def _scrape_impl(self, products: List[Product]) -> None:
        """Scrape Alfagift by iterating grocery category tree."""
        logger.info("Fetching Alfagift category tree...")
        cats = await self._load_categories()
        if not cats:
            logger.error("Failed to load categories")
            return

        leaf_cats = self._collect_leaf_categories(cats)
        logger.info(f"Found {len(leaf_cats)} grocery leaf categories")

        for i, cat in enumerate(leaf_cats):
            if len(products) >= self.MAX_PRODUCTS:
                break
            cat_name = cat.get("categoryName", "unknown")
            cat_id = cat.get("categoryId", "")
            logger.info(f"Category {i+1}/{len(leaf_cats)}: {cat_name} ({len(products)} so far)")
            await self._scrape_category(cat_id, products)
            logger.info(f"  {cat_name}: {len([p for p in products if cat_name.lower() in (p.category or '').lower()])} matched, {len(products)} total")

        logger.info(f"Alfagift total: {len(products)} products from {len(leaf_cats)} categories")


async def main():
    """Quick test."""
    logging.basicConfig(level=logging.INFO)
    async with AlfagiftIDScraper() as scraper:
        products = await scraper.scrape()
        print(f"\nAlfagift ID: {len(products)} products")
        if products:
            for p in products[:10]:
                print(f"  {p.name} - {p.price} [{p.brand}]")


if __name__ == "__main__":
    asyncio.run(main())
