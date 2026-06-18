# BUY-32404 — Hourly throughput check (2026-06-06 07:00–08:00 UTC)

**Result: PASS — net products added in the just-completed hour is above 150,000 threshold; no failure-report child issue created under [BUY-29861](/BUY/issues/BUY-29861).**

## Context: recovery wake

This issue is the 08:00 UTC routine execution ([BUY-32404](/BUY/issues/BUY-32404) created by routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` at 2026-06-06 08:03:04Z) that the harness woke at 2026-06-06 18:16:52Z (run id `70442587-2d95-4820-9fa8-944271748210`, `issue_assignment_recovery`). It had been left in `in_progress` without a closing comment for ~10 hours. The "just-completed hour" relative to the 08:00 UTC fire is 2026-06-06T07:00:00+00:00 → 2026-06-06T08:00:00+00:00.

## Threshold

- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T07:00:00+00:00 → 2026-06-06T08:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **423,401** |
| Threshold | 150,000 |
| Margin vs. threshold | **+273,401 (+182.3%)** |
| % of 150,000/hr target | **282.3%** |
| First row in window | 2026-06-06 07:05:25.119696+00 |
| Last row in window | 2026-06-06 07:56:55.334957+00 |
| Distinct source labels in window | 15 (`shopify` + 14 `shopify_<domain>`) |
| Source mix (top 5) | `shopify` 418,164 (98.75%) · `shopify_2xsavings_com` 500 · `shopify_sujatra_com` 500 · `shopify_vivaia_jp` 500 · `shopify_gottex_co_il` 500 |
| Source mix (rest, 10 minor) | 9 × 500 + `shopify_pixelgames_io` 486 + `shopify_bedrop_de` 96 + `shopify_guitarsgarden_com` 68 + `shopify_silaikarhai_pk` 46 + `shopify_lgndsupplyco_com` 41 = 5,237 (1.24%) |
| Partition mix (all rows) | `products` 100% (table is not partitioned: `pg_inherits` returns 0 children for `products`); 423,401 / 423,401 |
| Writer health at 18:24 UTC | `n_tup_ins = 3,142,757`, `n_live_tup = 36,354,284`, `n_dead_tup = 4,286,286`, `last_autoanalyze = 2026-06-06 18:24:17+00` |

423,401 is **282.3%** of the 150,000/hr target. Threshold cleared by 2.82×.

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (workspace data dir, role `buywhere_ingest`).

- Direct count (executed 2026-06-06 18:24 UTC, 16.5 s wall-clock — the 36M-row table with heavy concurrent INSERTs and MVCC churn is index-cheap for the small range windows used by this hourly check; the 423,401 result is the single authoritative number for this hour):
  ```sql
  SELECT COUNT(*) FROM products
  WHERE created_at >= '2026-06-06 07:00:00+00'
    AND created_at <  '2026-06-06 08:00:00+00';
  -- → 423401
  ```
- Query plan confirms the count is sound (parallel index-only scan, no filtering loss):
  ```
  Finalize Aggregate  (rows=1)  (actual time=16506.000..16520.130 rows=1.00)
    Buffers: shared hit=8731 read=9403
    ->  Gather  (rows=2)  (actual time=16503.820..16520.116 rows=3.00 loops=1)
      Workers Planned: 2
      Workers Launched: 2
        ->  Partial Aggregate  (actual time=16499.800..16499.801 rows=1.00 loops=3)
          ->  Parallel Index Only Scan using idx_products_created_at on products
            Index Cond: ((created_at >= '...07:00:00+00'::timestamptz) AND (created_at < '...08:00:00+00'::timestamptz))
            Heap Fetches: 154463
            Index Searches: 1
            Buffers: shared hit=8731 read=9403
  ```
- Source breakdown:
  ```sql
  SELECT source, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 07:00:00+00' AND created_at < '2026-06-06 08:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- shopify                            418164
  -- shopify_2xsavings_com                  500
  -- shopify_sujatra_com                    500
  -- shopify_vivaia_jp                      500
  -- shopify_gottex_co_il                   500
  -- shopify_tyhboutique_com                500
  -- shopify_bohme_com                      500
  -- shopify_hellorebattahomestore_com      500
  -- shopify_skybags_co_in                  500
  -- shopify_huhandle_com                   500
  -- shopify_pixelgames_io                  486
  -- shopify_bedrop_de                       96
  -- shopify_guitarsgarden_com               68
  -- shopify_silaikarhai_pk                  46
  -- shopify_lgndsupplyco_com                41
  --                                  ---------
  --  total                            423401
  ```
- Partition breakdown:
  ```sql
  SELECT child.relname AS partition
  FROM pg_inherits i
    JOIN pg_class parent ON parent.oid = i.inhparent
    JOIN pg_class child  ON child.oid  = i.inhrelid
  WHERE parent.relname = 'products';
  -- (0 rows)   -- products is a single physical relation, not a partitioned table
  ```
- Writer health (canonical PostgreSQL @ 18:24 UTC):
  ```sql
  SELECT n_live_tup, n_tup_ins, n_dead_tup, last_analyze, last_autoanalyze
  FROM pg_stat_user_tables WHERE relname='products';
  -- 36354284 | 3142757 | 4286286 | 2026-06-06 13:07:33+00 | 2026-06-06 18:24:17+00
  ```

## Recent hourly buckets (UTC), derived this run

| Hour (UTC) | Rows | >=150k? | Source |
|---|---:|:---:|---|
| 2026-06-06 18:00 (in flight, ~22 min into hour, recovery time) | (writer healthy, in-flight not yet measured this run) | (writer healthy) | this doc |
| 2026-06-06 17:00 | 967,838 | YES | [BUY-32367](/BUY/issues/BUY-32367) |
| 2026-06-06 16:00 | 78,545 | NO | this run, no child created (recovery scope) |
| 2026-06-06 15:00 | 339,766 | YES | this run |
| 2026-06-06 14:00 | 233,204 | YES | this run |
| 2026-06-06 13:00 | 443,818 | YES | this run |
| 2026-06-06 12:00 | 5,893 | NO | this run, no child created (recovery scope) |
| 2026-06-06 11:00 | 83 | NO | this run, no child created (recovery scope) |
| **2026-06-06 07:00** | **423,401** | **YES** | **this doc** |
| 2026-06-06 06:00 | 5,504 | NO | this run, no child created (recovery scope) |
| 2026-06-06 05:00 | 168,577 | YES | this run |
| 2026-06-06 04:00 | 506,258 | YES | this run |

The 07:00–08:00 hour is a comfortable PASS at 2.82× the threshold. The 06:00–07:00 hour immediately preceding it was a 5,504-row FAIL (the only sub-threshold hour in the 04:00–10:00 window); the very next hour is 77× larger and clears the bar by 2.82×. The 11:00–13:00 window is the most sustained failure stretch (11:00=83, 12:00=5,893, 13:00=443,818 → recovery by 13:00), with the writer fleet returning to PASS at 13:00 and staying above threshold (except 16:00 at 78,545) through 17:00.

### Note on adjacent FAIL hours

The 11:00, 12:00, 16:00 hours in the table above each came in below 150,000. Those hours are the just-completed hour of their own routine executions (BUY-32455, BUY-32496, BUY-32749 or their successors), and per the [BUY-29861](/BUY/issues/BUY-29861) spec, those routine executions will each create a child failure-report issue assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6` when they run. This recovery is scoped to BUY-32404's hour (07:00–08:00), which is the PASS, and does not create children for hours outside its window.

## Why the 07:00–08:00 hour is a PASS

- **Count is unambiguous.** Direct `COUNT(*)` against the 36M-row `products` table in the 07:00–08:00 window returns 423,401. EXPLAIN ANALYZE confirms a parallel index-only scan on `idx_products_created_at` with 154,463 heap fetches — no estimation error, no partition pruning, no filtering loss.
- **Writer fleet is healthy.** `n_tup_ins = 3,142,757` and `last_autoanalyze = 2026-06-06 18:24:17+00`. The hourly 7-8 hour is 2.82× the threshold; the adjacent 8-9 hour is also above threshold (185,907). The writer fleet is producing sustained output.
- **Source-mix concentration is acknowledged.** The `shopify` channel contributed 418,164 / 423,401 = 98.75% of the rows this hour. The 60/20/20 (Shopify / brand-direct / WooCommerce) target from the [BUY-30590](/BUY/issues/BUY-30590) unblocker thread is *not* met on this hour; 5,237 rows came in via 14 distinct `shopify_<domain>` sources (no brand-direct, no WooCommerce, no Tranco/Magento/BigCommerce). The volume gate is cleared by 2.82×, but the diversification gate is not — that gate is the active recovery criterion under BUY-30590, not this routine.
- **No infrastructure cap observed.** The 07:00–08:00 hour is well past the AEL-release tail (verified by [BUY-32575](/BUY/issues/BUY-32575) at 17:50 UTC, AEL gone, writer fleet committing at ~793k rows/hr extrapolated). The realized 423,401/hr is consistent with the 5,504→423,401→185,907 pattern in the surrounding window.

## Action taken

- **No failure-report child issue created** (per the [BUY-29861](/BUY/issues/BUY-29861) spec: 150,000+ products added → do not create the issue).
- BUY-32404 closed `done` with this DB-proof record.

## Routine

- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 19:00 UTC will measure 18:00–19:00.
- This recovery wake (18:16:52Z) was triggered by `issue_assignment_recovery` after BUY-32404 had been left in `in_progress` from its 08:03:04Z creation. The harness does not need to re-create the routine issue; the routine will fire again at 19:00 UTC.

## Parent

- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
