# BUY-31732 — Hourly throughput check (2026-06-05 21:00–22:00 UTC)

**Result: PASS — no failure-report issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T21:00:00+00:00 → 2026-06-05T22:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **269,834** |
| Threshold | 150,000 |
| Margin over threshold | +119,834 (+79.9%) |

## DB proof (maglev `products.created_at`, previous 14 full UTC hours)

| Hour (UTC) | Rows | ≥150k? |
|---|---:|:---:|
| 2026-06-05 21:00 | 269,834 | YES |
| 2026-06-05 20:00 | 97,076 | NO |
| 2026-06-05 19:00 | 442,472 | YES |
| 2026-06-05 18:00 | 376,879 | YES |
| 2026-06-05 17:00 | 793,933 | YES |
| 2026-06-05 16:00 | 540,716 | YES |
| 2026-06-05 15:00 | 189,426 | YES |
| 2026-06-05 14:00 | 525,058 | YES |
| 2026-06-05 13:00 | 617,890 | YES |
| 2026-06-05 12:00 | 188,128 | YES |
| 2026-06-05 11:00 | 344,468 | YES |
| 2026-06-05 10:00 | 1,016,100 | YES |
| 2026-06-05 09:00 | 1,321,262 | YES |
| 2026-06-05 08:00 | 324,081 | YES |

**Consecutive hours ≥150,000 (counted backward from previous full hour): 1 / 14**
(21:00 UTC clear; broken at 20:00 by 97,076.)

## Query

```sql
SELECT to_char(date_trunc('hour', created_at), 'YYYY-MM-DD HH24:MI') AS hour, count(*) AS rows
FROM products
WHERE created_at >= '2026-06-05 08:00:00+00'
  AND created_at < '2026-06-05 23:00:00+00'
GROUP BY 1
ORDER BY 1 DESC;
```

## Disposition

Just-completed hour 21:00 UTC = 269,834 rows. Above 150,000 threshold. No BUY-#### failure report created per [BUY-29861](/BUY/issues/BUY-29861) spec.
Streak reset to 1/14 — the 20:00 UTC hour (97,076 rows) broke a 9-hour clear streak. 21:00 UTC recovered above threshold.
BUY-29861 close criterion (sustained 150k/hour) still progressing; single-hour misses continue to interrupt the streak.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. It produced this run issue [BUY-31732](/BUY/issues/BUY-31732) at 2026-06-05T22:00:41Z. Next fire 23:00 UTC will measure 22:00–23:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
