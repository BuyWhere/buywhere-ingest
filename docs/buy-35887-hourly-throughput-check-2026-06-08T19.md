# BUY-35887 — Hourly throughput check (2026-06-08 20:02 UTC fire, 19:00–20:00 UTC window)

**Result: PASS — ~1,546,941 / 150,000 (1031.3% of threshold; +1,396,941 above bar). No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-08T19:00:00Z` → `2026-06-08T20:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Dispatcher result | **~1,546,941** |
| Threshold | `150,000` |
| Margin | **+1,396,941** |
| % of target | **1031.3%** |
| Secondary verification | `COUNT(*)` timed out after `30s` under maglev contention |
| `n_tup_ins` baseline | `17,318,663` at `2026-06-08T19:03:29.846365+00:00` |
| `n_tup_ins` current sample | `18,848,078` at `2026-06-08T20:02:49.061255+00:00` |
| `n_live_tup` current sample | `55,474,632` |

## Interpretation

The direct hour-bucket count timed out again, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

The baseline for this fire came from the prior routine report [BUY-35777](/BUY/issues/BUY-35777) at `2026-06-08T19:03:29Z`, so this `1,546,941/hr` figure is the dispatcher's annualized rate over the actual sample window between fires. Even with that caveat, the measured rate is still more than `10x` the `150,000/hr` threshold, so the [BUY-29861](/BUY/issues/BUY-29861) rule is unambiguous: **do not create a failure issue**.

## Dispatcher output

```text
[throughput-dispatcher] Checking hour 2026-06-08T19:00:00+00:00 → 2026-06-08T20:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=1,546,941 target=150,000 (1031.3%) source=n_tup_ins_delta
[throughput-dispatcher] PASS — 1,546,941 >= 150,000. No issue filed.
```

## State file after this fire

```json
{
  "last_n_tup_ins": 18848078,
  "last_n_tup_ins_at": "2026-06-08T20:02:49.061255+00:00",
  "last_hour_checked": "2026-06-08T19:00:00+00:00",
  "last_check_result": "PASS",
  "last_check_real_rows": 1546941,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 55474632,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and no child failure report is required for the `19:00–20:00Z` window.
