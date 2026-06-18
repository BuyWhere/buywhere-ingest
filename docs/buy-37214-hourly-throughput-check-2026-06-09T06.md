# BUY-37214 — Hourly throughput check (2026-06-09 07:04 UTC fire, 06:00–07:00 UTC window)

**Result: FAIL — 206 / 150,000 (0.1% of threshold; -149,794 below bar). Failure child [BUY-37223](/BUY/issues/BUY-37223) was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-09T06:00:00Z` → `2026-06-09T07:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Baseline `n_tup_ins` | `20,366,394` at `2026-06-09T06:05:16.414084+00:00` |
| Current `n_tup_ins` sample | `20,366,597` at `2026-06-09T07:04:26.106104+00:00` |
| Delta rows | `203` |
| Delta window | `0.9860255611h` |
| Computed rows/hour | **206** |
| Threshold | `150,000` |
| Margin | **-149,794** |
| % of target | **0.1%** |
| Secondary verification | `COUNT(*)` timed out after `30s`; failure child notes `MAX(created_at)` also timed out, so staleness was inferred from the `n_tup_ins` delta |
| `n_live_tup` current sample | `56,845,589` |
| Failure child | [BUY-37223](/BUY/issues/BUY-37223) |

## Interpretation

The direct hour-bucket count timed out under maglev contention again, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

That delta was only `203` rows across just under an hour, which annualizes to `206/hr` and lands far below the `150,000/hr` threshold. Under the [BUY-29861](/BUY/issues/BUY-29861) rule, this is a clear failure, so the dispatcher filed [BUY-37223](/BUY/issues/BUY-37223) and assigned it to the user owner.

## Dispatcher output

```text
[throughput-dispatcher] Checking hour 2026-06-09T06:00:00+00:00 → 2026-06-09T07:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=206 target=150,000 (0.1%) source=n_tup_ins_delta
[throughput-dispatcher] FAIL — filed BUY-37223 under BUY-29861
```

## State file after this fire

```json
{
  "last_n_tup_ins": 20366597,
  "last_n_tup_ins_at": "2026-06-09T07:04:26.106104+00:00",
  "last_hour_checked": "2026-06-09T06:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 206,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 56845589,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the required failure child [BUY-37223](/BUY/issues/BUY-37223) was created for the `06:00–07:00Z` window.
