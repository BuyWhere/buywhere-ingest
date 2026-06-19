# BUY-53271 ID Grocery Ingestion Wave — Alfagift + Klik Indomaret

Date: 2026-06-19
Parent: BUY-53258 (Grocery SEA gap-fill targets)

## Scrapers created

### 1. Alfagift ID (`src/scrapers/alfagift_id.py`)

- **Site**: https://alfagift.id
- **Stack**: Nuxt.js SPA (Vue) with Spring Boot backend at `webcommerce-gw.alfagift.id`
- **Method**: Playwright + Brightdata residential proxy + Stealth
- **Strategy**: Renders search pages via Playwright, captures API responses from `webcommerce-gw` backend to extract structured product data
- **Search queries**: Covers grocery alphabet (a-z) plus branded Indonesian grocery terms (indomie, beras, gula, minyak, kopi, etc.)
- **Max products**: 20,000
- **Expected uplift**: 10K–20K ID grocery SKUs
- **Key queries to recover**: indomie, instant noodle, ground coffee, cooking oil

### 2. Klik Indomaret (`src/scrapers/klik_indomaret.py`)

- **Site**: https://www.klikindomaret.com
- **Stack**: Behind Cloudflare WAF challenge
- **Method**: Playwright + Brightdata residential proxy + Stealth to solve Cloudflare
- **Strategy**: Crawls grocery category pages, parses rendered HTML / `__NEXT_DATA__` for product extraction
- **Grocery categories**: makanan, minuman, sembako, bumbu-dapur, mie, beras, minyak-goreng, susu, etc.
- **Max products**: 15,000
- **Expected uplift**: 8K–15K ID grocery SKUs
- **Key queries to recover**: indomie goreng, instant coffee, soy sauce, rice

## Ingestion runner

`scripts/ingest_id_grocery.py` — sequential runner that:
1. Runs Alfagift scraper → saves NDJSON to `data/alfagift_id_<timestamp>.ndjson`
2. Runs Klik Indomaret scraper → saves NDJSON to `data/klik_indomaret_<timestamp>.ndjson`
3. Logs summary of products collected per merchant

## Registration

Both scrapers are registered in `src/scrapers/__init__.py` with:
- Imports: `AlfagiftIDScraper`, `KlikIndomaretScraper`
- SCRAPERS dict entries: `alfagift_id`, `klik_indomaret`

## Usage

```bash
cd /path/to/repo
python3 scripts/ingest_id_grocery.py
```

## Notes

- Both scrapers require Brightdata residential proxy credentials (`BRIGHTDATA_RESIDENTIAL_USERNAME` / `BRIGHTDATA_RESIDENTIAL_PASSWORD`)
- Alfagift is a full SPA — direct HTTP requests only return the Vue shell; JS rendering is required
- Klik Indomaret has aggressive Cloudflare WAF that requires Playwright + stealth to bypass
- The scrapers are designed to be iterative — search queries and categories can be expanded as coverage matures
