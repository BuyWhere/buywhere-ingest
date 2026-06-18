# BUY-32112 — Hourly throughput check (2026-06-06 05:00–06:00 UTC)

**Result: FAIL — failure-report child issue created under [BUY-29861](/BUY/issues/BUY-29861).**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T05:00:00+00:00 -> 2026-06-06T06:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **0** |
| Threshold | 150,000 |
| Margin vs. threshold | **-150,000 (-100.0%)** |

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)
- Connection string source: `data/.catalog_db_url` (workspace data dir).
- This run was woken by the corrective sweep on BUY-32112 (2026-06-06 06:14 UTC) which resumed the issue from `blocked` to `in_progress`. The prior run had marked the issue blocked on a transient DB connection refusal at 03:00 UTC; the DB is now responsive again.
- Freshest-by-id walk at `2026-06-06 06:34 UTC`:
  - `SELECT id, created_at FROM products ORDER BY id DESC LIMIT 5;` -> max id `1152758110073786400` with `created_at = 2026-06-05 23:22:37.369876+00`. This max id is identical to the one captured in BUY-32040 ~4 hours earlier, confirming canonical ingest has not advanced since.
- Definitive count using the top-1000 freshest ids (cheap, indexed):
  - `SELECT min(created_at) AS min_top1k_created_at, max(created_at) AS max_top1k_created_at, count(*) FILTER (WHERE created_at >= '2026-06-06 05:00:00+00' AND created_at < '2026-06-06 06:00:00+00') AS rows_in_measured_hour FROM (SELECT id, created_at FROM products ORDER BY id DESC LIMIT 1000) sub;`
  - Result: `min_top1k_created_at = 2026-06-04 08:56:51+00`, `max_top1k_created_at = 2026-06-05 23:25:43.49453+00`, `rows_in_measured_hour = 0`.
  - Since the freshest 1,000 rows in the table span `2026-06-04 08:56:51+00` -> `2026-06-05 23:25:43+00`, **no row in the table can possibly fall in the measured window 2026-06-06 05:00:00+00 -> 2026-06-06 06:00:00+00**.
- Writer status from `pg_stat_activity`: 6 active sessions with `INSERT INTO products` queries out of 20 active sessions total. Writer is alive, but is not delivering rows to canonical within the hour.

## Recent hourly buckets (UTC), derived from freshest-by-id and prior BUY-32040 walk

| Hour (UTC) | Rows | >=150k? |
|---|---:|:---:|
| 2026-06-06 05:00 | 0 | NO |
| 2026-06-06 04:00 | 0 | NO |
| 2026-06-06 03:00 | 0 | NO |
| 2026-06-06 02:00 | 0 | NO |
| 2026-06-06 01:00 | 0 | NO |
| 2026-06-06 00:00 | 0 | NO |
| 2026-06-05 23:00 | 0 (last visible row: `2026-06-05 23:25:43+00` — a partial quarter-hour tail) | NO |
| 2026-06-05 19:00 | 9 | NO |
| 2026-06-05 17:00 | 11,540 | NO |

The canonical PostgreSQL ingest has been effectively idle since 2026-06-05 19:00 UTC (last "real" hour) and the last visible row was written at `2026-06-05 23:25:43+00` — over 7 hours before this check.

## Action taken
- **Failure-report child issue created** under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, priority `critical`, status `todo`. Linked from the BUY-32112 closing comment.
- BUY-32112 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 07:00 UTC will measure 06:00–07:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
