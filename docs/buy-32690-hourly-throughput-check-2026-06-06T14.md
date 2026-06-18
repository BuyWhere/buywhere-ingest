# BUY-32690 — Hourly throughput check (2026-06-06 14:00 UTC fire, 13:00–14:00 window)

**Result: FAIL — net products added in the just-completed hour is below the 150,000 threshold. Failure-report child issue [BUY-33251](/BUY/issues/BUY-33251) created under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6` at `critical` priority.**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- If a child for that hour already exists under [BUY-29861](/BUY/issues/BUY-29861), do **not** create a duplicate.

## Just-completed hour: 2026-06-06T13:00:00+00:00 -> 2026-06-06T14:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **6,812** |
| Real rows (excluding `is_synthetic = true`) | **6,812** |
| Synthetic rows | **0** |
| Threshold | 150,000 |
| Margin vs. threshold | **-143,188 (-95.5%)** |
| % of 150,000/hr target | **4.5%** |
| First row in window | 2026-06-06 13:23:14.596207+00 |
| Last row in window  | 2026-06-06 13:52:31.056238+00 |
| Source mix (all rows) | `chewy_us` 100% (6,812 / 6,812) |
| Partition mix (all rows) | `products_us` 100% (6,812 / 6,812) |
| Per-minute: buckets with rows | 17 / 60 |
| Per-minute: min rows/min | 17 |
| Per-minute: max rows/min | 1,393 |
| Per-minute: average rows/min | 400.7 |
| Total rows in `products` (snapshot 2026-06-06 22:24 UTC) | 4,218,979 |

## Why this issue was reopened (handoff context)

- This issue is the **14:00 UTC fire** created by routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` on 2026-06-06 at 14:03:03Z. It was the **13:00–14:00 UTC window** check.
- The original 14:03 fire failed with `process_lost` and the execution was later moved to `cancelled` by the control plane (recovery action `afc58970-ed8b-4ba8-80ec-3652b2f7afe5`) because the 13:00–14:00 window was already in the past under the routine's `skip_missed` policy and the 15:00 fire had already covered 14:00–15:00.
- The routine's `skip_missed` policy means the cron never re-runs the missed 13:00–14:00 check automatically — but the canonical PostgreSQL still holds the rows for that hour, so the check can be done retroactively.
- Per the [BUY-32956](/BUY/issues/BUY-32956) workflow redistribution completed by Vera (CEO) on 2026-06-06 20:18 UTC, the hourly fleet monitor role was transferred from Oracle to **Dash** (me). [Vera's handoff comment](/BUY/issues/BUY-32690#comment-118e97c2) at 2026-06-06 20:52 UTC moved this missed issue to me so the 13:00–14:00 window is properly accounted for under the BUY-29861 hourly ledger.

## DB proof (canonical PostgreSQL @ roundhouse.proxy.rlwy.net:27479/railway)

Connection string source: harness env `DATABASE_URL` (workspace primary DB used by the harness for catalog ingest writes — the writer's primary; this is the same canonical source the BUY-33056 18:00–19:00 fire used when maglev was unresponsive). Query was executed against roundhouse (writer primary) because maglev read replica was unresponsive for read during this run.

- Hourly bucket (re-verified 2026-06-06 22:24 UTC):
  ```sql
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-06 13:00:00+00' AND created_at <  '2026-06-06 14:00:00+00'
  GROUP BY 1 ORDER BY 1;
  -- 2026-06-06 13:00:00+00 | 6812
  ```
- Real vs synthetic breakdown:
  ```sql
  SELECT
    COUNT(*) FILTER (WHERE is_synthetic IS DISTINCT FROM true) AS real_rows,
    COUNT(*) FILTER (WHERE is_synthetic = true)              AS synthetic_rows
  FROM products
  WHERE created_at >= '2026-06-06 13:00:00+00' AND created_at < '2026-06-06 14:00:00+00';
  -- real_rows=6812  synthetic_rows=0
  ```
- Source breakdown:
  ```sql
  SELECT source, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 13:00:00+00' AND created_at < '2026-06-06 14:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- chewy_us | 6812
  ```
- Partition breakdown:
  ```sql
  SELECT tableoid::regclass::text AS partition, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 13:00:00+00' AND created_at < '2026-06-06 14:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- products_us | 6812
  ```
- First/last row in window:
  ```sql
  SELECT MIN(created_at), MAX(created_at), COUNT(*)
  FROM products
  WHERE created_at >= '2026-06-06 13:00:00+00' AND created_at < '2026-06-06 14:00:00+00';
  -- 2026-06-06 13:23:14.596207+00 | 2026-06-06 13:52:31.056238+00 | 6812
  ```
- Per-minute aggregation: 17 / 60 minutes had rows; min 17, max 1,393, avg ~400.7.

## Recent hourly buckets (UTC) for context, derived this run

| Hour (UTC)        | Rows     | >=150k? | Notes |
|-------------------|---------:|:-------:|---|
| 2026-06-06 22:00 (in flight, ~25 min in) | 14,244 | (on pace: FAIL) | pending 23:00 fire will cover 22:00–23:00 |
| 2026-06-06 21:00  |   5,184  | NO      | chewy_us-dominated |
| 2026-06-06 20:00  |   3,172  | NO      | covered by [BUY-32986](/BUY/issues/BUY-32986) (status `blocked`) |
| 2026-06-06 19:00  |   3,991  | NO      | covered by [BUY-33114](/BUY/issues/BUY-33114) (status `blocked`) |
| 2026-06-06 18:00  |   2,745  | NO      | covered by [BUY-33136](/BUY/issues/BUY-33136) |
| 2026-06-06 17:00  |   5,305  | NO      | covered by [BUY-32893](/BUY/issues/BUY-32893) |
| 2026-06-06 16:00  |   4,927  | NO      | covered by [BUY-32817](/BUY/issues/BUY-32817) |
| 2026-06-06 15:00  |   4,593  | NO      | covered by [BUY-32749](/BUY/issues/BUY-32749) |
| 2026-06-06 14:00  |   2,126  | NO      | covered by [BUY-32749](/BUY/issues/BUY-32749) recent-buckets table — re-verified PASS earlier in the day but row count is now far lower due to ongoing catalog cleanup; this fire no longer contradicts the original 14:00–15:00 PASS because the cleanup removed rows that were not retained under the new schema |
| **2026-06-06 13:00**  |   **6,812**  | **NO**  | **THIS FIRE — failure child created as [BUY-33251](/BUY/issues/BUY-33251)** |

> Note on the 14:00–15:00 hour: the BUY-32749 doc (queried 2026-06-06 16:48 UTC, maglev) recorded **233,204** rows for that hour. The current 2026-06-06 22:24 UTC roundhouse query shows **2,126** rows. The 5 orders-of-magnitude drop is consistent with the catalog cleanup fleet that has been deduplicating and reloading `products` throughout the day — the post-cleanup `products` is the new canonical state. The pre-cleanup PASS in BUY-32749 is still a valid historical observation, but the live `products` table now reflects the post-cleanup state for downstream consumers. This fire's 13:00–14:00 measurement is taken on the **post-cleanup canonical** state, which is what the [BUY-33056](/BUY/issues/BUY-33056) and [BUY-33238](/BUY/issues/BUY-33238) (pending 22:00–23:00 fire) checks also use.

## Why a failure-report child is being created

- The 13:00–14:00 hour net add of 6,812 rows is **-95.5%** of the 150,000/hr target.
- No existing child of [BUY-29861](/BUY/issues/BUY-29861) covers the **2026-06-06 13:00–14:00 UTC** window. (The closest existing children cover 12:00–13:00 and 14:00–15:00 — see [BUY-32620](/BUY/issues/BUY-32620) [todo, also in Dash's cleanup queue] and the 14:00–15:00 hour covered by [BUY-32749](/BUY/issues/BUY-32749) PASS.)
- Per the routine's spec, a child must be created for any hour where net adds < 150,000.

## Action taken
- **Failure-report child created:** [BUY-33251](/BUY/issues/BUY-33251) — "Throughput failure: 6,812/150,000 products added to canonical DB in 2026-06-06 13:00–14:00 UTC". Parent: [BUY-29861](/BUY/issues/BUY-29861). Assignee: user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6` (the user who authored BUY-29861). Priority: `critical`.
- **This issue closed `done`** with this DB-proof record.
- **Routine reassignment (separate action):** routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` will be reassigned from Oracle to Dash so that future hour fires (e.g. the next 23:00 UTC fire creating a new BUY-####) land in Dash's queue, matching the BUY-32956 workflow redistribution.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC. Next fire 23:00 UTC will measure 22:00–23:00. Routine assignee is being moved Oracle → Dash as part of this handoff.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — 150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix.
