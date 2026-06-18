# BUY-32036 — Hourly catalog drift + ingest health tracker (2026-06-06 02:00 UTC)

**Result: COMPLETE — tracking period through 2026-06-06 06:00 UTC has ended.**

## Tracking period
- Started: 2026-06-05 (aligned with BUY-31179 catalog drift investigation)
- Ended: 2026-06-06 06:00 UTC (deadline met)
- Final capture: 2026-06-06T02:00:28 UTC

## Final health snapshot (2026-06-06T02:00:28 UTC)

### Runtime `/v1/catalog/stats`
```json
{
  "data": {
    "total_products": 31181580,
    "total_merchants": 64812,
    "active_products": 31181580
  },
  "meta": {
    "approximate": true,
    "source": "pg_class_estimate",
    "ts": "2026-06-06T02:00:42.673Z"
  }
}
```

### Health monitor results

| Check | Status | Message |
|---|---|---|
| db_freshness | warning | DB max(updated_at) timed out; last autoanalyze 2.5h ago — DB under heavy load |
| runtime_canonical_divergence | warning | Could not get canonical count (DB timeout or unavailable) |
| source_diversity | warning | Source diversity from stale catalog_stats (79h old): 6405 sources |
| api_latency | healthy | API latency healthy: p95=64ms |
| health_endpoints | healthy | All health endpoints OK |

**Overall: WARNING**

### Key observations

1. **Runtime source changed**: Runtime now reports `source=pg_class_estimate` (previously `catalog_stats` per BUY-31179). The pg_class estimate (31.18M) may be closer to actual than the BUY-31179 frozen value of 16.8M, but is still approximate.

2. **DB under heavy load**: Exact count queries timing out; autoanalyze last ran 2.5h prior. Cannot confirm canonical divergence without exact count.

3. **catalog_stats stale**: Pre-aggregated catalog_stats table is 79h old (last refresh ~2026-06-03T07:00 UTC). Source diversity data may not reflect current state.

4. **Runtime/canonical gap unknown**: Cannot compute divergence — DB timeout prevents canonical count retrieval.

5. **API infrastructure healthy**: Latency p95=64ms (well below thresholds), all health endpoints returning 200.

## Required follow-up

The DB-heavy-load issue is blocking canonical divergence verification. This should be addressed in a separate issue if持续的 canonical count monitoring is required.

## Child issues from BUY-31179 (still relevant)
- [BUY-31180](/BUY/issues/BUY-31180) — Flux: restore runtime exact-count path
- [BUY-31181](/BUY/issues/BUY-31181) — Ops: grant buywhere_ingest refresh permissions

## Parent
- Related: [BUY-31179](/BUY/issues/BUY-31179) (catalog drift verification 2026-06-05)
