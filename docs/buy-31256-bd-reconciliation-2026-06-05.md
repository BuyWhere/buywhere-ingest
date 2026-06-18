# BUY-31256 BD Integration Reconciliation — 2026-06-05

## Issue
[BUY-31256](/BUY/issues/BUY-31256) — [Venture] BD integration under Echo

## Week 1 Status

### Courts SG
- **Status:** Scraped, data quality issues identified
- **Products:** 21 records saved to `merchants/courts_sg_2026-06-05.ndjson`
- **Issues:**
  - Brand field misaligned (picking up cross-sell/related product data)
  - Some null entries in name/price/url fields
  - Scraper may need brand extraction fix

### Guardian SG
- **Status:** Blocked — scraper broken (website structure changed)
- **Child Issue:** [BUY-31299](/BUY/issues/BUY-31299) created
- **Selector Issue:** `.product-item, .product-card` returns 0 elements

## Merchant Config Updates

Added to `data/.merchant_configs.json`:
- `courts_sg` — active, SGD currency
- `guardian_sg` — inactive (scraper broken), SGD currency

## Reconciliation Summary

| Merchant | Scraped | Configured | Ingest Ready | Issues |
|----------|---------|------------|--------------|--------|
| Courts SG | 21 | Yes | Partial | Brand extraction quality |
| Guardian SG | 0 | Yes | No | Scraper broken |

## Next Steps

1. **BUY-31299** (child): Fix Guardian SG scraper
2. Fix Courts SG brand extraction logic
3. Reconcile against merchant DB once data quality resolved
4. Begin feed ingestion testing

## Dependencies

- [BUY-31299](/BUY/issues/BUY-31299) — Guardian SG scraper fix (blocks Guardian SG integration)