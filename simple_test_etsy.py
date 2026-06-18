#!/usr/bin/env python3
"""Simple test for Etsy scraper without imports."""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Set
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ETSY_BASE = "https://www.etsy.com"

CATEGORIES = [
    {"id": "jewelry", "name": "Jewelry", "path": "/c/jewelry"},
    {"id": "clothing", "name": "Clothing", "path": "/c/clothing"},
    {"id": "home_and_living", "name": "Home & Living", "path": "/c/home-and-living"},
    {"id": "vintage", "name": "Vintage", "path": "/c/vintage"},
]

PRODUCT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

def fetch_with_retry(url: str, max_retries: int = 5) -> Optional[str]:
    """Fetch URL with retry logic."""
    headers = PRODUCT_HEADERS.copy()

    for attempt in range(max_retries):
        try:
            # Add jitter
            jitter = 1 + (hash(url + str(attempt)) % 5) / 10
            time.sleep(jitter)

            resp = requests.get(
                url,
                headers=headers,
                timeout=30,
                verify=False,
                allow_redirects=True,
            )

            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                wait_time = min(60, (2 ** attempt) + (hash(url + str(attempt)) % 10))
                logger.warning(f"Rate limited on {url}, waiting {wait_time}s (attempt {attempt + 1})")
                time.sleep(wait_time)
            elif resp.status_code in (403, 503):
                logger.warning(f"Blocked on {url} ({resp.status_code})")
                return None
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")

        except RequestException as e:
            logger.error(f"Request error for {url} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    return None

def extract_products_from_html(html: str, category: str, seen_ids: Set[str]) -> List[dict]:
    """Extract products from HTML."""
    products = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("[data-listing-id]")

        for card in cards:
            listing_id = card.get("data-listing-id", "")
            if not listing_id or listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)

            # Get URL
            href = card.get("href", "")
            if not href.startswith("http"):
                href = f"{ETSY_BASE}{href}"

            # Get title
            title = ""
            link = card.select_one("a[href*='/listing/']")
            if link:
                title = link.get_text(strip=True)

            # Get price
            price = ""
            price_elem = card.select_one(".currency-value, .wt-text-title-small, [data-e2e='price']")
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                matches = re.findall(r'[\d,]+\.?\d*', price_text)
                if matches:
                    price = matches[0]

            # Get image
            img_url = ""
            img = card.select_one("img")
            if img:
                img_url = img.get("src") or img.get("data-src", "")
                if img_url.startswith("//"):
                    img_url = "https:" + img_url

            # Get seller
            seller = ""
            shop_elem = card.select_one(".wt-text-truncate.wt-mr-xs, .shop-name, [data-e2e='shop-name']")
            if shop_elem:
                seller = shop_elem.get_text(strip=True)

            products.append({
                "name": title.strip() if title else "",
                "price": price,
                "url": href,
                "brand": seller,
                "image_url": img_url,
                "category": category,
                "category_path": ["Etsy US", category],
                "listing_id": listing_id,
                "raw_data": {"listing_id": listing_id}
            })

    except Exception as e:
        logger.error(f"Error parsing products: {e}")

    return products

async def test_etsy():
    """Test Etsy scraper with limited scope."""
    logger.info("Testing Etsy scraper with 2 categories and 2 pages max...")

    products = []
    seen_ids = set()

    # Test just jewelry and clothing
    test_categories = CATEGORIES[:2]

    for cat in test_categories:
        cat_name = cat["name"]
        cat_path = cat["path"]
        page = 1

        logger.info(f"Testing {cat_name}")

        # Fetch first 2 pages only
        while page <= 2:
            url = f"{ETSY_BASE}{cat_path}?page={page}"
            logger.info(f"Fetching {cat_name} page {page}")

            html = fetch_with_retry(url)

            if not html:
                logger.warning(f"Failed to fetch {cat_name} page {page}")
                break

            page_products = extract_products_from_html(html, cat_name, seen_ids)

            if page_products:
                products.extend(page_products)
                logger.info(f"  {cat_name} page {page}: {len(page_products)} products")
            else:
                logger.info(f"  {cat_name} page {page}: no products")

            page += 1

            # Longer delay between pages
            time.sleep(5)

    logger.info(f"Test complete: {len(products)} products scraped")

    # Save results
    if products:
        with open("etsy_test_products.jsonl", "w") as f:
            for p in products:
                f.write(json.dumps(p) + "\n")

        # Print summary
        print("\n" + "="*50)
        print("ETSY TEST RESULTS")
        print("="*50)
        print(f"Total products: {len(products)}")
        for cat in test_categories:
            count = len([p for p in products if p["category"] == cat["name"]])
            print(f"  {cat['name']}: {count}")
        print("="*50)
    else:
        logger.warning("No products were scraped")

    return products

if __name__ == "__main__":
    asyncio.run(test_etsy())