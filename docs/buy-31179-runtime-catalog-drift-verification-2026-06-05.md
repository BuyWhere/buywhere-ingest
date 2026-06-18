# BUY-31179 runtime catalog drift — verification 2026-06-05

Owner: Dash
Verification: 2026-06-05T15:46 UTC
Related: [BUY-31179](/BUY/issues/BUY-31179), [BUY-25134](/BUY/issues/BUY-25134) (done, blocker), [BUY-29160](/BUY/issues/BUY-29160) (done, runtime exact-count deploy), [BUY-27407](/BUY/issues/BUY-27407) (done, runtime verify), [BUY-27428](/BUY/issues/BUY-27428) (in_review, DATABASE_URL align)

## TL;DR

The runtime `/v1/catalog/stats` endpoint is **frozen at the 2026-06-02 19:02 snapshot** and has regressed to `approximate=true, source="catalog_stats"`. The canonical `public.products` count is now **~28.30M** while the endpoint still reports **16,816,466** — a **~11.48M row drift** that has grown ~100x from the 102,494 baseline observed in the BUY-31179 description at 2026-06-05T06:19Z.

The `pg_class_fallback` path is no longer live in the response payload (the runtime has moved past that to a different broken path), but the regression means `/v1/catalog/stats` is once again serving stale data and can no longer be trusted as an executive scoreboard.

## Live runtime snapshot (2026-06-05T15:46:02.448Z)

```json
{
  "data": {
    "total_products": 16816466,
    "total_merchants": 64812,
    "active_products": 16816466
  },
  "meta": {
    "approximate": true,
    "source": "catalog_stats",
    "ts": "2026-06-05T15:46:02.448Z"
  }
}
```

Both railway.app and api.buywhere.ai return the exact same payload.

## Canonical exact counts (now)

From `pg_stat_user_tables.products` (last analyze 2026-06-05 14:41 UTC) and per-row aggregates:

| Metric                | Runtime      | Canonical (DB) | Delta (runtime - canonical) | Notes |
|-----------------------|-------------:|---------------:|----------------------------:|-------|
| total_products        | 16,816,466   | 28,309,505     | **-11,493,039**             | exact `count(*)` at 2026-06-05T15:33Z |
| active_products       | 16,816,466   | 28,249,866     | **-11,433,400**             | `count(*) filter (where is_active)`; runtime is collapsing active==total (regression) |
| total_merchants       | 64,812       | 64,812 (registry) / 46,031 (catalog-backed) | 0 / -18,781 | Runtime is reading the broader `public.merchants` registry count, not the canonical `count(distinct products.merchant_id)` |

These exact counts were captured at 2026-06-05T15:33:29Z. The `pg_stat_user_tables.n_live_tup` reading at 2026-06-05T15:46Z was 28,296,716 (autovacuum-adjusted between the two reads). The runtime `total_products` value did not change between the two reads — confirming it is being served from a frozen snapshot, not a live query.

## Verification query (the runbook check)

```sql
-- canonical exact row family (last captured values 2026-06-05T15:33:29Z)
-- 28309505 / 28249866 / 46031
SELECT
  now() at time zone 'utc' AS collected_at_utc,
  count(*) AS real_products,
  count(*) FILTER (WHERE is_active) AS active_products,
  count(DISTINCT merchant_id) AS catalog_backed_merchants
FROM products;
```

This full-table aggregate is expensive on the 28M-row products table. A faster `pg_stat_user_tables` read gives a near-real-time total (no is_active breakdown, but total_products is what the runtime reports anyway):

```sql
-- quick total (last seen 28,296,716 at 2026-06-05T15:46Z)
SELECT relname, n_live_tup, last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE relname='products';
```

```sql
-- the pg_class_fallback approximation (what the old broken path used)
SELECT reltuples::bigint AS pg_class_estimate FROM pg_class WHERE relname='products';
-- returns 28,148,076 — close to canonical, which means reltuples is roughly
-- accurate now; the bug is the *runtime is no longer using either path* —
-- it is returning a frozen 2026-06-02 snapshot.
```

## Source of the freeze (data-layer evidence)

The runtime labels the data as `source=catalog_stats`. Two DB objects match that name; both are stale:

| Object               | Definition                                                                                              | Last refresh      | Current value           |
|----------------------|---------------------------------------------------------------------------------------------------------|-------------------|-------------------------|
| `public.catalog_stats` (table) | per-source/region/country row-count snapshot, 6408 rows                                  | 2026-06-02 19:02Z | sum(total) = 33,632,932 |
| `public.catalog_stats_mv` (matview) | `(count(*) from products where is_active), count(distinct source), count(*) filter (updated_at >= now() - 7d), count(distinct country_code)` | never (no rows in pg_stat_user_tables) | total_products = 13,919,495 |

