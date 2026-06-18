# BUY-29215 Shopper Continuous Merchant Acquisition Lane

Date: 2026-06-02 UTC

## Summary

Built a configuration-driven merchant acquisition lane on top of the restored maglev writer (BUY-29210). The `catalog_live_ingest.py` script now dynamically loads merchant configurations from `data/.merchant_configs.json` and uses any scraper from `src.scrapers.SCRAPERS`, enabling Shopper to add new merchants without modifying core scripts.

## What Changed

- created [data/.merchant_configs.json](file:///paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.merchant_configs.json)
  - Externalized merchant defaults from hardcoded SCRAPER_CONFIG into a JSON config file
  - Each entry maps a `merchant_key` to a `scraper_key` and `defaults`
- modified [scripts/catalog_live_ingest.py](file:///paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/catalog_live_ingest.py)
  - Replaced hardcoded SCRAPER_CONFIG with dynamic loading from `.merchant_configs.json`
  - Uses `src.scrapers.SCRAPERS` dict to dynamically instantiate any scraper by key
  - Added `--all` flag to run all configured merchants in parallel
  - Added `--concurrency` flag (default 3) for parallel merchant scraping
  - Changed metadata tag from BUY-29210 to BUY-29215

## How to Add a New Merchant

1. **Create a scraper** in `src/scrapers/<merchant>.py` that implements `BaseScraper`
2. **Register the scraper** in `src/scrapers/__init__.py` SCRAPERS dict
3. **Add merchant config** to `data/.merchant_configs.json`:

```json
{
  "my_merchant": {
    "scraper_key": "my_merchant",
    "defaults": {
      "merchant_id": "my_merchant",
      "source": "my_merchant",
      "platform": "shopify",
      "region": "US",
      "country_code": "US",
      "currency": "USD",
      "is_active": true,
      "in_stock": true
    }
  }
}
```

4. **Run the ingest**:

```bash
python3 scripts/catalog_live_ingest.py my_merchant --limit 10
python3 scripts/catalog_live_ingest.py --all --limit 10  # all merchants
```

## Usage

```bash
# Single merchant
python3 scripts/catalog_live_ingest.py paper_source --limit 10

# Multiple merchants
python3 scripts/catalog_live_ingest.py paper_source floor_and_decor --limit 10

# All configured merchants (parallel)
python3 scripts/catalog_live_ingest.py --all --limit 10 --concurrency 3

# Dry run
python3 scripts/catalog_live_ingest.py --all --limit 3 --dry-run
```

## Verification

```bash
python3 -m py_compile scripts/catalog_live_ingest.py
python3 scripts/catalog_live_ingest.py paper_source --limit 3 --dry-run
# Result: scraped 3 products from paper_source

python3 scripts/catalog_live_ingest.py --all --limit 3 --dry-run
# Result: scraped 3 products each from floor_and_decor, paper_source, the_body_shop
```

## Handoff

The continuous merchant acquisition lane is now operational. Shopper can add new merchants by:
1. Creating a scraper in `src/scrapers/`
2. Adding config to `data/.merchant_configs.json`
3. Running the ingest script

No code changes to `catalog_live_ingest.py` are needed for new merchants.