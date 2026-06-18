# BUY-31512 Hunt 2: Ingest Non-Shopify Merchant Catalog (Zalora / Tokopedia)

**Status:** Blocked - awaiting Playwright system dependencies and network access
**Created:** 2026-06-05
**Agent:** Hunt 2 (708a8ce4-96dd-409d-94e7-a91d5032e4e0)

## Work Completed

### Scraper Implementation
1. **Created `src/scrapers/zalora_sg.py`** - Zalora Singapore fashion e-commerce scraper
   - Uses Playwright for JavaScript rendering (required due to JS-heavy SPA)
   - Supports product name, price, brand, image, URL extraction
   - Includes fallback to basic HTTP fetch

2. **Created `src/scrapers/tokopedia.py`** - Tokopedia Indonesia e-commerce marketplace scraper
   - Custom API pattern with price extraction
   - Supports product name, price, brand, image, URL extraction

3. **Updated `src/scrapers/__init__.py`**
   - Registered `ZaloraSGScraper` as `zalora_sg`
   - Registered `TokopediaScraper` as `tokopedia`
   - SCRAPERS dict now contains 36 merchants

4. **Updated `scripts/catalog_live_ingest.py`**
   - Added `zalora_sg` to SCRAPER_CONFIG with SGD currency, SG region
   - Added `tokopedia` to SCRAPER_CONFIG with IDR currency, ID region

5. **Updated `data/.merchant_configs.json`**
   - Added `zalora_sg` configuration
   - Added `tokopedia` configuration

## Integration Verification

```python
# Verified imports work:
from src.scrapers import SCRAPERS
print('zalora_sg' in SCRAPERS)  # True
print('tokopedia' in SCRAPERS)    # True

# Verified catalog_live_ingest.py integration:
import scripts.catalog_live_ingest as cli
print('zalora_sg' in cli.SCRAPER_CONFIG)  # True
print('tokopedia' in cli.SCRAPER_CONFIG)   # True
```

## Blockers

### Blocker 1: Playwright System Dependencies Missing
**Impact:** Zalora scraper cannot render JavaScript, returns 0 products
**Error:**
```
error while loading shared libraries: libatk-1.0.so.0: cannot open shared object file
```
**Fix:** Run `npx playwright install-deps chromium` or install system dependencies manually

### Blocker 2: Tokopedia Network Unreachable
**Impact:** Tokopedia scraper cannot fetch any content (timeout)
**Error:**
```
httpcore.ReadTimeout: Task timed out
```
**Fix:** Requires network access to Tokopedia domain - may be geo-blocking or DDoS protection

## Next Steps

1. **Unblock Playwright** - Install Playwright system dependencies on the agent workspace
2. **Test Zalora** - After Playwright deps installed, run `python3 scripts/catalog_live_ingest.py zalora_sg --limit 10 --dry-run`
3. **Investigate Tokopedia** - May need ScraperAPI or similar service for JS rendering + geo-unblocking

## Files Changed

- `src/scrapers/zalora_sg.py` (new)
- `src/scrapers/tokopedia.py` (new)
- `src/scrapers/__init__.py` (modified)
- `scripts/catalog_live_ingest.py` (modified)
- `data/.merchant_configs.json` (modified)