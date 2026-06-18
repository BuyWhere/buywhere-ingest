# BUY-31277 Shopper Merchant-Feed Assists - RESOLVED

Date: 2026-06-05
Issue: BUY-31277
Title: [Milo] Shopper merchant-feed assists
Status: resolved
Fix: NameError in src/scrapers/__init__.py line 54

## Problem

The `catalog_live_ingest.py` script failed with a `NameError` when attempting to import the scrapers module:

```
NameError: name 'BestDenkiScraper' is not defined. Did you mean: 'BestDenkiSGScraper'?
```

The SCRAPERS dict in `src/scrapers/__init__.py` referenced `BestDenkiScraper` (line 54) but the class was imported as `BestDenkiSGScraper` (line 22). This typo prevented the entire scrapers module from loading, blocking all merchant feed operations.

## Fix

Changed line 54 in `src/scrapers/__init__.py`:

```diff
-    "best_denki_sg": BestDenkiScraper,
+    "best_denki_sg": BestDenkiSGScraper,
```

## Verification

Both configured merchants now scrape successfully in dry-run mode:

```bash
# paper_source
python3 scripts/catalog_live_ingest.py paper_source --limit 3 --dry-run
# Result: scraped 3 products (SKUs: 0196940140866, 0196940140910, 0196940140927)

# floor_and_decor
python3 scripts/catalog_live_ingest.py floor_and_decor --limit 3 --dry-run
# Result: scraped 3 products (SKUs: 100902774, 101176915, 101254522)
```

## Impact

- catalog_live_ingest.py can now load all scrapers
- Shopper merchant-feed operations unblocked
- BUY-29215 continuous merchant acquisition lane operational