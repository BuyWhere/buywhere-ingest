# BUY-53279: Thailand Home/Kitchen Ingestion Lane — Power Buy + Central Online

**Date:** 2026-06-19  
**Agent:** Hex

---

## Power Buy Thailand (`powerbuy_th`)

**Status:** ✅ Delivered — 233 home/kitchen products ingested

**Approach:**
- Power Buy runs on Next.js behind Cloudflare WAF
- Accessed via Brightdata residential proxy
- Product URL discovery via sitemap (`/sitemap/product-sitemap-1.xml`) — 10,102 total products
- Home/kitchen filter applied via slug keywords: **2,396 HK products** identified
- Product data extraction via JSON-LD structured data from product pages
- 233 products scraped and ingested into catalog DB (46.6% hit rate; Cloudflare blocks ~53% of product page requests)

**Data quality:**
- 100% with prices, brands, images, stock status
- 39 brands including BOSCH, DAIKIN, DYSON, CARRIER, ELECTROLUX, DELONGHI
- Price range: 199 THB — 118,500 THB (median 7,990 THB)
- All with THB currency, Thailand region, correct merchant metadata

**Files created:**
- `scripts/ingest_powerbuy_th_home_kitchen.py` — standalone ingestion script
- `src/scrapers/powerbuy_th.py` — scraper module for pipeline integration
- Registered in `src/scrapers/__init__.py`

**Remaining:** Full 2,396-product run would take ~12 min. The current 233 products cover the hit rate from the first 500 URLs attempted. For full coverage, run with `--max-products 2396` (exposes to ~53% Cloudflare miss rate, expect ~1,100 products).

---

## Central Online Thailand (`central_th`)

**Status:** ⏳ Scraper built but blocked by Cloudflare — not currently runnable

**Approach:**
- Central Online is behind aggressive Cloudflare WAF
- Brightdata residential proxy intermittently fails (502/403 errors)
- Scraper supports dual-mode access: httpx (when proxy works) + Playwright (for challenge bypass)
- Category paths identified from site navigation

**Files created:**
- `scripts/ingest_central_th_home_kitchen.py` — ingestion script with Playwright fallback
- `src/scrapers/central_th.py` — scraper module
- Registered in `src/scrapers/__init__.py`

**Blocked until:** Brightdata residential proxy rotation provides working TH-based egress, OR dedicated proxy solution is configured for central.co.th

---

## Usage

```bash
# Power Buy — full run with ingestion
python scripts/ingest_powerbuy_th_home_kitchen.py --max-products 2396

# Power Buy — scrape only (no DB write)
python scripts/ingest_powerbuy_th_home_kitchen.py --skip-ingest --max-products 100

# Central Online — attempt scrape (may fail if proxy blocked)
python scripts/ingest_central_th_home_kitchen.py --max-products 200
```
