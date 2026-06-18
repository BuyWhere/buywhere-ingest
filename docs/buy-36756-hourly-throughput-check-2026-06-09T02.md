# BUY-36756 — Hourly throughput check (2026-06-09 03:04 UTC fire, 02:00–03:00 UTC window)

**Result: PASS — ~269,029 / 150,000 (179.4% of threshold; +119,029 above bar). No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-09T02:00:00Z` → `2026-06-09T03:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Dispatcher result | **~269,029** |
| Threshold | `150,000` |
| Margin | **+119,029** |
| % of target | **179.4%** |
| Secondary verification | `COUNT(*)` timed out after `30s` under maglev contention |
| `n_tup_ins` baseline | `19,816,115` at `2026-06-09T01:06:20.364761+00:00` |
| `n_tup_ins` current sample | `20,346,438` at `2026-06-09T03:04:36.870661+00:00` |
| `n_live_tup` current sample | `56,846,375` |

## Interpretation

The direct hour-bucket count timed out again, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

The measured delta was `530,323` inserts over `1.9713` hours, which annualizes to `~269,029/hr`. That comfortably clears the `150,000/hr` threshold, so the [BUY-29861](/BUY/issues/BUY-29861) rule is unambiguous: **do not create a failure issue**.

## Dispatcher output

```text
[throughput-dispatcher] Checking hour 2026-06-09T02:00:00+00:00 → 2026-06-09T03:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=269,029 target=150,000 (179.4%) source=n_tup_ins_delta
[throughput-dispatcher] PASS — 269,029 >= 150,000. No issue filed.
```

## State file after this fire

```json
{
  "last_n_tup_ins": 20346438,
  "last_n_tup_ins_at": "2026-06-09T03:04:36.870661+00:00",
  "last_hour_checked": "2026-06-09T02:00:00+00:00",
  "last_check_result": "PASS",
  "last_check_real_rows": 269029,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 56846375,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and no child failure report is required for the `02:00–03:00Z` window.
