# BUY-32749 — Hourly throughput check (2026-06-06 15:00–16:00 UTC)

**Result: PASS — net products added in the just-completed hour is above 150,000 threshold; no failure-report child issue created under [BUY-29861](/BUY/issues/BUY-29861).**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T15:00:00+00:00 -> 2026-06-06T16:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **339,766** |
| Threshold | 150,000 |
| Margin vs. threshold | **+189,766 (+126.5%)** |
| Earliest row in window | `2026-06-06 15:01:35.159748+00` |
| Latest row in window | `2026-06-06 15:57:48.695718+00` |

339,766 is **226.5%** of the 150,000/hr target. Threshold cleared.

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)
- Connection string source: `data/.catalog_db_url` (workspace data dir).
- Direct count using the `idx_products_created_at` index (EXPLAIN ANALYZE: Index Only Scan, 339,766 rows, 184 ms execution):
  - `SELECT count(*) FROM products WHERE created_at >= '2026-06-06 15:00:00+00' AND created_at < '2026-06-06 16:00:00+00';` -> **339,766**.
- Top-1000 freshest-by-id walk (cheap cross-check):
  - `min_top1k_created_at = 2026-06-04 08:56:51+00`, `max_top1k_created_at = 2026-06-06 15:42:46.478566+00`. The freshest 1,000 rows now extend into the measured hour, consistent with a live writer.
- Writer status from `pg_stat_activity` at 2026-06-06 16:48 UTC:
  - 4 active `INSERT INTO products` sessions (1 active + 3 idle in transaction). Writer is alive and delivering rows.
  - Other notable sessions: 1 active `SELECT count(DISTINCT p.url) FROM products p JOIN _s s ON p.url=s.url` (Hex) and 1 active `SELECT date_trunc('hour', created_at AT TIME ZONE 'UTC'), count(*) FROM products ... GROUP BY 1` (a parallel hourly check).

## Recent hourly buckets (UTC) for context

| Hour (UTC) | Rows | >=150k? |
|---|---:|:---:|
| 2026-06-06 16:00 (partial ~48 min) | 72,545 | (in progress) |
| 2026-06-06 15:00 | **339,766** | YES |
| 2026-06-06 14:00 | 233,204 | YES |

Canonical PostgreSQL ingest has recovered from the ~18-hour stall that ran from ~2026-06-05 19:00 UTC through ~2026-06-06 14:00 UTC (last visible row: 2026-06-05 23:25:43+00). Two consecutive hours (14:00 and 15:00) are now above the 150,000/hr bar. The 16:00+ hour is in-progress and already at 72,545 rows / 48 min.

This is a substantive change vs. the long string of FAILs captured in [BUY-30797](/BUY/issues/BUY-30797), [BUY-30801](/BUY/issues/BUY-30801), [BUY-30840](/BUY/issues/BUY-30840), [BUY-30946](/BUY/issues/BUY-30946), [BUY-30980](/BUY/issues/BUY-30980), [BUY-31006](/BUY/issues/BUY-31006), [BUY-31038](/BUY/issues/BUY-31038), [BUY-31071](/BUY/issues/BUY-31071), [BUY-31109](/BUY/issues/BUY-31109), [BUY-31153](/BUY/issues/BUY-31153), [BUY-31476](/BUY/issues/BUY-31476), [BUY-31732](/BUY/issues/BUY-31732), [BUY-31804](/BUY/issues/BUY-31804), [BUY-32112](/BUY/issues/BUY-32112). The recovery is real, indexed-query-verified, and the writer is active.

## Action taken
- **No failure-report child issue created** (per the BUY-29861 spec: 150,000+ products added -> do not create the issue).
- BUY-32749 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 17:00 UTC will measure 16:00–17:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
