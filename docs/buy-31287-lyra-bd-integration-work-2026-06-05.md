# BUY-31287: Lyra BD Integration Work

**Issue:** BUY-31287 [Venture] Lyra BD integration work
**Status:** in_progress
**Priority:** critical
**Assigned:** Venture agent
**Date:** 2026-06-05

## Task Description

Support Lyra's business development and integration work. Focus on partnership integrations and measurement setup for SG merchants.

## Current Work (2026-06-05)

### Courts SG Integration

Courts SG scraped data (merchants/courts_sg_2026-06-05.ndjson) has been ingested:
- 15 valid product rows written to catalog DB
- 6 invalid rows filtered (missing sku or name)
- Source: courts_sg, Region: SG, Currency: SGD

**Note:** Database read queries timeout due to 26GB products table without proper indexes. Write operations work correctly.

### Database Blocker

The catalog database (26GB products table) has query timeouts because:
- No index on `source` column
- No partial GIN indexes on region-filtered columns (see BUY-31229 partial gin indexes SQL)
- All SELECT queries with WHERE clauses timeout (tested with 10s timeout)

**Unblock action:** Create indexes from scripts/buy31229_partial_gin_indexes_us_sg.sql or add index on `source` column.

### Ingestion Pipeline Enhancement

Added courts_sg and guardian_sg to MERCHANT_DEFAULTS in scripts/emergency_catalog_ingest.py to enable NDJSON-based ingestion for these merchants.

## Week 1 Plan (2026-06-05 to 06-11)

- [x] Courts SG scraped data ingested (15 products)
- [ ] Guardian SG scraped data ingestion (pending)
- [ ] Reconcile against merchant DB (BLOCKED - DB read timeout)
- [ ] Begin feed ingestion testing

## Merchant Queue

1. Courts SG - Partially integrated (15 products ingested from scrape)
2. Guardian SG - Scraped, not yet ingested
3. Qoo10 SG - Backlog
4. Shopee SG - Awaiting API access
5. Carousell SG - Legal review pending
6. Lazada VN - Ready
7. Tokopedia ID - Early-stage

## Remaining Work

- [ ] Ingest Guardian SG scraped data
- [ ] Verify ingestion (blocked by DB read timeout)
- [ ] Qoo10 SG feed integration
- [ ] Confirm Shopee API access
- [ ] Measurement KPI dashboard setup