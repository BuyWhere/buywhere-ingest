#!/usr/bin/env python3
"""Full product scraper for Guardian MY via GraphQL."""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

import httpx
from tqdm import tqdm

GRAPHQL_URL = "https://www.guardian.com.my/graphql"
PAGE_SIZE = 200
OUTPUT_DIR = "data"

QUERY_PRODUCTS = """query Products($pageSize: Int!, $currentPage: Int!) {
  products(search: "", pageSize: $pageSize, currentPage: $currentPage) {
    total_count
    items {
      name
      sku
      url_key
      price { regularPrice { amount { value currency } } }
    }
    page_info { total_pages }
  }
}"""


async def fetch_page(client: httpx.AsyncClient, page: int) -> list[dict]:
    """Fetch one page of products."""
    resp = await client.post(
        GRAPHQL_URL,
        json={
            "query": QUERY_PRODUCTS,
            "variables": {"pageSize": PAGE_SIZE, "currentPage": page},
        },
    )
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL error on page {page}: {data['errors']}")
    return data["data"]["products"]


async def scrape_all() -> list[dict]:
    """Scrape all 9,461 products from Guardian MY via concurrent GraphQL calls."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=60, headers=headers) as client:
        # Get pagination info
        info = await fetch_page(client, 1)
        total_count = info["total_count"]
        total_pages = info["page_info"]["total_pages"]
        print(f"Total products: {total_count} across {total_pages} pages (pageSize={PAGE_SIZE})")

        # Fetch all pages concurrently
        tasks = [fetch_page(client, p) for p in range(1, total_pages + 1)]
        all_items = []
        with tqdm(total=total_pages, desc="Fetching pages", unit="page") as pbar:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                all_items.extend(result["items"])
                pbar.update(1)

        return all_items


def main():
    start = time.time()
    print(f"[{datetime.utcnow().isoformat()}] Starting Guardian MY full product scrape...")
    
    products = asyncio.run(scrape_all())
    
    elapsed = time.time() - start
    print(f"Fetched {len(products)} products in {elapsed:.1f}s")

    # Write output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    outpath = os.path.join(OUTPUT_DIR, f"guardian_my_full_{timestamp}.ndjson")
    
    with open(outpath, "w") as f:
        for product in products:
            f.write(json.dumps(product, ensure_ascii=False) + "\n")

    # Also write to fixed location for downstream
    fixed_path = os.path.join(OUTPUT_DIR, "guardian_my_full_product_scrape.ndjson")
    with open(fixed_path, "w") as f:
        for product in products:
            f.write(json.dumps(product, ensure_ascii=False) + "\n")

    print(f"Output: {outpath} ({os.path.getsize(outpath)} bytes)")
    print(f"Fixed:  {fixed_path} ({os.path.getsize(fixed_path)} bytes)")
    print(f"[{datetime.utcnow().isoformat()}] Scrape complete.")


if __name__ == "__main__":
    main()
