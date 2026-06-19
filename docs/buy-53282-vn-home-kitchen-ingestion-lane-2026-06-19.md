# BUY-53282 Vietnam home/kitchen ingestion lane

Date: 2026-06-19

## Outcome

Opened two Vietnam home/kitchen ingestion lanes:

### LocknLock Vietnam (locknlock_vn)
- **Site**: https://www.locknlock.vn (Salesforce Commerce Cloud)
- **Approach**: Sitemap-driven product page scraping via JSON-LD structured data
- **Products ingested**: 108 (all vi-vn locale products from sitemap)
- **Script**: `scripts/ingest_locknlock_vn_home_kitchen.py`
- **Snapshot**: `merchants/locknlock_vn_home_kitchen_2026-06-19.ndjson`
- **Query coverage**: food containers, water bottles, cookware, kitchen tools
- **Repeatable**: rerun with `python3 scripts/ingest_locknlock_vn_home_kitchen.py`

### Nguyen Kim Vietnam (nguyen_kim_vn)
- **Site**: https://www.nguyenkim.com (CS-Cart)
- **Approach**: Category page scraping via embedded `dataRenderProduct.push(...)` JS data
- **Products ingested**: 369 (deduplicated across 22 home/kitchen category pages with pagination)
- **Script**: `scripts/ingest_nguyen_kim_vn_home_kitchen.py`
- **Snapshot**: `merchants/nguyen_kim_vn_home_kitchen_2026-06-19.ndjson`
- **Query coverage**: cookware, pots/pans, coffee makers, air fryers, rice cookers, kettles, kitchen tools, appliances
- **Repeatable**: rerun with `python3 scripts/ingest_nguyen_kim_vn_home_kitchen.py`

## Categories scraped (Nguyen Kim)
- nha-bep: 8 | noi-chao: 48 | dung-cu-nha-bep: 8
- may-pha-ca-phe: 32 | bep-tu: 86 | lo-nuong: 21
- lo-vi-song: 61 | noi-chien: 51 | bep-dien: 86
- may-xay-thit: 19 | may-danh-trung: 4 | may-ep-trai-cay: 31
- bo-noi-tefal: 18 | bo-noi-fissler: 2 | bo-noi-fivestar: 3 | bo-noi-supor: 5
- gia-dung: 380 | dung-cu-nha-bep-delaware: 1

## Total VN home/kitchen catalog addition
- **LocknLock VN**: 108 products
- **Nguyen Kim VN**: 369 products
- **Combined total**: 477 products

## Notes
- Nguyen Kim uses NxCloud CDN that required cookie-persistent sessions. Individual product pages return server-rendered shells without structured data, so category-page scraping via `dataRenderProduct.push(...)` was used instead.
- LocknLock uses Salesforce Commerce Cloud (SFCC). Product detail pages contain excellent JSON-LD structured data with name, SKU, price, and brand.
- Both scripts registered as scraper classes in `src/scrapers/` and in `src/scrapers/__init__.py`.
