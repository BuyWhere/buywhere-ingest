"""Apple Singapore buy.xml lane scraper.

Fetches Apple Singapore's buy.xml sitemap and scrapes product pages
to extract SKU, price, and URL data using direct HTTP only.
"""

import asyncio
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


APPLE_SG_BUY_XML = "https://www.apple.com/sg/shop/sitemaps/buy.xml"
APPLE_SG_PRODUCT_BASE = "https://www.apple.com/sg/shop/product"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


async def fetch_sitemap(url: str, client: httpx.AsyncClient) -> list[str]:
    """Fetch and parse XML sitemap, returning list of product URLs."""
    try:
        resp = await client.get(url, headers=HEADERS, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch sitemap {url}: {e}", file=sys.stderr)
        return []

    product_urls = []
    try:
        root = ET.fromstring(resp.text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for url_elem in root.findall(".//sm:loc", ns):
            loc = url_elem.text
            if loc and "/shop/" in loc:
                product_urls.append(loc)
        if not product_urls:
            for url_elem in root.iter():
                if url_elem.tag.endswith("loc"):
                    loc = url_elem.text
                    if loc and "/shop/" in loc:
                        product_urls.append(loc)
    except ET.ParseError as e:
        print(f"Failed to parse sitemap XML: {e}", file=sys.stderr)

    print(f"Found {len(product_urls)} product URLs from sitemap")
    return product_urls


def extract_sku_from_url(url: str) -> Optional[str]:
    """Extract SKU identifier from Apple product URL path."""
    patterns = [
        r'/product/([a-z0-9]+)/a/',  # /product/MQD83CH/a/...
        r'/buy-[^/]+/[^/]+/([a-z0-9]+)-',  # /buy-mac/imac/SKU-...
        r'/([A-Z0-9]{5,})',  # Capital letter SKU patterns
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


async def scrape_product(url: str, client: httpx.AsyncClient) -> Optional[dict[str, Any]]:
    """Scrape a single Apple product page for SKU, price, and availability."""
    try:
        resp = await client.get(url, headers=HEADERS, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        return None

    html = resp.text
    sku = extract_sku_from_url(url)
    price = None
    in_stock = None

    price_match = re.search(r'[\$SGD][\s]*[\d,]+\.?\d*', html)
    if price_match:
        price = price_match.group(0).strip()

    if "add to cart" in html.lower() or "buy now" in html.lower():
        if "unavailable" in html.lower() or "sold out" in html.lower():
            in_stock = False
        else:
            in_stock = True

    json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
    for match in re.finditer(json_ld_pattern, html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and data.get("@type") == "Product":
                offers = data.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                availability = offers.get("availability", "")
                if "InStock" in availability:
                    in_stock = True
                elif "OutOfStock" in availability or "Discontinued" in availability:
                    in_stock = False
                price_val = offers.get("price")
                if price_val:
                    price = f"SGD {price_val}"
                break
        except (json.JSONDecodeError, KeyError):
            continue

    return {
        "sku": sku,
        "url": url,
        "price": price,
        "in_stock": in_stock,
        "source": "apple_sg_buy_xml",
        "region": "SG",
    }


async def run_lane(output_path: str, limit: int = 0):
    """Main entry point for Apple SG buy.xml lane."""
    async with httpx.AsyncClient() as client:
        product_urls = await fetch_sitemap(APPLE_SG_BUY_XML, client)
        if limit > 0:
            product_urls = product_urls[:limit]

        print(f"Scraping {len(product_urls)} product pages...")

        products = []
        for i, url in enumerate(product_urls):
            if i % 50 == 0:
                print(f"Progress: {i}/{len(product_urls)}")

            product = await scrape_product(url, client)
            if product:
                products.append(product)

            await asyncio.sleep(0.25)

        print(f"Scraped {len(products)} products")

        with open(output_path, "w", encoding="utf-8") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")

        print(f"Output written to {output_path}")

        stock_true = sum(1 for p in products if p.get("in_stock") is True)
        stock_false = sum(1 for p in products if p.get("in_stock") is False)
        stock_unknown = sum(1 for p in products if p.get("in_stock") is None)
        print(f"Stock: in_stock={stock_true}, out_of_stock={stock_false}, unknown={stock_unknown}")

        return products


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/apple_sg_buy_xml_products.ndjson", help="Output NDJSON path")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of URLs to scrape (0=no limit)")
    args = parser.parse_args()

    asyncio.run(run_lane(args.output, args.limit))