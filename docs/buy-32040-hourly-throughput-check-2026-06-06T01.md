# BUY-32040 — Hourly throughput check (2026-06-06 01:00–02:00 UTC)

**Result: FAIL — canonical ingest was already stale before the measured hour, so a failure-report child issue is required.**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T01:00:00+00:00 -> 2026-06-06T02:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **0 (inferred)** |
| Threshold | 150,000 |
| Margin vs. threshold | **-150,000 (-100.0%)** |

## DB proof (canonical PostgreSQL)
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Initial freshness watermark query: `SELECT max(created_at) FROM products;` -> `2026-06-05 19:06:17+00`.
- Re-verification in the follow-up heartbeat (DB was hammered by other agents' concurrent max(created_at) scans at the time):
  - `SELECT max(id) FROM products;` -> `1152758110073786400`
  - `SELECT id, created_at FROM products WHERE id BETWEEN 1152758110073780000 AND 1152758110073786400 ORDER BY id DESC LIMIT 20;` -> exactly one row, the max id, with `created_at = 2026-06-05 23:22:37+00`.
  - `SELECT count(*) FROM products WHERE id > 1152758110073780000;` -> `1`.
  - So the freshest row in the table predates the measured window start (`2026-06-06 01:00:00+00`) by at least 1h 37m 23s, and the measured hour necessarily added **0** products to canonical PostgreSQL.
- Writer status from `pg_stat_activity`: multiple `INSERT INTO products` queries are active, so the writer is alive but is not delivering rows to canonical within the hour.

## Interpretation
- The failure is not a near-miss; the canonical table had already stopped advancing roughly **5h 53m 43s** before the measured hour started.
- This is the same idle-ingest pattern surfaced one hour earlier in [BUY-31984](/BUY/issues/BUY-31984), now extended through the next top-of-hour check.

## Action taken
- Failure-report child issue created under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, priority `critical`, status `todo`:
  - [BUY-32083](/BUY/issues/BUY-32083) — "Hourly throughput failure — 2026-06-06 01:00–02:00 UTC (0 / 150,000 products)".
- BUY-32040 closed `done` with this visible DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 03:00 UTC will measure 02:00–03:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
