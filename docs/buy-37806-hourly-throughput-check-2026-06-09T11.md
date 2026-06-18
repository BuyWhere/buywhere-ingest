# BUY-37806 — Hourly throughput check (2026-06-09 12:01 UTC fire, 11:00–12:00 UTC window)

**Result: FAIL — 0 / 150,000 (0.0% of threshold; -150,000 below bar). Failure child [BUY-37818](/BUY/issues/BUY-37818) was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `python3 scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-09T11:00:00+00:00` → `2026-06-09T12:00:00+00:00` |
| Signal source | `n_tup_ins_delta` |
| Dispatcher result | **0** |
| Threshold | `150,000` |
| Margin | **-150,000** |
| % of target | **0.0%** |
| Secondary verification | `COUNT(*)` timed out after `30s` under maglev contention |
| Dispatcher note | `n_tup_ins delta 0 over 0.97h = 0/hr` |
| `n_tup_ins` current sample | `21,348,318` at `2026-06-09T12:01:25.341455+00:00` |
| `n_live_tup` current sample | `57,825,717` |
| Failure child | [BUY-37818](/BUY/issues/BUY-37818) |

## Interpretation

The direct hour-bucket count timed out again, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

That delta was zero across roughly `0.97h` of elapsed time, so the throughput estimate for the just-completed hour was `0/hr`. That is below the `150,000/hr` threshold in [BUY-29861](/BUY/issues/BUY-29861), so the dispatcher correctly filed [BUY-37818](/BUY/issues/BUY-37818) for user follow-up.

## State file after this fire

```json
{
  "last_n_tup_ins": 21348318,
  "last_n_tup_ins_at": "2026-06-09T12:01:25.341455+00:00",
  "last_hour_checked": "2026-06-09T11:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 0,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 57825717,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the failure child [BUY-37818](/BUY/issues/BUY-37818) was filed for the `11:00–12:00Z` miss.
