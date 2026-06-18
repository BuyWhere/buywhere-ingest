# BUY-33056 — Hourly throughput check (2026-06-06 19:00 UTC fire, 18:00–19:00 window)

**Result: PASS-OF-CHECK — failure-report child for the 18:00–19:00 hour already filed under [BUY-29861](/BUY/issues/BUY-29861) as [BUY-33136](/BUY/issues/BUY-33136). This issue is closed without creating a duplicate child.**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- If a child for that hour already exists under [BUY-29861](/BUY/issues/BUY-29861), do **not** create a duplicate.

## Just-completed hour for this fire: 2026-06-06T18:00:00+00:00 -> 2026-06-06T19:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **2,745** |
| Threshold | 150,000 |
| Margin vs. threshold | **-147,255 (-98.2%)** |
| % of 150,000/hr target | **1.8%** |
| First row in window | 2026-06-06 18:00:21.873660+00 |
| Last row in window | 2026-06-06 18:46:40.612465+00 |
| Source mix (all rows) | `chewy_us` 100% (2,745 / 2,745) |
| Partition mix (all rows) | `products_us` 100% (2,745 / 2,745) |
| Per-minute: buckets with rows | 42 / 60 |
| Per-minute: peak rows/min | 325 |
| Per-minute: average rows/min | 65.4 |
| Total rows in `products` (snapshot 2026-06-06 ~20:42 UTC) | 4,196,663 |

## DB proof (canonical PostgreSQL @ roundhouse.proxy.rlwy.net:27479/railway)

Connection string source: harness env `DATABASE_URL` (workspace primary DB used by the harness for catalog ingest writes). The maglev read replica used by some earlier reports (`data/.catalog_db_url`) was unresponsive on read for this run due to writer contention — roundhouse is the writer's primary, so it is the canonical source.

- Hourly bucket (re-verified 2026-06-06 20:42 UTC):
  ```sql
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-06 18:00:00+00' AND created_at <  '2026-06-06 19:00:00+00'
  GROUP BY 1 ORDER BY 1;
  -- 2026-06-06 18:00:00+00 | 2745
  ```
- Source breakdown:
  ```sql
  SELECT source, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 18:00:00+00' AND created_at < '2026-06-06 19:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- chewy_us | 2745
  ```
- Partition breakdown:
  ```sql
  SELECT tableoid::regclass AS partition, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-06 18:00:00+00' AND created_at < '2026-06-06 19:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- products_us | 2745
  ```
- First/last row in window:
  ```sql
  SELECT MIN(created_at) AS first_row, MAX(created_at) AS last_row, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-06 18:00:00+00' AND created_at < '2026-06-06 19:00:00+00';
  -- 2026-06-06 18:00:21.873660+00 | 2026-06-06 18:46:40.612465+00 | 2745
  ```
- Per-minute aggregation: 42 / 60 minutes had rows; min 4, max 325, avg ~65.4.

## Recent hourly buckets (UTC) for context, derived this run

| Hour (UTC)        | Rows     | >=150k? | Notes |
|-------------------|---------:|:-------:|---|
| 2026-06-06 19:00 (in flight, ~42 min in) | 3,991 | (on pace: FAIL) | chewy_us only — covered by [BUY-33114](/BUY/issues/BUY-33114) (20:00 fire, still `todo`) |
| **2026-06-06 18:00** |   **2,745**  | **NO** | **covered by existing [BUY-33136](/BUY/issues/BUY-33136); not duplicated** |
| 2026-06-06 17:00  |   5,305  | NO | chewy_us 4,825 + sitemap 480 |
| 2026-06-06 16:00  |   4,927  | NO | chewy_us only — [BUY-32933](/BUY/issues/BUY-32933) |

## Why this issue is being closed as done without creating a child

- The 19:00 UTC fire (this issue, BUY-33056, created 2026-06-06 19:23:08Z) targets the **18:00–19:00 UTC** window — the hour that was just-completed at the time of the cron fire.
- The harness woke this issue at 2026-06-06 20:38:20Z (a stale `issue_assignment_recovery` wake, ~75 minutes after the cron fire). The same window had already been covered by the 18:00 fire's stale wake run (the BUY-32893 doc authored at 20:12 UTC), which created the child failure report **[BUY-33136](/BUY/issues/BUY-33136)** at 2026-06-06 20:14:09Z with the matching `2,745/150,000` numbers, the same source/partition mix (`chewy_us` / `products_us`), and the same first/last row timestamps. That child is already parented to [BUY-29861](/BUY/issues/BUY-29861) and assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6` at `critical` priority.
- Re-verifying the 18:00–19:00 hour against the canonical PostgreSQL writer primary at 20:42 UTC reproduces the same `2,745` row count and the same single-channel `chewy_us` 100% mix. The existing child is correct.
- Per the routine's own convention (and the BUY-32893 doc's "that worker should not duplicate the report" note), a child that already covers the target hour is a valid superseder — this fire should **not** create a second child for the same window.

## Action taken
- **No new child issue created.** The 18:00–19:00 hour is already filed as [BUY-33136](/BUY/issues/BUY-33136).
- This issue [BUY-33056](/BUY/issues/BUY-33056) closed `done` with this DB-proof record.

## Next fires
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 20:00 UTC created issue [BUY-33114](/BUY/issues/BUY-33114) (status `todo`); that fire will measure 19:00–20:00 UTC and should run on its own cron at 21:00 UTC, not on this stale wake.
- Two prior unprocessed routine issues remain in the parent's child list as stale: [BUY-32986](/BUY/issues/BUY-32986) (18:00 fire for the 17:00–18:00 hour) and [BUY-32817](/BUY/issues/BUY-32817) (16:00 fire for the 15:00–16:00 hour). They are out of scope for this heartbeat but will be picked up by the next 21:00 fire's stale-wake sweep.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
- Existing failure-report child for the 18:00–19:00 hour: [BUY-33136](/BUY/issues/BUY-33136).
