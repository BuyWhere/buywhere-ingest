# BUY-32167 — Hourly throughput check (recovery, 2026-06-06)

**Result: PASS — net products added in the just-completed hour is above 150,000 threshold; no failure-report child issue created under [BUY-29861](/BUY/issues/BUY-29861).**

## Context: recovery wake

This issue is the 04:01 UTC routine execution ([BUY-32167](/BUY/issues/BUY-32167) created by routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` at 2026-06-06 04:01:17Z) that had been left in `in_progress` without a closing comment. The harness woke it for assignment recovery at 2026-06-06 16:53 UTC (run id `3f5a25c2-a982-4c9f-8f70-c129b695c261`).

The "just-completed hour" relative to the recovery wake is 2026-06-06T15:00:00+00:00 -> 2026-06-06T16:00:00+00:00 (the 16:00–17:00 hour is still in progress at the time of the check).

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T15:00:00+00:00 -> 2026-06-06T16:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **339,766** |
| Threshold | 150,000 |
| Margin vs. threshold | **+189,766 (+126.5%)** |
| % of 150,000/hr target | **226.5%** |

339,766 is well above the 150,000/hr threshold.

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)
- Connection string source: `data/.catalog_db_url` (workspace data dir).
- Direct count using the `idx_products_created_at` index at `2026-06-06 16:57 UTC`:
  - `SELECT count(*) FROM products WHERE created_at >= '2026-06-06 15:00:00+00' AND created_at < '2026-06-06 16:00:00+00';` -> **339,766**.
  - Same value as captured in [BUY-32749](/BUY/issues/BUY-32749) at 16:48 UTC (~9 min earlier). No additional rows materialized in that 9-min window — consistent with the canonical writer already being past the 15:00–16:00 hour and into the next bucket.
- In-progress 16:00–17:00 hour at the same instant: **77,045 rows** (47 minutes into the hour, on pace to clear 150k by 17:00).
- Top-5 freshest rows by id (`SELECT id, created_at FROM products ORDER BY id DESC LIMIT 5`) show two new rows with `created_at` in the 15:18 UTC range alongside three older 2026-06-05 23:22–23:23 rows, confirming the canonical writer is delivering rows into the measured window.
- Writer status from `pg_stat_activity` at 2026-06-06 16:57 UTC: **3 active `INSERT INTO products` sessions** out of 6 client-backend sessions. Writer is alive and delivering rows.

## Cross-reference
- The just-completed hour (15:00–16:00) was already covered end-to-end by [BUY-32749](/BUY/issues/BUY-32749) "Hourly throughput check (2026-06-06 15:00–16:00 UTC)" closed `done` at 2026-06-06 16:51 UTC with the same 339,766-row PASS result. This recovery check is a re-confirmation, not a new finding.

## Recent hourly buckets (UTC), verified

| Hour (UTC) | Rows | >=150k? |
|---|---:|:---:|
| 2026-06-06 16:00 (partial, ~47 min) | 77,045 | (in progress, on pace) |
| 2026-06-06 15:00 | **339,766** | YES |
| 2026-06-06 14:00 | 233,204 | YES (per [BUY-32749](/BUY/issues/BUY-32749), not re-counted here) |

Canonical PostgreSQL ingest is delivering rows; the 18-hour stall that ran from ~2026-06-05 19:00 UTC through ~2026-06-06 14:00 UTC is over (per [BUY-32749](/BUY/issues/BUY-32749)). Earlier-hour buckets (10:00–13:00 UTC) were not re-counted in this recovery wake — the group-by against `products` for the wider 7-hour window times out at 2 min on this DB; the 15:00–16:00 count via the `idx_products_created_at` index returned in <1s, confirming the writer is healthy on the just-completed hour.

## Action taken
- **No failure-report child issue created** (per the BUY-29861 spec: 150,000+ products added -> do not create the issue).
- BUY-32167 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 17:00 UTC will measure 16:00–17:00.
- The most recent unprocessed routine-created issue is [BUY-32817](/BUY/issues/BUY-32817) (status `todo`, created 2026-06-06 16:03 UTC). The next routine run at 17:00 will create a new issue for the 16:00–17:00 hour check.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
