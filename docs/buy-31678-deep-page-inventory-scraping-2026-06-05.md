# BUY-31678: Deep-page product detail scraping for inventory lane

## Summary
Added support for scraping individual Shopify product detail pages to extract inventory/stock status for the inventory lane.

## Changes Made

### 1. `src/scrapers/base_scraper.py`
- Added `in_stock: Optional[bool] = None` field to `Product` dataclass
- This field captures inventory/availability status from product detail pages

### 2. `src/scrapers/shopify_product_page.py` (new file)
- Created `ShopifyProductPageScraper` class for deep-page inventory scraping
- Methods:
  - `scrape_products(product_handles: List[str])` - scrape multiple products by handles
  - `scrape_product(handle: str)` - scrape single product by handle
- Parses inventory status from:
  - `var product = {...}` JavaScript object in page HTML (primary method)
  - Stock/inventory/availability CSS class elements
  - Add-to-cart button disabled state
- Also extracts: price, name, SKU, image URL

### 3. `src/scrapers/__init__.py`
- Added import for `ShopifyProductPageScraper`

## Usage Example

```python
from src.scrapers import ShopifyProductPageScraper

async def scrape_inventory():
    async with ShopifyProductPageScraper('https://shop.example.com') as scraper:
        # Scrape multiple products
        products = await scraper.scrape_products(['product-handle-1', 'product-handle-2'])
        for p in products:
            print(f"{p.name}: in_stock={p.in_stock}")

        # Or scrape single product
        product = await scraper.scrape_product('product-handle-1')
        print(f"SKU: {product.sku}, in_stock: {product.in_stock}")
```

## Integration
The `in_stock` field is now available in the `Product` dataclass and will be included when products are upserted via `catalog_ingest.py`.

## Verification
- All Python files pass syntax check
- Module imports correctly
- Context manager works properly
