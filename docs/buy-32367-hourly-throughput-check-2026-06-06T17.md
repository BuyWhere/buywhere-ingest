# BUY-32367 — Hourly throughput check (2026-06-06 17:00–18:00 UTC)

**Result: PASS — net products added in the just-completed hour is above 150,000 threshold; no failure-report child issue created under [BUY-29861](/BUY/issues/BUY-29861).**

## Context: recovery wake

This issue is the 18:00 UTC routine execution ([BUY-32367](/BUY/issues/BUY-32367) created by routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` at 2026-06-06 18:00:02Z) that the harness woke at 2026-06-06 18:05:55Z (run id `1e92ae7f-3ed3-4e7d-bb58-cdfd62f557b9`, `issue_assignment_recovery`). It had been left in `in_progress` without a closing comment. The "just-completed hour" relative to the 18:00 UTC fire is 2026-06-06T17:00:00+00:00 → 2026-06-06T18:00:00+00:00.

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T17:00:00+00:00 → 2026-06-06T18:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **967,838** |
| Threshold | 150,000 |
| Margin vs. threshold | **+817,838 (+545.2%)** |
| % of 150,000/hr target | **645.2%** |
| First row in window | 2026-06-06 17:00:16.203825+00 |
| Last row in window | 2026-06-06 17:59:55.166395+00 |
| Source mix (all rows) | `shopify` 967,816 (99.998%), `costco_us` 22 (0.002%) |
| Partition mix (all rows) | `products` 100% (table is not partitioned; 967,838 / 967,838) |
| Distinct source labels in window | 2 (`shopify`, `costco_us`) |

967,838 is **645.2%** of the 150,000/hr target. Threshold cleared by a wide margin.

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (workspace data dir, role `buywhere_ingest`).

- Direct count (executed 2026-06-06 18:07 UTC, 44 s wall-clock — the 36M-row table with heavy concurrent INSERTs and MVCC churn is index-cheap for the *small* range windows but expensive for hour-wide counts; the 967,838 result is the single authoritative number for this hour):
  ```sql
  SELECT COUNT(*) FROM products
  WHERE created_at >= '2026-06-06 17:00:00+00'
    AND created_at <  '2026-06-06 18:00:00+00';
  -- → 967838
  ```
- Source breakdown:
  ```sql
  SELECT source, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 17:00:00+00' AND created_at < '2026-06-06 18:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- shopify   | 967816
  -- costco_us |     22
  ```
- Partition breakdown:
  ```sql
  SELECT tableoid::regclass AS partition, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 17:00:00+00' AND created_at < '2026-06-06 18:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- products | 967838
  ```
- In-flight 18:00–19:00 hour at 18:07 UTC (~7 min into the hour): **177,764 rows**. On pace to clear 150k comfortably.
- Writer health (canonical PostgreSQL @ 18:07 UTC):
  - `pg_stat_user_tables` for `products`: `n_tup_ins = 3,020,386`, `n_live_tup = 36,270,718`, `n_dead_tup = 3,911,687`. `n_tup_ins` is up from 2,636,467 at 17:50 UTC (per the BUY-32575 AEL-release verification doc) — a delta of +383,919 in 17 minutes, consistent with sustained ingest.
  - `pg_stat_activity` shows 2 active sessions, both are this heartbeat's own psql probes. No `INSERT INTO products` writer session in flight at 18:07 UTC (writer fleet is between batches); the in-flight 18:00 hour count (177,764 rows in 7 min) confirms new batches are landing on schedule.
  - Per `pg_inherits`: `products` has zero partition children — the table is a single physical relation. The earlier `products_us`/`products_sg`/`products_default` partition family referenced in the 16:00 UTC BUY-32224 doc is not present in this snapshot of the schema; the canonical writer writes directly to `products`.

## Recent hourly buckets (UTC), derived this run

| Hour (UTC) | Rows | >=150k? | Source |
|---|---:|:---:|---|
| 2026-06-06 18:00 (in flight, ~7 min) | 177,764 | (on pace) | direct count |
| 2026-06-06 17:00 | **967,838** | **YES** | this doc |
| 2026-06-06 16:00 |   4,927  | NO | [BUY-32224](/BUY/issues/BUY-32224) |
| 2026-06-06 15:00 | 339,766  | YES | [BUY-32749](/BUY/issues/BUY-32749) |
| 2026-06-06 14:00 | 233,204  | YES | [BUY-32749](/BUY/issues/BUY-32749) |

The 17:00–18:00 hour is the strongest single hour in the recovery window. The 16:00–17:00 hour (4,927 rows, single source `chewy_us`) was a 1-σ low that triggered a FAIL child under [BUY-29861](/BUY/issues/BUY-29861); the very next hour is ~196× larger and clears the bar by 6.5×. The two consecutive PASS hours (14:00 and 15:00) followed by a slow 16:00–17:00 hour and then this 17:00–18:00 surge are consistent with the writer fleet completing its deferred queue and the AEL-release tail ([BUY-32575](/BUY/issues/BUY-32575)) flowing through.

## Why the 17:00–18:00 hour is a PASS

- **Writer fleet is healthy.** `n_tup_ins` advanced 383,919 rows in the 17 minutes between the 17:50 UTC BUY-32575 snapshot and 18:07 UTC; the in-flight 18:00 hour is already at 177,764 rows / ~7 min.
- **967,838 is unambiguous.** Direct `COUNT(*)` against the 36M-row `products` table in the 17:00–18:00 window returns a single number, 967,838 — ~6.45× the threshold.
- **Source-mix concentration is acknowledged.** The `shopify` channel contributed 967,816 / 967,838 = 99.998% of the rows this hour. The 60/20/20 (Shopify / brand-direct / WooCommerce) target from the [BUY-30590](/BUY/issues/BUY-30590) unblocker thread is *not* met on this hour; only 22 rows came in via `costco_us` and zero via any brand-direct or WooCommerce lane. The volume gate is cleared, but the diversification gate is not — that gate is the active recovery criterion under BUY-30590, not this routine.
- **No infrastructure cap observed.** The 17:00–18:00 hour is well past the 17:00 AEL-release verification ([BUY-32575](/BUY/issues/BUY-32575) at 17:50 UTC: AEL on `public.products` gone, writer fleet committing at ~793k rows/hr extrapolated). The 967,838/hr realized in the second half-hour validates that extrapolation.

## Action taken

- **No failure-report child issue created** (per the [BUY-29861](/BUY/issues/BUY-29861) spec: 150,000+ products added → do not create the issue).
- BUY-32367 closed `done` with this DB-proof record.

## Routine

- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 19:00 UTC will measure 18:00–19:00.
- This recovery wake (18:05:55Z) was triggered by `issue_assignment_recovery` after BUY-32367 had been left in `in_progress` from its 18:00:02Z creation. The harness does not need to re-create the routine issue; the routine will fire again at 19:00 UTC.

## Parent

- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
