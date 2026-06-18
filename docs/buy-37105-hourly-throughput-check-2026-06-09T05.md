# BUY-37105 — Hourly throughput check (2026-06-09 06:03 UTC fire, 05:00–06:00 UTC window)

**Result: FAIL — 174 / 150,000 (0.1% of threshold; -149,826 below bar). Failure child will be filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Since `data/.throughput_state.json` was missing in this workspace, the prior baseline was reconstructed from the previous recorded fire in [docs/buy-36981-hourly-throughput-check-2026-06-09T04.md](docs/buy-36981-hourly-throughput-check-2026-06-09T04.md).

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-09T05:00:00Z` → `2026-06-09T06:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Baseline `n_tup_ins` | `20,366,218` at `2026-06-09T05:04:37.222127+00:00` |
| Current `n_tup_ins` sample | `20,366,394` at `2026-06-09T06:05:16.414084+00:00` |
| Delta rows | `176` |
| Delta window | `1.0108866547h` |
| Computed rows/hour | **174** |
| Threshold | `150,000` |
| Margin | **-149,826** |
| % of target | **0.1%** |
| Secondary verification | `COUNT(*)` timed out after `30s`; `MAX(created_at)` timed out after `8s` |
| `n_live_tup` current sample | `56,866,331` |

## Interpretation

The direct hour-bucket count timed out again, so the check used the primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior recorded baseline and the current sample.

That delta was only `176` rows across just over an hour, which normalizes to `174` rows/hour. Under the [BUY-29861](/BUY/issues/BUY-29861) rule, this is a clear failure, so a user-assigned failure child must be created for the `05:00–06:00Z` window.

## Dispatcher-equivalent output

```text
[throughput-dispatcher] Checking hour 2026-06-09T05:00:00+00:00 → 2026-06-09T06:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=174 target=150,000 (0.1%) source=n_tup_ins_delta
[throughput-dispatcher] FAIL — file child under BUY-29861
```

## DB proof

```sql
SELECT now() AT TIME ZONE 'utc', n_live_tup, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
WHERE relname = 'products';
-- 2026-06-09 06:05:16.414084 | 56866331 | 20366394 | 36634542 | 2011
```

```sql
SELECT COUNT(*) AS total_rows,
       COUNT(*) FILTER (
           WHERE merchant_id::text NOT IN (
               'shopnow','techdepot','fastshop','megamart','smartcart',
               'valuehub','easycart','quickbuy','primestore','globalmart'
           )
             AND url NOT LIKE '%example.com%'
       ) AS real_rows,
       MIN(created_at) AS first_row,
       MAX(created_at) AS last_row
FROM products
WHERE created_at >= '2026-06-09T05:00:00+00:00'
  AND created_at <  '2026-06-09T06:00:00+00:00';
-- timed out after 30s
```

```sql
SELECT MAX(created_at) FROM products;
-- timed out after 8s
```

## Disposition

`done` once the required failure child issue is created and this run issue is closed.
