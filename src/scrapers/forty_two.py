"""Scraper for FortyTwo Singapore.

Approach (per BUY-43058):
- FortyTwo is a Nuxt SPA behind Cloudflare. Direct HTTP from this machine
  returns 403.
- The site's product data is loaded via Magento GraphQL at
  `https://otak.fortytwo.sg/graphql`, but BrightData residential blocks
  POST requests (402 bad_endpoint) on that host without KYC.
- The `/search?q=<term>` URL is a Cloudflare-passable render that returns
  the full SSR'd product listing page with product cards inline. We hit
  several search terms and parse the embedded product cards.
- Each product card has: name, current price (S$), image URL, product URL
  (`/<slug>.html`), color options, dimensions.
- We use BrightData residential to bypass Cloudflare, with SSL verify=False
  (the proxy serves a self-signed chain) and `httpx`.
"""

import asyncio
import os
import re
import urllib.parse
from typing import List, Optional

import httpx

from .base_scraper import BaseScraper, Product

FORTY_TWO_BASE = "https://www.fortytwo.sg"

# Search terms that cover the major FortyTwo categories. Each query returns
# ~50 product cards in the rendered HTML. We walk enough queries to get 50+
# unique products (the scraper dedupes by product URL).
SEARCH_TERMS = [
    "sofa", "bed", "mattress", "table", "chair",
    "wardrobe", "shelf", "desk", "dining",
]

# BrightData residential proxy (verified working for fortytwo.sg GETs).
BRIGHTDATA_PROXY_URL: Optional[str] = None
_BR_USER = os.environ.get("BRIGHTDATA_USERNAME", "brd-customer-hl_3ab737be-zone-residential")
_BR_PASS = os.environ.get("BRIGHTDATA_PASSWORD", "o3feuq72olm5")
_BR_HOST = os.environ.get("BRIGHTDATA_PROXY_HOST", "brd.superproxy.io")
_BR_PORT = os.environ.get("BRIGHTDATA_PROXY_PORT", "33335")
_BR_ENC_USER = urllib.parse.quote(_BR_USER, safe="")
_BR_ENC_PASS = urllib.parse.quote(_BR_PASS, safe="")
BRIGHTDATA_PROXY_URL = (
    f"http://{_BR_ENC_USER}:{_BR_ENC_PASS}@{_BR_HOST}:{_BR_PORT}"
)

# Regexes to find product cards in the rendered search results page.
# Product cards are: <div data-testid="product-card" maximumPrice="S$NNN.00">
#   <a href="<slug>.html" ...>
#     <img src="<image>" alt="<name>">
#   <span class="sf-product-card__title"><name></span>
#   <div class="new-price">S$<price></div>
_PRODUCT_CARD_RE = re.compile(
    r'<div[^>]+data-testid="product-card"[^>]*maximumPrice="S\$([0-9,]+(?:\.[0-9]+)?)"[^>]*>'
    r'(.*?)'                                                  # card body
    r'</div>\s*</div>\s*</div>\s*</div>\s*</div>',             # closing tags
    re.DOTALL,
)
_HREF_RE = re.compile(r'href="(/[a-z][a-z0-9\-]+\.html)"')
_TITLE_RE = re.compile(
    r'<span[^>]*class="sf-product-card__title"[^>]*>\s*([^<]+?)\s*</span>',
    re.DOTALL,
)
_IMG_RE = re.compile(
    r'<img[^>]+src="(https?://static[0-9]?\.fortytwo\.sg/[^"]+)"[^>]+alt="([^"]+)"',
)


class FortyTwoScraper(BaseScraper):
    def __init__(self):
        super().__init__("FortyTwo", FORTY_TWO_BASE)

    async def _scrape_impl(self, products: List[Product]) -> None:
        # We use a separate client with BrightData residential proxy because
        # BaseScraper's `self.session` is direct and fortytwo.sg returns 403
        # to it. We disable SSL verify because the BrightData chain is
        # self-signed (see buy-42673-chewy-burn-vs-premium memory: HttpsProxy
        # agent's rejectUnauthorized:false does NOT propagate to the
        # tunnelled request, so we have to set this on the inner client).
        async with httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            verify=False,  # noqa: S501 - required for BrightData
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-SG,en;q=0.9",
            },
            proxy=BRIGHTDATA_PROXY_URL,
        ) as client:
            seen: set[str] = set()
            for term in SEARCH_TERMS:
                url = f"{FORTY_TWO_BASE}/search?q={urllib.parse.quote(term)}"
                try:
                    resp = await client.get(url)
                except Exception as exc:
                    logger.warning("FortyTwo fetch failed for %s: %s", term, exc)
                    continue
                if resp.status_code != 200:
                    logger.warning(
                        "FortyTwo HTTP %s for term %s", resp.status_code, term
                    )
                    continue
                for card in _extract_cards(resp.text):
                    href = card.get("url")
                    if not href or href in seen:
                        continue
                    seen.add(href)
                    products.append(Product(
                        name=card.get("name"),
                        price=card.get("price"),
                        url=f"{FORTY_TWO_BASE}{href}",
                        brand="FortyTwo",
                        image_url=card.get("image"),
                        in_stock=True,
                        raw_data=card,
                    ))


def _extract_cards(html: str) -> List[dict]:
    """Parse the rendered search-results page and extract product cards."""
    cards: List[dict] = []
    seen_in_page: set[str] = set()

    # Find all product card blocks via the data-testid marker.
    for m in _PRODUCT_CARD_RE.finditer(html):
        body = m.group(2)
        max_price = m.group(1)

        # URL
        href_m = _HREF_RE.search(body)
        if not href_m:
            continue
        href = href_m.group(1)
        if href in seen_in_page:
            continue
        seen_in_page.add(href)

        # Title
        title_m = _TITLE_RE.search(body)
        name = title_m.group(1).strip() if title_m else None
        if not name:
            # Fall back to image alt text
            img_m = _IMG_RE.search(body)
            if img_m:
                name = img_m.group(2).strip()

        # Image
        img_m = _IMG_RE.search(body)
        image = img_m.group(1) if img_m else None

        # New price from inside .new-price; fall back to max price attr
        price_m = re.search(
            r'<div class="new-price"[^>]*>.*?S\$([0-9,]+(?:\.[0-9]+)?)',
            body,
            re.DOTALL,
        )
        price = (
            f"S${price_m.group(1)}" if price_m else f"S${max_price}"
        )

        cards.append({
            "name": name,
            "price": price,
            "url": href,
            "image": image,
            "max_price": f"S${max_price}",
        })

    return cards


import logging
logger = logging.getLogger(__name__)


async def main():
    """CLI entrypoint for ad-hoc verification."""
    import warnings
    warnings.filterwarnings("ignore")  # noqa: S501 - self-signed proxy cert
    scraper = FortyTwoScraper()
    # Bypass the base scraper and use our dedicated client for fetching.
    async with httpx.AsyncClient(
        timeout=60.0,
        follow_redirects=True,
        verify=False,  # noqa: S501
        headers={"User-Agent": "Mozilla/5.0 (compatible; FortyTwoScraper)"},
        proxy=BRIGHTDATA_PROXY_URL,
    ) as client:
        # Walk a single term as a smoke test.
        resp = await client.get(f"{FORTY_TWO_BASE}/search?q=sofa")
        cards = _extract_cards(resp.text)
        print(f"FortyTwo: {len(cards)} products (smoke test for term 'sofa')")
        for c in cards[:5]:
            print(f"  {c['name']} | {c['price']} | {c['url']}")


if __name__ == "__main__":
    asyncio.run(main())
