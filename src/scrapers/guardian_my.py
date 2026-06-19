"""Scraper for Guardian Malaysia (MY)."""

import asyncio
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from .base_scraper import BaseScraper, Product

GUARDIAN_MY_BASE = "https://www.guardian.com.my"
GRAPHQL_URL = f"{GUARDIAN_MY_BASE}/graphql"
PAGE_SIZE = 200
MAX_CONCURRENT_PAGES = 8

PRODUCTS_QUERY = """query Products($pageSize: Int!, $currentPage: Int!) {
  products(search: "", pageSize: $pageSize, currentPage: $currentPage) {
    total_count
    items {
      name
      sku
      url_key
      price {
        regularPrice {
          amount {
            value
            currency
          }
        }
      }
      categories {
        name
        level
      }
    }
    page_info {
      total_pages
    }
  }
}"""

BEAUTY_CATEGORY_ALIASES = (
    ("Skin Care", ("skin care", "skin")),
    ("Cosmetics", ("cosmetic", "makeup")),
    ("Hair Care", ("hair care", "hair")),
    ("Personal Care", ("personal care",)),
    ("Fragrance", ("fragrance", "perfume")),
    ("Bath & Body", ("bath", "body wash", "body care")),
    ("Sun Care", ("sun care", "suncare", "sun")),
    ("Beauty Enhancer", ("beauty enhancer",)),
)

NON_PRODUCT_CATEGORY_HINTS = (
    "promotion",
    "rewards",
    "contest",
    "winner",
    "news",
    "community",
    "guardian awards",
    "beauty days",
    "featured brands",
    "online exclusives",
    "bulk deals",
)


class GuardianMYScraper(BaseScraper):
    """Scrape Guardian MY through its public GraphQL product catalogue."""

    REQUEST_TIMEOUT = 60

    def __init__(self):
        super().__init__("Guardian MY", GUARDIAN_MY_BASE)

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        current_page: int,
        semaphore: asyncio.Semaphore,
    ) -> dict[str, Any]:
        async with semaphore:
            response = await client.post(
                GRAPHQL_URL,
                json={
                    "query": PRODUCTS_QUERY,
                    "variables": {
                        "pageSize": PAGE_SIZE,
                        "currentPage": current_page,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                raise RuntimeError(
                    f"Guardian MY GraphQL error on page {current_page}: {payload['errors']}"
                )
            return payload["data"]["products"]

    def _sorted_category_names(self, categories: list[dict[str, Any]] | None) -> list[str]:
        if not categories:
            return []

        ordered = sorted(
            categories,
            key=lambda item: (
                int(item.get("level") or 0),
                self._clean_text(item.get("name") or "") or "",
            ),
        )

        deduped: list[str] = []
        seen: set[str] = set()
        for item in ordered:
            name = self._clean_text(item.get("name") or "")
            if not name:
                continue
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            deduped.append(name)
        return deduped

    def _pick_beauty_category(self, category_names: list[str]) -> str | None:
        for category_name in category_names:
            lowered = category_name.lower()
            if any(hint in lowered for hint in NON_PRODUCT_CATEGORY_HINTS):
                continue
            for label, aliases in BEAUTY_CATEGORY_ALIASES:
                if any(alias in lowered for alias in aliases):
                    return label
            if "beauty" in lowered:
                return category_name
        return None

    def _format_price(self, raw_price: Any, currency: str | None) -> str | None:
        if raw_price is None:
            return None

        try:
            normalized = Decimal(str(raw_price)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return None

        amount = f"{normalized:.2f}"
        return f"{amount} {currency}" if currency else amount

    def _build_product(self, item: dict[str, Any]) -> Product | None:
        name = self._clean_text(item.get("name") or "")
        url_key = self._clean_text(item.get("url_key") or "")
        if not name or not url_key:
            return None

        category_names = self._sorted_category_names(item.get("categories"))
        category = self._pick_beauty_category(category_names)
        if not category:
            return None

        amount = (
            (((item.get("price") or {}).get("regularPrice") or {}).get("amount") or {})
        )
        price = self._format_price(amount.get("value"), amount.get("currency"))

        raw_data = {
            "sku": item.get("sku"),
            "url_key": url_key,
            "categories": category_names,
            "price": item.get("price"),
        }

        return Product(
            name=name,
            price=price,
            url=f"{GUARDIAN_MY_BASE}/{url_key}.html",
            sku=self._clean_text(item.get("sku") or ""),
            category=category,
            category_path=["Beauty", category],
            raw_data=raw_data,
        )

    async def _scrape_impl(self, products: list[Product]) -> None:
        headers = {
            "User-Agent": self._get_headers()["User-Agent"],
            "Content-Type": "application/json",
        }
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)

        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT, headers=headers) as client:
            first_page = await self._fetch_page(client, 1, semaphore)
            for item in first_page.get("items", []):
                product = self._build_product(item)
                if product:
                    products.append(product)

            total_pages = int((first_page.get("page_info") or {}).get("total_pages") or 1)
            if total_pages <= 1:
                return

            tasks = [
                self._fetch_page(client, current_page, semaphore)
                for current_page in range(2, total_pages + 1)
            ]
            for page in await asyncio.gather(*tasks):
                for item in page.get("items", []):
                    product = self._build_product(item)
                    if product:
                        products.append(product)
