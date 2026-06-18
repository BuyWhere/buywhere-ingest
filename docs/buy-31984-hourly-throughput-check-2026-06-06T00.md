# BUY-31984 — Hourly throughput check (2026-06-06 00:00–01:00 UTC)

**Result: FAIL — failure-report child issue [BUY-32035](/BUY/issues/BUY-32035) created.**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T00:00:00+00:00 -> 2026-06-06T01:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **0** |
| Threshold | 150,000 |
| Margin vs. threshold | **-150,000 (-100.0%)** |

## DB proof (canonical PostgreSQL)
- Query: `SELECT count(*) FROM products WHERE created_at >= '2026-06-06 00:00:00+00' AND created_at < '2026-06-06 01:00:00+00';`
- Result: `0`
- Freshness watermark: `SELECT max(created_at) FROM products;` -> `2026-06-05 19:06:17+00`

## Recent hourly buckets (UTC)

| Hour (UTC) | Rows | >=150k? |
|---|---:|:---:|
| 2026-06-06 01:00 | 0 | NO |
| 2026-06-06 00:00 | 0 | NO |
| 2026-06-05 23:00 | 0 | NO |
| 2026-06-05 22:00 | 0 | NO |
| 2026-06-05 21:00 | 0 | NO |
| 2026-06-05 20:00 | 0 | NO |
| 2026-06-05 19:00 | 9 | NO |
| 2026-06-05 18:00 | 0 | NO |
| 2026-06-05 17:00 | 11,540 | NO |
| 2026-06-05 16:00 | 86 | NO |
| 2026-06-05 15:00 | 550 | NO |
| 2026-06-05 14:00 | 0 | NO |
| 2026-06-05 13:00 | 1,173 | NO |
| 2026-06-05 12:00 | 45 | NO |
| 2026-06-05 11:00 | 127 | NO |

The current canonical DB state indicates ingestion had already fallen effectively idle before the measured hour and remained idle through the just-completed hour.

## Action taken
- **Failure-report child issue [BUY-32035](/BUY/issues/BUY-32035) created** under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, priority `critical`, status `todo`.
- BUY-31984 will be closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 02:00 UTC will measure 01:00–02:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
