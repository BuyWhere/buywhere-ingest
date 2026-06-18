"""Samsung Singapore sitemap lane scraper.

Fetches Samsung Singapore sitemaps and scrapes product pages
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


SAMSUNG_SG_SITEMAPS = [
    "https://www.samsung.com/sg/im-sitemap.xml",
    "https://www.samsung.com/sg/vd-sitemap.xml",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


async def fetch_sitemap(url: str, client: httpx.AsyncClient) -> list[str]:
    """Fetch and parse XML sitemap, returning list of product page URLs."""
    try:
        resp = await client.get(url, headers=HEADERS, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch sitemap {url}: {e}", file=sys.stderr)
        return []

    product_urls = []
    try:
        root = ET.fromstring(resp.text)
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == "loc":
                loc = elem.text
                if loc and "/sg/" in loc and loc.endswith("/"):
                    product_urls.append(loc)
    except ET.ParseError as e:
        print(f"Failed to parse sitemap XML: {e}", file=sys.stderr)

    print(f"Found {len(product_urls)} product URLs from {url}")
    return product_urls


def extract_sku_from_url(url: str) -> Optional[str]:
    """Extract SKU/model identifier from Samsung product URL path."""
    patterns = [
        r'-([a-z0-9]{8,20})/$',  # SKU suffix at end before trailing slash
        r'/([a-z0-9]{8,20})/$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    parts = url.rstrip('/').split('/')
    if parts:
        return parts[-1]
    return None


async def scrape_product(url: str, client: httpx.AsyncClient) -> Optional[dict[str, Any]]:
    """Scrape a single Samsung product page for SKU, price, and availability."""
    try:
        resp = await client.get(url, headers=HEADERS, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return None

    html = resp.text
    sku = extract_sku_from_url(url)
    price = None
    in_stock = None

    price_match = re.search(r'SGD\s*[\d,]+\.?\d*', html, re.IGNORECASE)
    if price_match:
        price = price_match.group(0)
    else:
        price_match = re.search(r'[\$S][\s]*[\d,]+\.?\d*', html)
        if price_match:
            price = price_match.group(0)

    if "out of stock" in html.lower() or "sold out" in html.lower():
        in_stock = False
    elif "add to cart" in html.lower() or "buy now" in html.lower():
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
        "source": "samsung_sg_sitemap",
        "region": "SG",
    }


async def run_lane(output_path: str, limit: int = 0):
    """Main entry point for Samsung SG sitemap lane."""
    async with httpx.AsyncClient() as client:
        all_urls = []
        for sitemap_url in SAMSUNG_SG_SITEMAPS:
            urls = await fetch_sitemap(sitemap_url, client)
            all_urls.extend(urls)

        unique_urls = list(set(all_urls))
        print(f"Total unique product URLs: {len(unique_urls)}")

        if limit > 0:
            unique_urls = unique_urls[:limit]

        print(f"Scraping {len(unique_urls)} product pages...")

        products = []
        for i, url in enumerate(unique_urls):
            if i % 50 == 0:
                print(f"Progress: {i}/{len(unique_urls)}")

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
    parser.add_argument("--output", default="data/samsung_sg_products.ndjson", help="Output NDJSON path")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of URLs to scrape (0=no limit)")
    args = parser.parse_args()

    asyncio.run(run_lane(args.output, args.limit))