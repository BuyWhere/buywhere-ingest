# BUY-29216 Higher-Throughput Merchant Runs

Date: 2026-06-02 UTC

## Summary

Converted the restored writer path (`scripts/catalog_live_ingest.py`) from sequential single-merchant execution to concurrent multi-merchant runs using `asyncio.gather` with a configurable concurrency semaphore.

## What Changed

Modified `scripts/catalog_live_ingest.py`:

1. **Concurrent merchant execution**: Added `asyncio.gather` with a semaphore-controlled pool to run multiple merchants in parallel instead of sequentially
2. **New `--all` flag**: Run all configured merchants in a single command
3. **New `--concurrency` flag**: Control max concurrent merchant runs (default: 3)
4. **Multi-merchant result aggregation**: Returns combined results across all merchants

### Key Changes

- `_scrape_singlemerchant()`: Wraps individual merchant scrape with semaphore
- `_scrape_all_merchants()`: Uses `asyncio.gather` to run all merchants concurrently
- `_main()`: Updated to handle multiple merchant keys and aggregate results
- Metadata tag updated to reference `BUY-29216`

### CLI Interface

```bash
# Run specific merchants
python3 scripts/catalog_live_ingest.py paper_source floor_and_decor --limit 10

# Run all configured merchants concurrently
python3 scripts/catalog_live_ingest.py --all --limit 10

# Control concurrency (default 3)
python3 scripts/catalog_live_ingest.py --all --limit 10 --concurrency 5

# Dry run to verify without writing
python3 scripts/catalog_live_ingest.py --all --limit 3 --dry-run
```

## Verification

```bash
python3 -m py_compile scripts/catalog_live_ingest.py
python3 scripts/catalog_live_ingest.py --all --limit 3 --dry-run
python3 scripts/catalog_live_ingest.py --all --limit 3
```

### Dry-run output:
- 3 merchants scraped concurrently (floor_and_decor, paper_source, the_body_shop)
- 3 products per merchant = 9 total scraped

### Live run output:
- `total_written: 9` rows across all 3 merchants
- All writes targeting canonical `maglev.proxy.rlwy.net:31310`
- Metadata `_writer.issue: BUY-29216`

## Performance Characteristics

Before (sequential):
- 3 merchants × 10 products = 30 products processed serially
- Total time = sum of all merchant scrape times

After (concurrent with --concurrency 3):
- 3 merchants processed in parallel
- Total time ≈ max(individual merchant times) with concurrency=3
- Semaphore prevents overwhelming the DB or target sites