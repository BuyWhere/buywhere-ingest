"""Scraper for Uniqlo Singapore.

Approach (per BUY-43058):
- Uniqlo SG's search URL `uniqlo.com/sg/en/search?q=*` returns 404.
- The Uniqlo SPA loads product listings via a private commerce API at
  `/sg/api/commerce/v3/en/products?offset=N&limit=N`. With no `path` filter
  it returns the full SG catalog (1269 products paginated).
- Each item has: `name`, `productId` (E-style code), `genderName`,
  `prices.base.value` (SGD), `images.main[].url`, `composition`.
- We paginate through several pages of the catalog to get 50+ products.
"""

import asyncio
import urllib.parse
from typing import List, Optional

import httpx

from .base_scraper import BaseScraper, Product

UNIQLO_SG_BASE = "https://www.uniqlo.com/sg/en"
UNIQLO_API_BASE = "https://www.uniqlo.com/sg/api/commerce/v3/en"
UNIQLO_PRODUCTS_URL = f"{UNIQLO_API_BASE}/products"

# Pagination settings. Uniqlo's catalog has 1269+ items; we pull several pages.
PAGE_SIZE = 60
MAX_PAGES = 3  # 3 pages × 60 = 180 products, well over the 50+ target


class UniqloSGScraper(BaseScraper):
    """Scraper for Uniqlo Singapore."""

    def __init__(self):
        super().__init__("Uniqlo SG", UNIQLO_SG_BASE)
        self._session: Optional[httpx.AsyncClient] = None

    async def _scrape_impl(self, products: List[Product]) -> None:
        # Use a dedicated client so we can use httpx's connection pooling across
        # the multiple pages of the catalog pagination.
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=self._get_headers(),
        ) as client:
            for page in range(MAX_PAGES):
                offset = page * PAGE_SIZE
                page_products = await self._fetch_page(client, offset, PAGE_SIZE)
                if not page_products:
                    break
                for item in page_products:
                    p = _item_to_product(item)
                    if p:
                        products.append(p)
                if len(page_products) < PAGE_SIZE:
                    # No more pages
                    break

    async def _fetch_page(
        self, client: httpx.AsyncClient, offset: int, limit: int
    ) -> List[dict]:
        """Fetch one page of products from Uniqlo's catalog API."""
        params = {"offset": str(offset), "limit": str(limit)}
        try:
            resp = await client.get(UNIQLO_PRODUCTS_URL, params=params)
        except Exception as e:
            logger.warning("Uniqlo API request failed (offset=%s): %s", offset, e)
            return []
        if resp.status_code != 200:
            logger.warning("Uniqlo API HTTP %s (offset=%s)", resp.status_code, offset)
            return []
        try:
            data = resp.json()
        except Exception as e:
            logger.warning("Uniqlo API response not JSON (offset=%s): %s", offset, e)
            return []
        result = data.get("result", {})
        return result.get("items", []) or []


def _item_to_product(item: dict) -> Optional[Product]:
    """Map a Uniqlo catalog API item to our internal Product schema."""
    name = item.get("name")
    product_id = item.get("productId")
    if not name or not product_id:
        return None

    # Price: prices.base.value (or prices.promo.value if base is null for sale items)
    price = None
    prices = item.get("prices") or {}
    base = prices.get("base") or {}
    if not base:
        # Sale items: base is null, the actual selling price is in promo
        base = prices.get("promo") or {}
    raw_price = base.get("value")
    if raw_price is not None:
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            price = None

    # Image: images.main[0].url
    image_url = None
    images = item.get("images") or {}
    main = images.get("main") or []
    if main and isinstance(main, list):
        image_url = main[0].get("url") if isinstance(main[0], dict) else None

    # URL: /sg/en/products/{productId}
    url = f"{UNIQLO_SG_BASE}/products/{product_id}"

    # Category from genderName
    gender = item.get("genderName") or ""
    category = gender or None

    # Subcategory from representative.l2Id (we keep it as a string)
    rep = item.get("representative") or {}

    # Colors
    colors = item.get("colors") or []
    color_names = [c.get("name") for c in colors if isinstance(c, dict) and c.get("name")]

    return Product(
        name=name,
        price=f"{price:.2f}" if price is not None else None,
        url=url,
        brand="Uniqlo",
        image_url=image_url,
        sku=product_id,
        category=category,
        in_stock=True,
        raw_data={
            "productId": product_id,
            "name": name,
            "price": price,
            "currency": (base.get("currency") or {}).get("code", "SGD"),
            "image_url": image_url,
            "gender": gender,
            "colors": color_names,
            "l2Id": rep.get("l2Id"),
        },
    )


# Module-level logger (re-uses the one in base_scraper)
import logging
logger = logging.getLogger(__name__)


async def main():
    async with UniqloSGScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Uniqlo SG: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
