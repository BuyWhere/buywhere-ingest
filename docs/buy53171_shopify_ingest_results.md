# BUY-53171: Ingest 100 US Shopify Merchants — Results

## Summary
Successfully ingested products from **92 out of 100** confirmed Shopify merchants  
via the Shopify /products.json API into the catalog database.

## Source Data
- 355 US Shopify candidates from Shopper workspace (us_shopify_candidates.json)
- 171 confirmed Shopify (signal=products_json on /products.json endpoint)
- First 100 confirmed merchants targeted for this batch

## Results

| Metric | Value |
|--------|-------|
| Merchants attempted | 100 |
| Successfully ingested | 92 |
| No products (blocked/empty) | 8 |
| Total products ingested | ~4,465 |
| Max products per merchant | 50 |

## Technical Details
- **Script**: scripts/ingest_shopify_merchants.py
- **Scraper**: src/scrapers/shopify_store.py (ShopifyScraper via /products.json?limit=250)
- **Ingestion**: src/catalog_ingest.py (upsert_products via ON CONFLICT DO UPDATE)
- **DB**: Railway Postgres (catalog pin)
- **Fix applied**: SKU fallback to variant ID when sku/barcode are null (src/scrapers/shopify_store.py)
- **Fix applied**: Pre-deduplicate by SKU within batches to avoid ON CONFLICT DO UPDATE command cannot affect row a second time

## Files Modified
- **scripts/ingest_shopify_merchants.py** — main ingestion script (new)
- **scripts/retry_shopify_merchants.py** — retry script for dupe-SKU merchants (new)
- **src/scrapers/shopify_store.py** — SKU fallback to variant ID (patched)
- **data/us_shopify_candidates.json** — copied from Shopper workspace
- **data/us_shopify_validated.json** — copied from Shopper workspace

## Notes
- 8 merchants returned 0 products via /products.json (likely behind Cloudflare blocks or empty stores)
- All 9 merchants that failed with duplicate SKU constraint were successfully retried with deduplication
