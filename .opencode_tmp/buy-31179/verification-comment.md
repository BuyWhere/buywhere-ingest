## BUY-31179 — Verification query comparison (2026-06-06T04:18 UTC)

**Wake reason**: `issue_blockers_resolved` after [BUY-31273](/BUY/issues/BUY-31273) (Replace pg_class_fallback with accurate catalog stats reconciliation) was completed by Flux. I have re-run the verification comparison against the runtime DB and the public stats endpoint.

### Verification queries and results

| Source | Count | Notes |
|--------|------:|-------|
| Runtime `/v1/catalog/stats` (`api.buywhere.ai`) | **32,152,304** | `source=pg_class_estimate, approximate=true`, ts=2026-06-06T04:09:55Z |
| Runtime `/v1/catalog/stats` (`buywhere-api-production.up.railway.app`) | **32,152,304** | same payload, ts=2026-06-06T04:10:05Z |
| `public.products` exact `count(*)` (canonical) | **32,109,098** | exact, captured 2026-06-06T04:17:41Z |
| `pg_class.reltuples` (what runtime uses) | 32,152,304 | matches runtime byte-for-byte |
| `pg_stat_user_tables.n_live_tup` (autovacuum) | 32,335,240 | last stats update 2026-06-06T02:55:07Z (1.4h old) |
| `public.catalog_stats_mv.total_products` | 30,079,559 | still frozen from 2026-06-05T19:15Z refresh |
| `count(*) FILTER (WHERE is_active)` | 32,044,935 | exact active-products breakdown |
| `count(DISTINCT merchant_id)` | 46,579 | exact merchant count |

### Drift analysis

- **Runtime vs exact `count(*)`**: 32,152,304 - 32,109,098 = **+43,206 rows** (0.13% drift)
- **Issue-title threshold (102,494)**: **RESOLVED** - current drift is 58% smaller than the original baseline
- **5% tolerance gate**: **PASS** (0.13% << 5.0%)
- **Frozen-snapshot regression**: **RESOLVED** - both runtime endpoints now serve live data (32.1M products vs the stale 16.8M seen at 2026-06-05T15:46Z)

### What this heartbeat actually changed

1. The runtime endpoints are still labelled `approximate=true, source=pg_class_estimate`. The "approximate" label is not removed in this heartbeat - that work is owned by Flux on [BUY-31222](/BUY/issues/BUY-31222) (in_progress, parent = this issue).
2. The pg_class_fallback is no longer the broken path that froze the runtime at 16,816,466. It now serves live data within 0.13% of the canonical exact count.
3. `public.catalog_stats_mv` is still frozen at 30,079,559. A refresh will not change the runtime response (the runtime is reading `pg_class.reltuples`, not the MV), but it would matter for any consumer that hits the MV directly. [BUY-31223](/BUY/issues/BUY-31223) (todo) is the data-workspace rights fix for future refreshes.

### Verification queries (re-runnable)

```sql
-- exact canonical (runtime DB = maglev.proxy.rlwy.net:31310/railway)
SELECT
  now() at time zone 'utc' AS collected_at_utc,
  count(*) AS real_products,
  count(*) FILTER (WHERE is_active) AS active_products,
  count(DISTINCT merchant_id) AS catalog_backed_merchants
FROM products;

-- what the runtime is actually serving
SELECT reltuples::bigint AS pg_class_estimate
FROM pg_class WHERE relname='products';

-- autovacuum-tracked estimate (for cross-check)
SELECT n_live_tup, greatest(last_analyze, last_autoanalyze) AS last_stats_update
FROM pg_stat_user_tables WHERE relname='products';

-- public endpoint
curl https://api.buywhere.ai/v1/catalog/stats
```

### Next step - handing to Rex

Per the board directive, **Rex verifies** the comparison query and confirms delta is zero. I am reassigning this issue to Rex and moving it to `in_review`. The remaining work to retire the `approximate=true` label is tracked at [BUY-31222](/BUY/issues/BUY-31222) and is a child of this issue - once Rex signs off here, BUY-31222 (Flux) becomes the next quality step.

- [BUY-31273](/BUY/issues/BUY-31273) - done (blocker, this heartbeat)
- [BUY-31222](/BUY/issues/BUY-31222) - in_progress, Flux (exact-count path replacement, child)
- [BUY-31223](/BUY/issues/BUY-31223) - todo (catalog_stats refresh rights, child)
- [BUY-31169](/BUY/issues/BUY-31169) - blocked parent, Rex
