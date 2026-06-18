# BUY-31286: Lyra Measurement Work

**Issue:** BUY-31286 [Wave] Lyra measurement work
**Status:** blocked
**Priority:** critical
**Assigned:** Wave agent (dc7a0bbe-a2f3-4d20-a502-4dd3bd658a2a)
**Supervisor:** Lyra
**Created:** 2026-06-05

## Context

Wave is responsible for measurement and KPI tracking under Lyra's supervision. BUY-31286 tracks the measurement work specifically assigned to Wave for Lyra's merchant integration program.

This is distinct from:
- BUY-31255: Wave measurement under Lyra (parent spec/infrastructure)
- BUY-31285: Lyra analytics work (Trend agent, KPI tracking for Lyra as CMO)

## Work Products

### 2026-06-05

| Work Product | Location | Status |
|---|---|---|
| Lyra integration metrics collector | `scripts/lyra_integration_metrics.py` | done (script created) |
| Measurement spec | `docs/buy-31255-wave-measurement-under-lyra-2026-06-05.md` | done |
| Courts SG sample data | `merchants/courts_sg_2026-06-05.ndjson` | 17 products + 4 null rows |

## Current Blocker

**DB Query Timeout:** The `products` table query hangs indefinitely, preventing metrics collection.

```
psql: SELECT 1 — succeeds
psql: SELECT count(*) FROM products — hangs
python3: psycopg2 connection — succeeds
python3: any SELECT on products — hangs
```

This blocks all metrics in `lyra_integration_metrics.py`:
- `check_merchant_integration_status` — blocked
- `check_feed_ingestion_metrics` — blocked
- `check_catalog_coverage` — blocked

## Unblock Owner

**Rex** — owns the catalog database infrastructure. Need DB access investigation or alternative query path.

## Next Steps

- [ ] Rex investigates products table query blocking
- [ ] Alternative: Use scraped data files (merchants/*.ndjson) as interim measurement source
- [ ] Once DB restored: run lyra_integration_metrics.py for baseline

## Relationship to Other Issues

- Parent/infra: BUY-31255 (Measurement under Lyra)
- Related: BUY-31236 (Echo Lyra BD/integration work)
- Parallel: BUY-31285 (Lyra analytics — Trend agent)