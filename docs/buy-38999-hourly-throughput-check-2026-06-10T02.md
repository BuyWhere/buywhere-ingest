# BUY-38999 — Hourly throughput check (2026-06-10 03:00 UTC fire, 02:00–03:00 UTC window)

**Result: FAIL — failure-report child issue [BUY-39000](/BUY/issues/BUY-39000) created under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path used: `scripts/hourly_throughput_dispatcher.py`.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-10T02:00:00Z` → `2026-06-10T03:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Dispatcher result | **0** |
| Threshold | `150,000` |
| Margin | **-150,000** |
| % of target | **0.0%** |
| Secondary verification | `COUNT(*)` timed out after `30s` under maglev contention |
| `n_tup_ins` baseline | `21,366,014` at `2026-06-09T20:03:46.727343+00:00` (prior fire) |
| `n_tup_ins` current sample | `21,366,015` at `2026-06-10T03:02:45.233871+00:00` |
| `n_live_tup` current sample | `57,765,884` |
| `pg_postmaster_start_time` | `2026-06-08 10:21:09.112373+00:00` (no restart in window) |

## Interpretation

The direct hour-bucket count timed out, so the dispatcher used its primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline (recorded by the [BUY-38723](/BUY/issues/BUY-38723) fire at 20:03Z) and the current fire at 03:02Z.

Across the 7-hour window from `2026-06-09T20:03Z` to `2026-06-10T03:02Z`, the `n_tup_ins` counter advanced by exactly `1` (`21,366,014 → 21,366,015`). The just-completed `02:00–03:00Z` window inherits that 0/hr reading under the dispatcher's primary signal.

`n_live_tup` actually decreased from `57,876,127` to `57,765,884` (-110,243 rows) — autovacuum / cleanup activity on a table that has not been receiving new writes for many hours.

No maglev restart occurred in the window (`pg_postmaster_start_time` still 2026-06-08 10:21:09Z — the [BUY-35444 third restart](/BUY/issues/BUY-35444) baseline, ~40h ago).

Under the [BUY-29861](/BUY/issues/BUY-29861) rule this is an unambiguous failure, so the dispatcher created [BUY-39000](/BUY/issues/BUY-39000) and assigned it to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Wider context (re-reading memory index)

- The BUY-33694 cron path is still broken (missing `cd` + wrong path; [BUY-33694 dispatcher cron broken](/BUY/issues/BUY-33694)). This BUY-38999 manual heartbeat is the only path producing hourly children today.
- The same `0/hr` posture has held since at least 19:00–20:00Z on 2026-06-09 — see [BUY-38723](/BUY/issues/BUY-38723) (FAIL, 0 rows). The 20:00→03:00Z stretch shows the fleet is not producing rows against the canonical catalog at all.
- The active cap is maglev write contention, named in [BUY-30590 driver issue IS the destination](/BUY/issues/BUY-30590); maglev DDL is ops-only per [charter Rule 14](feedback_maglev_ddl_ops_only.md).
- Reed's [product ownership](/BUY/issues/BUY-29861) tracks the 150k/hr June-30 target; the metric this hour is 0/150000 (0.0%).

## Dispatcher output

```text
[throughput-dispatcher] Checking hour 2026-06-10T02:00:00+00:00 → 2026-06-10T03:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=0 target=150,000 (0.0%) source=n_tup_ins_delta
[throughput-dispatcher] FAIL — filed BUY-39000 under BUY-29861
```

## State file after this fire

```json
{
  "last_n_tup_ins": 21366015,
  "last_n_tup_ins_at": "2026-06-10T03:03:44.812835+00:00",
  "last_hour_checked": "2026-06-10T02:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 0,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 57765884,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

State-snapshot pre-fire backup: `data/.throughput_state.json.snapshot-pre-buy-38999-fire-20260610T0302Z`

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the required failure child was filed for the `02:00–03:00Z` window.
