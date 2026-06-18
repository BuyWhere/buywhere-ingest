# BUY-32429 — Hourly throughput check (2026-06-06 09:00 UTC fire, 08:00–09:00 window)

**Result: FAIL — failure-report child issue [BUY-33284](/BUY/issues/BUY-33284) created under [BUY-29861](/BUY/issues/BUY-29861).**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-06T08:00:00+00:00 → 2026-06-06T09:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **0** |
| Threshold | 150,000 |
| Margin vs. threshold | **-150,000 (-100.0%)** |
| % of 150,000/hr target | **0.0%** |
| First row in window | NULL (no rows) |
| Last row in window | NULL (no rows) |
| Source mix (all rows) | none (0 / 0) |
| Partition mix (all rows) | none (0 / 0) |
| Per-minute: buckets with rows | 0 / 60 |
| Per-minute: peak rows/min | 0 |
| Per-minute: average rows/min | 0.0 |
| Total rows in `products` (snapshot 2026-06-06 23:23 UTC) | 4,224,640 |

## DB proof (canonical PostgreSQL @ roundhouse.proxy.rlwy.net:27479/railway)

Connection string source: harness env `DATABASE_URL` (writer's primary). Workspace historical reports reference `data/.catalog_db_url` (maglev read replica) — that host is currently blocked behind catalog-cleanup fleet activity, so the writer's primary is used (matches the convention in the BUY-32893 / BUY-33056 / BUY-33273 docs).

- Direct count (executed 2026-06-06 23:23 UTC):
  ```sql
  SELECT COUNT(*) FROM products
  WHERE created_at >= '2026-06-06 08:00:00+00'
    AND created_at <  '2026-06-06 09:00:00+00';
  -- → 0
  ```
- Source breakdown:
  ```sql
  SELECT source, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 08:00:00+00' AND created_at <  '2026-06-06 09:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- (0 rows)
  ```
- Partition breakdown:
  ```sql
  SELECT tableoid::regclass AS partition, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 08:00:00+00' AND created_at <  '2026-06-06 09:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- (0 rows) -- empty across all partitions (products_sg, products_us, products_default)
  ```
- First/last row in window:
  ```sql
  SELECT MIN(created_at) AS first_row, MAX(created_at) AS last_row, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-06 08:00:00+00' AND created_at <  '2026-06-06 09:00:00+00';
  -- NULL | NULL | 0
  ```
- Per-minute: 0 / 60 minutes had rows; min 0, max 0, avg 0.

## Why this hour was a FAIL (post-cleanup canonical)

- **No rows landed in canonical in this hour.** Across the `products_sg`, `products_us`, and `products_default` partitions, the `created_at` range `[2026-06-06 08:00:00+00, 2026-06-06 09:00:00+00)` is empty. The hour produced zero inserts.
- **No fallback bucket either.** A scan of all partitions confirms there is no row sitting in the wrong partition for that hour. This is a real zero, not a routing artifact.
- **Pre-cleanup view of the adjacent 07:00–08:00 hour was PASS** (423,401 rows per the [BUY-32404](/BUY/issues/BUY-32404) doc) — those rows have since been retired by the catalog-cleanup fleet, so the post-cleanup `products` shows 0 for that hour as well. The 08:00–09:00 window is consistent with that cleanup pattern, not a fresh lane outage per se.
- **Adjacent-hour context.** The 10:00–11:00 hour is filed as [BUY-33061](/BUY/issues/BUY-33061) (0 / 150,000); the 11:00–12:00 hour as [BUY-33273](/BUY/issues/BUY-33273) (0 / 150,000); the 09:00–10:00 hour is a known gap (the 10:00 fire [BUY-32455](/BUY/issues/BUY-32455) was stranded and closed as no-op by Vera during process_lost recovery, no child was filed).

## Action taken
- **Failure-report child issue [BUY-33284](/BUY/issues/BUY-33284)** created under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, priority `critical`, status `todo`. Description carries the full DB proof, hour-over-hour context, and remediation pointers.
- This issue [BUY-32429](/BUY/issues/BUY-32429) closed `done` with this DB-proof record.

## Why this check is being filed from [BUY-32429](/BUY/issues/BUY-32429)

The 09:00 UTC fire ([BUY-32429](/BUY/issues/BUY-32429)) was created at 2026-06-06 09:03:04Z, hit `process_lost` during its first attempt (Vera's recovery comment at 19:25:17Z), and was re-dispatched from Oracle → Dash per [BUY-32956](/BUY/issues/BUY-32956) at 2026-06-06 20:52:42Z. Dash executed the 08:00–09:00 check on [BUY-32429](/BUY/issues/BUY-32429) at 23:23 UTC, and this doc is the DB-proof record. Delay: routine fire → report filed ≈ 14h 20m.

## Routine

- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC. Currently still assigned to Oracle (`3ec8f6dd`); agents can only manage their own routines, so the formal reassignment is on Oracle in [BUY-33252](/BUY/issues/BUY-33252) (still `todo`).
- Next fires:
  - [BUY-33238](/BUY/issues/BUY-33238) (22:00 fire for 21:00–22:00 hour) — `todo` on Oracle, stranded, will need the same stale-wake sweep.
  - [BUY-33269](/BUY/issues/BUY-33269) (23:00 fire for 22:00–23:00 hour) — `todo` on Oracle, the 22:00–23:00 hour already has its child [BUY-33279](/BUY/issues/BUY-33279) (18,033 / 150,000) filed from a separate heartbeat; this fire should detect the existing child and close as a no-op.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
- New failure-report child for the 08:00–09:00 hour: [BUY-33284](/BUY/issues/BUY-33284).
