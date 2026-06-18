"""Scraper for Nike Singapore.

Approach (per BUY-43058):
- Nike SG's search URL `nike.com/sg/search?q=*` returns 404.
- Real product data is embedded in the SSR'd landing page HTML.
- Each landing page (`/sg/w`, `/sg/w/shoes-y7ok`, `/sg/w/sale-3yaep`) returns
  20-60+ products with title, currentPrice, productCode, colorDescription, and
  product URLs (`/sg/t/{slug}/{productCode}`).
- We hit several landing pages and extract products from the HTML.
"""

import asyncio
import re
from typing import List, Optional

from .base_scraper import BaseScraper, Product

NIKE_SG_BASE = "https://www.nike.com/sg"

# Landing pages with embedded product data. Each returns 20-60+ products.
# Confirmed working URLs (BUY-43058): /sg/w, /sg/w/shoes-y7ok, /sg/w/sale-3yaep
# /sg/w/jordan redirects to /sg/w; /sg/men and /sg/kids are category landing
# pages with no product detail inline.
LANDING_PAGES = [
    f"{NIKE_SG_BASE}/w",                 # women (53 products)
    f"{NIKE_SG_BASE}/w/shoes-y7ok",      # women shoes (24+ products)
    f"{NIKE_SG_BASE}/w/sale-3yaep",      # women sale (24+ products)
]


class NikeSGScraper(BaseScraper):
    def __init__(self):
        super().__init__("Nike SG", NIKE_SG_BASE)

    async def _scrape_impl(self, products: List[Product]) -> None:
        for url in LANDING_PAGES:
            try:
                html = await self.fetch(url)
            except Exception:
                html = None
            if not html:
                continue
            for p in _extract_products(html):
                if not p.get("url") or not p.get("title"):
                    continue
                products.append(Product(
                    name=p.get("title"),
                    price=str(p.get("currentPrice")) if p.get("currentPrice") is not None else None,
                    url=p.get("url"),
                    brand="Nike",
                    image_url=p.get("imageUrl"),
                    sku=p.get("productCode"),
                    category=p.get("subcategory"),
                    in_stock=True,
                    raw_data=p,
                ))


# Nike product codes are 6 letters/digits optionally followed by `-NNN` variant suffix.
_PRODUCT_CODE_RE = re.compile(
    r'productCode[^a-zA-Z0-9]+(?P<code>[A-Z0-9]{6,12}(?:-[0-9]{3})?)'
)
# URL pattern in href: /sg/t/<slug>/<code>
_PRODUCT_URL_RE = re.compile(
    r'/sg/t/(?P<slug>[a-z0-9\-]+)/(?P<code>[A-Z0-9]{6,12}(?:-[0-9]{3})?)'
)


def _extract_products(html: str) -> List[dict]:
    """Walk a Nike landing page and extract product dicts.

    Two complementary extraction passes:
    1. From the `productCode` field in the SSR JSON state, with surrounding
       title/price/slug data harvested from a chunk around the match.
    2. From the `href="/sg/t/<slug>/<code>"` URLs that appear in product
       card links. These give us the full slug for clean product URLs.

    De-duplicate by `productCode` so the same product on multiple pages is
    reported once.
    """
    products_by_code: dict[str, dict] = {}

    # Pass 1: scrape productCode entries with their chunk data
    for m in _PRODUCT_CODE_RE.finditer(html):
        code = m.group("code")
        if code in products_by_code:
            continue
        prod = _chunk_product(html, m.start(), m.end(), code)
        if prod:
            products_by_code[code] = prod

    # Pass 2: enrich with full URLs from product-card hrefs
    for m in _PRODUCT_URL_RE.finditer(html):
        code = m.group("code")
        slug = m.group("slug")
        if code in products_by_code:
            products_by_code[code]["url"] = (
                f"{NIKE_SG_BASE}/t/{slug}/{code}"
            )
        else:
            # New product not seen in pass 1; just record the URL
            products_by_code[code] = {
                "productCode": code,
                "title": None,
                "currentPrice": None,
                "url": f"{NIKE_SG_BASE}/t/{slug}/{code}",
            }

    return list(products_by_code.values())


def _chunk_product(html: str, m_start: int, m_end: int, code: str) -> Optional[dict]:
    """Extract title/price/slug around a productCode match in the HTML chunk."""
    start = max(0, m_start - 100)
    end = min(len(html), m_end + 1800)
    chunk = html[start:end]

    title_m = re.search(
        r'title[^a-zA-Z0-9]+([^"\\]{2,80}?)["\\]',
        chunk,
    )
    price_m = re.search(
        r'currentPrice[^a-zA-Z0-9]+([0-9]+(?:\.[0-9]+)?)',
        chunk,
    )
    subcat_m = re.search(
        r'subcategory[^a-zA-Z0-9]+([^"\\]{2,40}?)["\\]',
        chunk,
    )
    image_m = re.search(
        r'(?:imageUrl|mainImageUrl)[^a-zA-Z0-9]+(https?://[^"\\]{20,200})',
        chunk,
    )
    color_m = re.search(
        r'colorDescription[^a-zA-Z0-9]+([^"\\]{2,80}?)["\\]',
        chunk,
    )

    title = title_m.group(1).strip() if title_m else None
    if not title or title == "Products. Nike SG":
        return None

    # Slug: try the URL in the same chunk first
    url_m = re.search(
        r'/sg/t/(?P<slug>[a-z0-9\-]+)/' + re.escape(code),
        chunk,
    )
    if url_m:
        url = f"{NIKE_SG_BASE}/t/{url_m.group('slug')}/{code}"
    else:
        url = f"{NIKE_SG_BASE}/t/{code}"

    price: Optional[float] = None
    if price_m:
        try:
            price = float(price_m.group(1))
        except (TypeError, ValueError):
            price = None

    return {
        "productCode": code,
        "title": title,
        "currentPrice": price,
        "url": url,
        "imageUrl": image_m.group(1) if image_m else None,
        "subcategory": subcat_m.group(1) if subcat_m else None,
        "colorDescription": color_m.group(1) if color_m else None,
    }


async def main():
    async with NikeSGScraper() as scraper:
        count = await scraper.get_product_count()
        print(f"Nike SG: {count} products")


if __name__ == "__main__":
    asyncio.run(main())
