# BUY-36008 — Hourly throughput check (2026-06-08 21:03 UTC fire, 20:00–21:00 UTC window)

**Result: FAIL — ~109,262 / 150,000 (72.8% of threshold; -40,738 below bar). Failure child [BUY-36018](/BUY/issues/BUY-36018) was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-08T20:00:00Z` → `2026-06-08T21:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Dispatcher result | **~109,262** |
| Threshold | `150,000` |
| Margin | **-40,738** |
| % of target | **72.8%** |
| Secondary verification | `COUNT(*)` timed out after `30s` under maglev contention |
| `n_tup_ins` baseline | `18,848,078` at `2026-06-08T20:02:49.061255+00:00` |
| `n_tup_ins` current sample | `18,957,792` at `2026-06-08T21:03:03.949739+00:00` |
| `n_live_tup` current sample | `55,584,344` |
| Failure child | [BUY-36018](/BUY/issues/BUY-36018) |

## Interpretation

The direct hour-bucket count timed out again, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

That delta was `109,714` rows across roughly one hour of elapsed time, which annualizes to `~109,262/hr`. That is below the `150,000/hr` threshold in [BUY-29861](/BUY/issues/BUY-29861), so the dispatcher correctly filed [BUY-36018](/BUY/issues/BUY-36018) for user follow-up.

## State file after this fire

```json
{
  "last_n_tup_ins": 18957792,
  "last_n_tup_ins_at": "2026-06-08T21:03:03.949739+00:00",
  "last_hour_checked": "2026-06-08T20:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 109262,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 55584344,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the failure child [BUY-36018](/BUY/issues/BUY-36018) was filed for the `20:00–21:00Z` miss.
