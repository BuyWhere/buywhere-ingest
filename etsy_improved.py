#!/usr/bin/env python3
"""Improved Etsy scraper with better anti-bot measures."""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Set
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import json
from pathlib import Path

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

def load_proxy() -> Optional[str]:
    """Load proxy configuration."""
    try:
        # Try to load proxy configuration
        from src.scrapers.proxy_config import proxy_url, Zone
        return proxy_url(Zone.BUYWHERE_RESI)
    except:
        return None

def fetch_with_retry(url: str, proxy: str = None, max_retries: int = 10) -> Optional[str]:
    """Fetch URL with exponential backoff and jitter."""
    headers = PRODUCT_HEADERS.copy()

    # Add random User-Agent variations
    if "Chrome" in headers["User-Agent"]:
        versions = ["90.0.4430.212", "91.0.4472.124", "92.0.4515.107"]
        headers["User-Agent"] = headers["User-Agent"].replace("Chrome/91.0.4472.124", f"Chrome/{versions[hash(url) % len(versions)]}")

    for attempt in range(max_retries):
        try:
            # Add random jitter
            jitter = 1 + (hash(url + str(attempt)) % 5) / 10
            time.sleep(jitter)

            resp = requests.get(
                url,
                proxies={"http": proxy, "https": proxy} if proxy else None,
                headers=headers,
                timeout=30,
                verify=False,
                allow_redirects=True,
            )

            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                # Rate limited - exponential backoff
                wait_time = min(60, (2 ** attempt) + (hash(url + str(attempt)) % 10))
                logger.warning(f"Rate limited on {url}, waiting {wait_time}s (attempt {attempt + 1})")
                time.sleep(wait_time)
            elif resp.status_code in (403, 503):
                # Blocked or service unavailable
                wait_time = min(300, (3 ** attempt) + (hash(url + str(attempt)) % 30))
                logger.warning(f"Blocked on {url} ({resp.status_code}), waiting {wait_time}s")
                time.sleep(wait_time)
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

        # Try multiple selectors
        selectors = [
            "[data-listing-id]",
            ".wt-card",
            ".listing-card",
            ".v2-listing-card"
        ]

        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                break

        for card in cards:
            # Get listing ID
            listing_id = card.get("data-listing-id", "")
            if not listing_id:
                # Try to extract from URL
                link = card.select_one("a[href*='/listing/']")
                if link:
                    match = re.search(r'/listing/(\d+)', link.get("href", ""))
                    if match:
                        listing_id = match.group(1)

            if not listing_id or listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)

            # Get URL
            href = card.get("href", "")
            if not href:
                link = card.select_one("a[href*='/listing/']")
                href = link.get("href", "") if link else ""

            if not href.startswith("http"):
                href = f"{ETSY_BASE}{href}"

            # Get title
            title = ""
            title_selectors = [
                ".wt-text-caption.v2-listing-card__title",
                ".card-title",
                "[data-e2e='listing-card-title']",
                "a"
            ]

            for selector in title_selectors:
                elem = card.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    if title and len(title) > 5:
                        break

            # Get price
            price = ""
            price_selectors = [
                ".currency-value",
                ".wt-text-title-small",
                "[data-e2e='price']",
                ".price"
            ]

            for selector in price_selectors:
                elem = card.select_one(selector)
                if elem:
                    price_text = elem.get_text(strip=True)
                    # Extract numeric price
                    matches = re.findall(r'[\d,]+\.?\d*', price_text)
                    if matches:
                        price = matches[0]
                        break

            # Get image
            img_url = ""
            img = card.select_one("img")
            if img:
                img_url = img.get("src") or img.get("data-src") or ""
                if img_url and img_url.startswith("//"):
                    img_url = "https:" + img_url

            # Get seller
            seller = ""
            seller_selectors = [
                ".wt-text-truncate.wt-mr-xs",
                ".shop-name",
                ".v2-listing-card__shop-name",
                "[data-e2e='shop-name']"
            ]

            for selector in seller_selectors:
                elem = card.select_one(selector)
                if elem:
                    seller = elem.get_text(strip=True)
                    break

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

async def scrape_etsy():
    """Main scraping function."""
    logger.info("Starting Etsy US scraper...")

    proxy = load_proxy()
    proxy_status = proxy or "none"
    logger.info(f"Using proxy: {proxy_status}")

    products = []
    seen_ids = set()
    total_pages = 0

    for cat in CATEGORIES:
        cat_name = cat["name"]
        cat_path = cat["path"]
        page = 1
        consecutive_empty = 0
        category_products = 0

        logger.info(f"Scraping category: {cat_name}")

        while consecutive_empty < 5 and len(products) < 100000:
            url = f"{ETSY_BASE}{cat_path}?page={page}"

            logger.info(f"Fetching {cat_name} page {page}...")
            html = fetch_with_retry(url, proxy)

            if not html:
                logger.warning(f"Failed to fetch {cat_name} page {page}")
                consecutive_empty += 1
                time.sleep(30)  # Longer wait for failures
                continue

            page_products = extract_products_from_html(html, cat_name, seen_ids)

            if page_products:
                consecutive_empty = 0
                products.extend(page_products)
                category_products += len(page_products)
                total_pages += 1

                logger.info(f"  {cat_name} page {page}: +{len(page_products)} "
                          f"(total: {category_products}, overall: {len(products)})")

                # Save progress
                if len(products) % 1000 == 0:
                    with open(f"etsy_products_{len(products)}.jsonl", "w") as f:
                        for p in products[-1000:]:
                            f.write(json.dumps(p) + "\n")

                if len(products) >= 100000:
                    break
            else:
                consecutive_empty += 1
                logger.info(f"  {cat_name} page {page}: no products "
                          f"(consecutive empty: {consecutive_empty})")

            page += 1
            # Longer delay between pages to avoid rate limiting
            time.sleep(10 + (hash(url) % 5))

    logger.info(f"Etsy US scraper complete: {len(products)} products from {total_pages} pages")

    # Save final results
    if products:
        with open("etsy_final_products.jsonl", "w") as f:
            for p in products:
                f.write(json.dumps(p) + "\n")

        # Also save a summary
        summary = {
            "total_products": len(products),
            "categories": {cat["name"]: len([p for p in products if p["category"] == cat["name"]])
                          for cat in CATEGORIES},
            "total_pages": total_pages,
            "timestamp": time.time()
        }

        with open("etsy_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Products saved to etsy_final_products.jsonl")
        logger.info(f"Summary saved to etsy_summary.json")

        # Print summary
        print("\n" + "="*60)
        print("ETSY SCRAPING SUMMARY")
        print("="*60)
        print(f"Total products scraped: {len(products)}")
        print("Products by category:")
        for cat, count in summary["categories"].items():
            print(f"  {cat}: {count}")
        print(f"Total pages processed: {total_pages}")
        print("="*60)

    return products

if __name__ == "__main__":
    asyncio.run(scrape_etsy())