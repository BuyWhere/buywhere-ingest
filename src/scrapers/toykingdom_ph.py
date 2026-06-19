"""Scraper for Toy Kingdom Philippines (toykingdom.com.ph).

Shopify-based store with ~5,250 products in Toys & Games category.
Exposes a dedicated scraper for the PH toys ingestion lane (BUY-53324).
"""

from typing import List

from .shopify_store import ShopifyScraper
from .base_scraper import Product


class ToyKingdomPHScraper(ShopifyScraper):
    """Scrape Toy Kingdom Philippines via Shopify products.json API."""

    MAX_PRODUCTS = 6000  # Allow a buffer above ~5,250 known products

    def __init__(self):
        super().__init__(
            base_url="https://www.toykingdom.com.ph",
            max_products=self.MAX_PRODUCTS,
        )
        self.merchant_name = "Toy Kingdom Philippines"

    def _parse_product(self, data: dict) -> Product | None:
        """Parse product with Toy Kingdom specific enrichments."""
        product = super()._parse_product(data)
        if product is None:
            return None

        # Extract age range from tags for category enrichment
        age_tags = [
            tag.replace("Shop by Age_", "").strip()
            for tag in data.get("tags", [])
            if tag.startswith("Shop by Age_")
        ]
        if age_tags:
            product.category_path = [
                product.category or "Toys & Games",
                f"Age: {age_tags[0]}",
            ]

        return product


__all__ = ["ToyKingdomPHScraper"]
