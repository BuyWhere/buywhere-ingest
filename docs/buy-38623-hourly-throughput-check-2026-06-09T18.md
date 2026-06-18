# BUY-38623 — Hourly throughput check (2026-06-09 19:03 UTC fire, 18:00–19:00 UTC window)

**Result: FAIL — failure-report child issue [BUY-38633](/BUY/issues/BUY-38633) created under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-09T18:00:00Z` -> `2026-06-09T19:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Dispatcher result | **7,268** |
| Threshold | `150,000` |
| Margin | **-142,732** |
| % of target | **4.8%** |
| Secondary verification | `COUNT(*)` timed out after `30s` under maglev contention |
| `n_tup_ins` baseline | `21,351,180` at `2026-06-09T17:01:23.593366+00:00` |
| `n_tup_ins` current sample | `21,366,014` at `2026-06-09T19:03:51.603439+00:00` |
| `n_live_tup` current sample | `57,876,127` |

## Interpretation

The direct hour-bucket count timed out, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

That delta was `14,834` rows over `2.04h`, which annualizes to `7,268/hr`. Even with the wider-than-one-hour baseline interval, that throughput estimate is far below the `150,000/hr` threshold. Under the [BUY-29861](/BUY/issues/BUY-29861) rule this is an unambiguous failure, so the dispatcher created [BUY-38633](/BUY/issues/BUY-38633) and assigned it to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Dispatcher output

```text
[throughput-dispatcher] Checking hour 2026-06-09T18:00:00+00:00 → 2026-06-09T19:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=7,268 target=150,000 (4.8%) source=n_tup_ins_delta
[throughput-dispatcher] FAIL — filed BUY-38633 under BUY-29861
```

## State file after this fire

```json
{
  "last_n_tup_ins": 21366014,
  "last_n_tup_ins_at": "2026-06-09T19:03:51.603439+00:00",
  "last_hour_checked": "2026-06-09T18:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 7268,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 57876127,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the required failure child was filed for the `18:00–19:00Z` window.
