# BUY-29861 hourly throughput — 2026-06-05 13:00 UTC (driver: BUY-31109)

## Just-completed hour

| Hour (UTC) | Rows | ≥150k? |
|---|---:|:---:|
| 2026-06-05 13:00 | **617,890** | **YES** |

No failure report created (threshold met).

## DB proof (maglev `products.created_at`, previous 14 full UTC hours)

| Hour (UTC) | Rows | ≥150k? |
|---|---:|:---:|
| 2026-06-05 13:00 | 617,890 | YES |
| 2026-06-05 12:00 | 188,128 | YES |
| 2026-06-05 11:00 | 344,468 | YES |
| 2026-06-05 10:00 | 1,016,100 | YES |
| 2026-06-05 09:00 | 1,321,262 | YES |
| 2026-06-05 08:00 | 324,081 | YES |
| 2026-06-05 07:00 | 216,205 | YES |
| 2026-06-05 06:00 | 261,059 | YES |
| 2026-06-05 05:00 | 149,999 | NO (1 row short) |
| 2026-06-05 04:00 | 108,948 | NO |
| 2026-06-05 03:00 | 155,638 | YES |
| 2026-06-05 02:00 | 98,001 | NO |
| 2026-06-05 01:00 | 312,321 | YES |
| 2026-06-05 00:00 | 33,523 | NO |

**Consecutive hours ≥150,000 (counted backward from previous full hour): 8 / 14**
(06:00 → 13:00 UTC clear; broken at 05:00 by 149,999 — one row short.)

## Query

```sql
SELECT to_char(date_trunc('hour', created_at), 'YYYY-MM-DD HH24:MI') AS hour, count(*) AS rows
FROM products
WHERE created_at >= now() - interval '14 hours'
  AND created_at < date_trunc('hour', now())
GROUP BY 1
ORDER BY 1 DESC;
```

## Disposition

Just-completed hour 13:00 UTC = 617,890 rows. Above threshold. No BUY-#### failure report created per BUY-31109 spec.
Streak extended to 8/14. BUY-29861 close criterion (sustained 150k/hour) still progressing.