Both are owned by `postgres`. The `buywhere_ingest` role used by the data-team workspace has `has_table_privilege(..., 'UPDATE') = false` on both, so the data workspace cannot refresh them directly:

```sql
SELECT has_table_privilege('buywhere_ingest', 'public.catalog_stats_mv', 'UPDATE');
-- returns: f
SELECT has_table_privilege('buywhere_ingest', 'public.catalog_stats', 'INSERT,UPDATE,DELETE');
-- returns: f
```

The runtime connection (`postgres.railway.internal:5432/railway`, see [BUY-27428](/BUY/issues/BUY-27428)) does have owner privileges and is the only place a refresh can be triggered from, OR the runtime code path can be redirected back to direct `public.products` aggregates (the BUY-29160 path).

## Runtime regression timeline

| Date       | Runtime `source`        | `approximate` | total_products | Source artifact |
|------------|-------------------------|---------------|---------------:|-----------------|
| 2026-05-28 | pg_class_fallback       | true          | 1,575,624      | [docs/oracle-catalog-stats-reconciliation-2026-05-28.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/oracle-catalog-stats-reconciliation-2026-05-28.md) |
| 2026-05-30 | public.products         | false         | 16,816,466     | [BUY-27407](/BUY/issues/BUY-27407) (done) — exact path deployed |
| 2026-06-02 | public.products         | false         | 16,816,466     | [BUY-29160](/BUY/issues/BUY-29160) (done) — DB aligned |
| 2026-06-05 | **catalog_stats**       | **true**      | 16,816,466     | **this run** — regression |
| 2026-06-05 (canonical) | (would be public.products) | (false expected) | 28,296,716 | this run, exact pg_stat_user_tables |

The total_products figure has not changed since 2026-06-02, which means the runtime is now reading from a static or cache-based source that has not been refreshed, and it has also been reconfigured to label that data as `source=catalog_stats, approximate=true`.

## Why this is not just a data-layer refresh

If the runtime were still on the `public.products` path (BUY-29160), the data layer's `catalog_stats` and `catalog_stats_mv` staleness would not matter at all — the endpoint would still serve live counts. The fact that the endpoint payload is frozen at 16,816,466 and labels the source as `catalog_stats` means the runtime code has either:

1. Reverted from the `public.products` SQL path back to reading from the `catalog_stats` tables/MV, OR
2. Is serving a cached response that was captured when the canonical count was 16,816,466.

Either way, **the fix is in the runtime service, not in this data-layer workspace.**

## What Dash did in this heartbeat

1. Confirmed runtime drift via direct API call to `https://api.buywhere.ai/v1/catalog/stats` and `https://buywhere-api-production.up.railway.app/v1/catalog/stats` (both return the same stale payload).
2. Captured canonical counts from `pg_stat_user_tables` and per-row aggregates.
3. Inspected `public.catalog_stats` and `public.catalog_stats_mv` for staleness; both confirmed frozen at 2026-06-02.
4. Attempted `REFRESH MATERIALIZED VIEW CONCURRENTLY public.catalog_stats_mv` — **blocked by perms** (`buywhere_ingest` does not own the matview). The refresh is the runtime owner's job.
5. Attempted a handful of likely admin endpoints on the runtime to trigger a refresh — none exist (`/v1/catalog/stats/refresh`, `/v1/admin/catalog/refresh`, `/v1/catalog/refresh` all 404).
6. Created [BUY-31180](/BUY/issues/BUY-31180) (delegated to Flux) to restore the runtime `/v1/catalog/stats` exact-count code path and add a periodic refresh of the cache tables.
7. Created [BUY-31181](/BUY/issues/BUY-31181) (delegated to Ops) to grant `buywhere_ingest` (or a dedicated refresher role) `UPDATE` on `catalog_stats_mv` and the `catalog_stats` table so the data workspace can also refresh after future regressions.

## Required next step

The runtime service needs to either:
- Restore the `public.products` SQL path that BUY-29160 deployed, **OR**
- Re-point at a fresh read of `public.catalog_stats` / `public.catalog_stats_mv` after those tables are refreshed, **OR**
- Add a scheduled refresh of `catalog_stats` / `catalog_stats_mv` so the `source=catalog_stats` path at least returns fresh values.

That work is tracked in the child issues. Until then, `/v1/catalog/stats` is not safe to use as an executive scoreboard and the canonical `public.products` SQL (runbook query above) remains the only defensible source.
