"""Scraper for Makro PRO Thailand (makro.pro).

Makro PRO is a Next.js SSR site with a Typesense-backed product catalog.
Products are accessible via SSR category pages. We crawl all grocery
leaf categories and collect products from each.

Based on the category tree analysis:
- ~428 grocery leaf categories
- ~20 products per SSR page
- Estimated total: ~8,000+ unique grocery products
"""

import asyncio
import json
import logging
import re
from typing import List, Optional, Set

from .base_scraper import BaseScraper, Product

logger = logging.getLogger(__name__)

MAKRO_BASE = "https://www.makro.pro"
MAKRO_EN = "https://www.makro.pro/en"

# Grocery-relevant top-level categories (mapped from the Makro category tree)
GROCERY_TOP = {
    "dry-grocery", "beverages", "snacks-confectionery",
    "household-supplies", "meat", "fish-seafood", "fruits-vegetables",
    "rice-and-flour", "dairy-eggs-chilled", "baby-care", "health-beauty",
    "pet-supplies", "world-of-cuisines", "royal-project",
}

class MakroProTHScraper(BaseScraper):
    """Scraper for Makro PRO Thailand via SSR category pages."""

    REQUEST_DELAY = 0.3

    def __init__(self):
        super().__init__("Makro PRO TH", MAKRO_BASE)
        self._leaf_slugs: List[str] = []
        self._collected_ids: Set[str] = set()

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch with retry and delay."""
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                response = await self.session.get(url, follow_redirects=True, timeout=30)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
        return None

    def _extract_next_data(self, html: str) -> Optional[dict]:
        """Extract __NEXT_DATA__ JSON from HTML."""
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html, re.DOTALL
        )
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    def _build_grocery_leaves(self, cats: list, in_grocery: bool = False) -> List[str]:
        """Recursively find leaf slugs under grocery categories."""
        leaves = []
        for c in cats:
            slug = c.get("slug", "")
            children = c.get("children", [])
            is_grocery = in_grocery or slug in GROCERY_TOP

            if children:
                child_leaves = self._build_grocery_leaves(children, is_grocery)
                leaves.extend(child_leaves)
            elif is_grocery and slug:
                # Skip promotional/marketing leaves
                skip = {"gold-container", "makro-milli", "get-one-free",
                        "makro-mail", "top-brands-hot-deals", "top-brands",
                        "pre-cny-ff-2026", "lotuss-electronic-expo",
                        "suggested-list-webview"}
                if slug not in skip and "hot-deal" not in slug and "expo" not in slug:
                    leaves.append(slug)
        return leaves

    def _parse_products_from_page(self, next_data: dict) -> List[Product]:
        """Extract products from __NEXT_DATA__ search result."""
        page_props = next_data.get("props", {}).get("pageProps", {})
        search_result = page_props.get("initialSearchResult", {})

        if not search_result:
            return []

        hits = search_result.get("hits", [])
        products = []

        for hit in hits:
            doc = hit.get("document", {})
            product = self._doc_to_product(doc)
            if product and product.name:
                # Deduplicate by SKU
                sku_key = product.sku or product.url or product.name
                if sku_key not in self._collected_ids:
                    self._collected_ids.add(sku_key)
                    products.append(product)

        return products

    def _doc_to_product(self, doc: dict) -> Optional[Product]:
        """Convert a Makro document to Product model."""
        title_en = doc.get("titleEn") or doc.get("title", "")
        if not title_en:
            return None

        # Price: stored as integer (satang / cents)
        display_price = doc.get("displayPrice")
        price = None
        if display_price is not None:
            price = f"฿{int(display_price):,}"

        slug = doc.get("sku", "")
        product_url = f"{MAKRO_EN}/p/{slug}" if slug else None

        brand = doc.get("brandEn") or doc.get("brand")
        images = doc.get("images", [])
        image_url = images[0] if images else None

        categories = doc.get("categories", [])
        cat_path = list(categories) if categories else None
        main_cat = categories[0] if categories else None

        unit_size = doc.get("unitSize", "")
        unit_type = doc.get("unitType", "")

        name = title_en
        if unit_size and unit_type and unit_size not in name:
            name = f"{name} - {unit_size}"

        return Product(
            name=self._clean_text(name),
            price=price,
            url=product_url,
            brand=self._clean_text(brand),
            image_url=image_url,
            sku=self._clean_text(doc.get("sku") or doc.get("itemBarCode", "")),
            category=main_cat,
            category_path=cat_path,
            in_stock=doc.get("inStock", True),
            raw_data={
                "makro_id": doc.get("makroId"),
                "product_id": doc.get("productId"),
                "sold_count": doc.get("soldCount"),
                "unit_size": unit_size,
                "unit_type": unit_type,
            },
        )

    async def _scrape_impl(self, products: List[Product]) -> None:
        """Scrape all grocery products from Makro PRO."""
        logger.info("Fetching Makro homepage for category tree...")
        html = await self.fetch(MAKRO_EN)
        if not html:
            logger.error("Failed to fetch Makro homepage")
            return

        next_data = self._extract_next_data(html)
        if not next_data:
            logger.error("Failed to extract __NEXT_DATA__ from homepage")
            return

        page_props = next_data.get("props", {}).get("pageProps", {})
        all_cats = page_props.get("_ssrCategories", [])
        if not all_cats:
            logger.error("No categories found in homepage data")
            return

        # Build the list of grocery leaf slugs
        self._leaf_slugs = self._build_grocery_leaves(all_cats)
        logger.info(f"Found {len(self._leaf_slugs)} grocery leaf categories")

        # Scrape each leaf category
        for i, slug in enumerate(self._leaf_slugs):
            if i > 0 and i % 50 == 0:
                logger.info(f"Progress: {i}/{len(self._leaf_slugs)} categories, "
                           f"{len(products)} products collected")

            url = f"{MAKRO_EN}/c/{slug}"
            html = await self.fetch(url)
            if not html:
                continue

            nd = self._extract_next_data(html)
            if not nd:
                continue

            cat_products = self._parse_products_from_page(nd)
            products.extend(cat_products)

        logger.info(f"Makro PRO TH scrape complete: {len(products)} products "
                    f"from {len(self._leaf_slugs)} categories")

async def main():
    """Quick test: scrape Makro and print count + samples."""
    logging.basicConfig(level=logging.INFO)
    async with MakroProTHScraper() as scraper:
        products = await scraper.scrape()
        print(f"\nMakro PRO TH: {len(products)} products")
        if products:
            for p in products[:5]:
                print(f"  {p.name} - {p.price} [{p.brand}]")


if __name__ == "__main__":
    asyncio.run(main())
