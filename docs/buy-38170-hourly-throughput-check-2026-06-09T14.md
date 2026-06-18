# BUY-38170 — Hourly throughput check (2026-06-09 15:01 UTC fire, 14:00–15:00 UTC window)

**Result: FAIL — 2,851 / 150,000 (1.9% of threshold; -147,149 below bar). Failure child [BUY-38179](/BUY/issues/BUY-38179) was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-09T14:00:00Z` → `2026-06-09T15:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Baseline `n_tup_ins` | `21,348,318` at `2026-06-09T14:01:38.119144+00:00` |
| Current `n_tup_ins` sample | `21,351,180` at `2026-06-09T15:01:52.470793+00:00` |
| Delta rows | `2,862` |
| Delta window | `1.0039865691666667h` |
| Computed rows/hour | **2,851** |
| Threshold | `150,000` |
| Margin | **-147,149** |
| % of target | **1.9%** |
| Secondary verification | `COUNT(*)` timed out after `30s`; `MAX(created_at)` timed out after `8s` |
| `n_live_tup` current sample | `58,094,577` |
| Failure child | [BUY-38179](/BUY/issues/BUY-38179) |

## Interpretation

The direct hour-bucket count timed out under maglev contention, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

That delta was only `2,862` rows across roughly one hour, which normalizes to `2,851` rows/hour. Under the [BUY-29861](/BUY/issues/BUY-29861) rule, this is a clear failure, so the dispatcher filed [BUY-38179](/BUY/issues/BUY-38179) and assigned it to the user owner.

## Dispatcher output

```text
[throughput-dispatcher] Checking hour 2026-06-09T14:00:00+00:00 → 2026-06-09T15:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=2,851 target=150,000 (1.9%) source=n_tup_ins_delta
[throughput-dispatcher] FAIL — filed BUY-38179 under BUY-29861
```

## State file after this fire

```json
{
  "last_n_tup_ins": 21351180,
  "last_n_tup_ins_at": "2026-06-09T15:01:52.470793+00:00",
  "last_hour_checked": "2026-06-09T14:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 2851,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 58094577,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the required failure child [BUY-38179](/BUY/issues/BUY-38179) was created for the `14:00–15:00Z` window.
