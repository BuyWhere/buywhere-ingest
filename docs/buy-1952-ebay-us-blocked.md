# BUY-1952 eBay US — Blocked: Credential Infrastructure Missing

**Date:** 2026-06-09
**Agent:** Shelf (6e32b337-dd25-4057-9b0e-e49be451575b)
**Status:** `blocked`

## Root Cause of Prior Timeout

Prior run `60779534-854d-4fce-aafe-3fbc57900330` timed out after 1800s because **no scraping mechanism works**:

| Mechanism | Status | Evidence |
|-----------|--------|----------|
| Brightdata residential proxy | **407 Invalid Auth** | Zone password env vars not set (`BRIGHTDATA_RESIDENTIAL_PASSWORD` absent). Zone: `brd-customer-hl_3ab737be-zone-residential` → `brd.superproxy.io:22225` |
| ScraperAPI | **Out of credits** | `SCRAPERAPI_KEY=0832602ba87752788b2cd9ab6cef34df` → "You have exhausted the API Credits" |
| Direct HTTP to eBay | **403 Forbidden** | eBay blocks data center IPs |
| eBay Finding API | **No App ID** | `SECURITY-APPNAME` / `EBAY_APP_ID` not in environment |
| Playwright | **Missing libs** | `libatk-1.0.so.0` not in `/home/paperclip/playwright-deps/lib/` |

## What's Implemented

- **`src/scrapers/ebay_us.py`** — 440 lines, follows `BaseScraper` + Playwright pattern
- Registered in **`src/scrapers/__init__.py`** as `ebay_us`
- 20 categories: electronics (8), fashion (6), collectibles (4), home & garden (2), auto (1)
- Buy It Now filter (`LH_BIN=1`), 100 pages per category
- NDJSON output to `/home/paperclip/buywhere-api/data/ebay_us/ebay_us_<timestamp>.ndjson`
- Tags: `region=us`, `country_code=US`, `currency=USD`, `merchant_id=ebay_us`

## Unblock Actions

| Owner | Action |
|-------|--------|
| **Rex/Board** | **Option A (preferred):** Set `BRIGHTDATA_RESIDENTIAL_PASSWORD` env var. Zone `brd-customer-hl_3ab737be-zone-residential` → `brd.superproxy.io:22225`. Retrieve from Brightdata dashboard at `dashboard.brightdata.com` |
| **Rex/Board** | **Option B:** Register eBay developer app at developer.ebay.com, get `SECURITY-APPNAME`, set `EBAY_APP_ID` env var. Then use `ebay_us_api.py` path (no proxy needed) |
| **Rex/Board** | **Option C:** Refill ScraperAPI credits at scraperapi.com/dashboard |

## Execution Command (when unblocked)

```bash
# From repo root:
python3 run_scrapers.py
# Or with correct LD_LIBRARY_PATH for Playwright:
LD_LIBRARY_PATH=/home/paperclip/playwright-deps/lib:$LD_LIBRARY_PATH python3 run_scrapers.py
```

## Why This Is Blocked Not Todo

The scraper code is complete and correct. The failure is infrastructure-level: Brightdata zone credentials need to be retrieved from the Brightdata dashboard and set as environment variables. This is a board/Rex action, not an agent implementation task.
