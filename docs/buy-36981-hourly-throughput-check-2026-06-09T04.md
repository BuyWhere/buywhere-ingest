# BUY-36981 — Hourly throughput check (2026-06-09 05:04 UTC fire, 04:00–05:00 UTC window)

**Result: FAIL — 0 / 150,000 (0.0% of threshold; -150,000 below bar). Failure child [BUY-36992](/BUY/issues/BUY-36992) was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-09T04:00:00Z` → `2026-06-09T05:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Baseline `n_tup_ins` | `20,366,218` at `2026-06-09T04:04:29.765756+00:00` |
| Current `n_tup_ins` sample | `20,366,218` at `2026-06-09T05:04:37.222127+00:00` |
| Delta rows | `0` |
| Delta window | `1.0019323225h` |
| Computed rows/hour | **0** |
| Threshold | `150,000` |
| Margin | **-150,000** |
| % of target | **0.0%** |
| Secondary verification | `COUNT(*)` timed out after `30s`; `MAX(created_at)` timed out after `8s` |
| `n_live_tup` current sample | `56,866,155` |
| Failure child | [BUY-36992](/BUY/issues/BUY-36992) |

## Interpretation

The direct hour-bucket count timed out again, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

That delta was exactly zero across the elapsed hour. Under the [BUY-29861](/BUY/issues/BUY-29861) rule, this is a clear failure, so the dispatcher filed [BUY-36992](/BUY/issues/BUY-36992) and assigned it to the user owner.

## Dispatcher output

```text
[throughput-dispatcher] Checking hour 2026-06-09T04:00:00+00:00 → 2026-06-09T05:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=0 target=150,000 (0.0%) source=n_tup_ins_delta
[throughput-dispatcher] FAIL — filed BUY-36992 under BUY-29861
```

## State file after this fire

```json
{
  "last_n_tup_ins": 20366218,
  "last_n_tup_ins_at": "2026-06-09T05:04:37.222127+00:00",
  "last_hour_checked": "2026-06-09T04:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 0,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 56866155,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway",
  "last_fire_buy": "BUY-36859",
  "last_fire_note": "FAIL ~19,819 rows (13.2% of 150K). Dispatcher timed out on COUNT/MAX and filed failure child BUY-36872 from the n_tup_ins delta.",
  "last_fire_doc": "docs/buy-36859-hourly-throughput-check-2026-06-09T03.md"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the required failure child [BUY-36992](/BUY/issues/BUY-36992) was created for the `04:00–05:00Z` window.
