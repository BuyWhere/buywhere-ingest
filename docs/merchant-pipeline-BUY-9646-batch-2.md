# BUY-9646 Batch 2 Merchant Pipeline

Date: 2026-05-29
Issue: BUY-9646
Parent: BUY-26287
Last Updated: 2026-05-29T06:24 Oracle execution

## Merchant Classification

### Tier 1: Executed (2026-05-29)

| Merchant | Feed URL | Status | Work Product |
|----------|----------|--------|--------------|
| Paper Source | `https://www.papersource.com/sitemap.xml` | ✅ Done | `merchants/paper_source_2026-05-29.ndjson` |
| Floor & Decor | `https://www.flooranddecor.com/sitemap-PDP.xml` | ✅ Done | `merchants/floor_and_decor_2026-05-29.ndjson` |
| The Body Shop US | `https://www.thebodyshop.com/sitemap_products_1.xml?...` | ✅ Done | `merchants/the_body_shop_2026-05-29.ndjson` |

### Tier 2: API-Specific Path Required

| Merchant | Status | Action Required |
|----------|--------|-----------------|
| Etsy | ℹ️ HTML docs | Route to Etsy API ingestion pipeline (existing issues: BUY-2968, BUY-2964) |

### Tier 3: Anti-Bot Protected (Proxy/Browser Required)

| Merchant | Original URL | Protection | Status |
|----------|--------------|------------|--------|
| Crutchfield | `https://www.crutchfield.com/sitemap.xml` | Cloudflare | 403 |
| Monoprice | `https://www.monoprice.com/sitemap.xml` | Cloudflare | 403 |
| The Container Store | `https://www.containerstore.com/site-map.xml` | PerimeterX | 307 redirect |
| Room & Board | `https://www.roomandboard.com/sitemap.xml` | Unknown | No response |
| iHerb | `https://www.iherb.com/sitemap.xml` | Challenge page | 403 |
| Backcountry | `https://www.backcountry.com/sitemap.xml` | Cloudflare | 403 |
| The RealReal | `https://www.therealreal.com/sitemap.xml` | Challenge page | 403 |

## Out-of-Scope Follow-Up Candidates

These merchants no longer belong in the "sitemap-easy" execution slice. They need separate routing outside BUY-9646.

Child issue creation failed during routing fan-out with API `500 Internal Server Error`, so the list below is preserved as a handoff package rather than an active blocker chain on this issue.

| # | Title | Priority | Description |
|---|-------|----------|-------------|
| 1 | Etsy API ingestion routing | high | No public sitemap; route to Etsy API pipeline |
| 2 | Crutchfield proxy/browser | medium | Cloudflare 403 |
| 3 | Monoprice proxy/browser | medium | Cloudflare 403 |
| 4 | The Container Store proxy/browser | medium | PerimeterX 307 |
| 5 | Room & Board feed discovery | medium | No response - needs discovery or browser |
| 6 | iHerb proxy/browser | medium | Challenge page 403 |
| 7 | Backcountry proxy/browser | medium | Cloudflare 403 |
| 8 | The RealReal proxy/browser | medium | Challenge page 403 |

## Final Disposition

BUY-9646 is complete as a sitemap-easy batch.

- The valid sitemap-easy merchants in the original batch have been executed:
  - `Paper Source`
  - `Floor & Decor`
  - `The Body Shop US`
- `Etsy` was a batch-classification error and requires API routing, not sitemap ingestion.
- `Crutchfield`, `Monoprice`, `The Container Store`, `Room & Board`, `iHerb`, `Backcountry`, and `The RealReal` require proxy/browser-backed collection and should be handled as separate non-sitemap follow-up work.

## Summary

- **Total merchants**: 11
- **Executed**: 3 (Paper Source, Floor & Decor, The Body Shop US)
- **API path needed**: 1 (Etsy)
- **Proxy/browser needed**: 7

## Evidence

- Recovery: `docs/buy-9646-sitemap-easy-batch-2-recovery-2026-05-29.md`
- Pipeline: this document
- Oracle execution notes: `docs/buy-9646-papersource-execution-2026-05-29.md`
