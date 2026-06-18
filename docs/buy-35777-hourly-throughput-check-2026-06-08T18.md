# BUY-35777 — Hourly throughput check (2026-06-08 19:03 UTC fire, 18:00–19:00 UTC window)

**Result: PASS — ~4,095,954 / 150,000 (2730.6% of threshold; +3,945,954 above bar). No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-08T18:00:00Z` → `2026-06-08T19:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Dispatcher result | **~4,095,954** |
| Threshold | `150,000` |
| Margin | **+3,945,954** |
| % of target | **2730.6%** |
| Secondary verification | `COUNT(*)` timed out after `30s` under maglev contention |
| `n_tup_ins` baseline | `15,924,186` at `2026-06-08T18:43:04.218124+00:00` |
| `n_tup_ins` current sample | `17,318,663` at `2026-06-08T19:03:29.846365+00:00` |
| `n_live_tup` current sample | `55,252,801` |

## Interpretation

The direct hour-bucket count timed out again, so the dispatcher fell back to its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

Important caveat: the prior baseline was written by the delayed recovery run for [BUY-35730](/BUY/issues/BUY-35730) at `18:43:04Z`, not at the top of the hour. That means this `4,095,954/hr` figure is an annualized rate over the `18:43:04Z` → `19:03:29Z` sampling window, not a full direct count of every row written between `18:00` and `19:00`.

That caveat does not change the disposition here: even on the dispatcher's fallback path, the measured rate is far above the `150,000/hr` threshold, so the rule in [BUY-29861](/BUY/issues/BUY-29861) says **do not create a failure issue**.

## Dispatcher output

```text
[throughput-dispatcher] Checking hour 2026-06-08T18:00:00+00:00 → 2026-06-08T19:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=4,095,954 target=150,000 (2730.6%) source=n_tup_ins_delta
[throughput-dispatcher] PASS — 4,095,954 >= 150,000. No issue filed.
```

## State file after this fire

```json
{
  "last_n_tup_ins": 17318663,
  "last_n_tup_ins_at": "2026-06-08T19:03:29.846365+00:00",
  "last_hour_checked": "2026-06-08T18:00:00+00:00",
  "last_check_result": "PASS",
  "last_check_real_rows": 4095954,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 55252801,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and no child failure report is required for the `18:00–19:00Z` window.
