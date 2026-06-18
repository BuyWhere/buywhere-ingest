# BUY-38409 — Hourly throughput check (2026-06-09 17:01 UTC fire, 16:00–17:00 UTC window)

**Result: FAIL — failure-report child issue [BUY-38418](/BUY/issues/BUY-38418) created under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-09T16:00:00Z` → `2026-06-09T17:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Dispatcher result | **0** |
| Threshold | `150,000` |
| Margin | **-150,000** |
| % of target | **0.0%** |
| Secondary verification | `COUNT(*)` timed out after `30s` under maglev contention |
| `n_tup_ins` baseline | `21,351,180` at `2026-06-09T16:01:42.951813+00:00` |
| `n_tup_ins` current sample | `21,351,180` at `2026-06-09T17:01:23.593366+00:00` |
| `n_live_tup` current sample | `58,094,577` |

## Interpretation

The direct hour-bucket count timed out, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

That delta was exactly zero over the sample window between hourly fires, so the measured throughput for the `16:00–17:00Z` hour is `0/hr`. Under the [BUY-29861](/BUY/issues/BUY-29861) rule this is an unambiguous failure, so the dispatcher created [BUY-38418](/BUY/issues/BUY-38418) and assigned it to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Dispatcher output

```text
[throughput-dispatcher] Checking hour 2026-06-09T16:00:00+00:00 → 2026-06-09T17:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=0 target=150,000 (0.0%) source=n_tup_ins_delta
[throughput-dispatcher] FAIL — filed BUY-38418 under BUY-29861
```

## State file after this fire

```json
{
  "last_n_tup_ins": 21351180,
  "last_n_tup_ins_at": "2026-06-09T17:01:23.593366+00:00",
  "last_hour_checked": "2026-06-09T16:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 0,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 58094577,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the required failure child was filed for the `16:00–17:00Z` window.
