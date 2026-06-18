# BUY-39162 — Hourly throughput check (2026-06-10 09:01 UTC fire, 08:00–09:00 UTC window)

**Result: FAIL — failure-report child issue filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical
  PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned
  failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Check path: manual heartbeat (BUY-33694 dispatcher cron is still broken — see
  `feedback_buy33694_dispatcher_cron_broken.md`).

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-10T08:00:00Z` → `2026-06-10T09:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Net products added | **30,226** (over 58m10s sample window) |
| Per-hour rate | **~31,189 / hr** |
| Threshold | `150,000` |
| Margin | **-118,811** |
| % of target | **20.8%** |
| Secondary verification | `COUNT(*)` for the hour timed out at 30s and 120s under maglev contention |
| `n_tup_ins` baseline (prior fire BUY-39118 @ 08:03:22Z) | `22,754,718` |
| `n_tup_ins` current sample (this fire @ 09:01:32Z) | `22,784,944` |
| `n_live_tup` current sample | `59,008,827` |
| `pg_postmaster_start_time` | `2026-06-08 10:21:09.112373+00:00` (no restart in window) |
| `reltuples` proxy | `58,726,136` (last ANALYZE 2026-06-10 06:38:45Z) |

## DB samples (pg_stat_user_tables.products)

| time (UTC)              | n_tup_ins     | n_live_tup     | n_tup_upd     | source            |
|-------------------------|---------------|----------------|---------------|-------------------|
| 2026-06-10T08:03:22Z \* |  22,754,718   |  58,985,649    |  48,486,156   | prior fire state  |
| 2026-06-10T09:01:32Z    |  22,784,944   |  59,008,827    |  48,493,876   | this fire sample  |
| 2026-06-10T09:09:00Z    |  22,868,971   |  59,092,851    |  48,692,342   | post-fire sample  |
| **delta 08:03:22→09:01:32 (58m10s)** | **+30,226** | +23,178 | +7,720 | **08:00 hour** |
| delta 09:01:32→09:09:00 (7m28s)      | +84,027      | +84,024  | +198,466 | 09:00 hour (post) |

\* = last dispatcher reading (`data/.throughput_state.json`, sampled 2026-06-10T08:03:22Z)

## Interpretation

The 08:00-09:00 UTC window received only **~30,226 rows** of net product inserts
across the 58-minute measurement span (08:03:22Z → 09:01:32Z). This is **20.8% of
the 150,000 / hr target**, a clear FAIL under the [BUY-29861](/BUY/issues/BUY-29861)
rule.

`pg_postmaster_start_time` is 2026-06-08 10:21:09Z (the [BUY-35444 third
restart](/BUY/issues/BUY-35444) baseline, ~46h ago) — no maglev restart occurred
in the just-completed hour, so the n_tup_ins delta is a valid primary signal
(no post-restart baseline reset applies per the "post-restart n_tup_ins baseline
= 0" memory).

The hour-bucket `COUNT(*)` query timed out at both 30s and 120s under maglev
write contention (the [BUY-30590 driver
issue](/BUY/issues/BUY-30590)-named cap), so the n_tup_ins delta is the only
viable signal — and it is unambiguous.

### Post-09:00 acceleration (informational)

In the 9 minutes after the hour boundary (09:01:32Z → 09:09:00Z), 84,027 rows
were inserted (~675,000 / hr extrapolated). This is a 21x rate jump vs the
08:00-09:00 hour's 31,200 / hr. The fleet appears to have just kicked into
high gear as the new hour opened. This is **not** credited to the 08:00 hour;
the 08:00-09:00 verdict stands as FAIL.

## Comparison to prior hours (canonical maglev)

| Hour (UTC)       | Result | Rows/hr    | Source                  |
|------------------|--------|------------|-------------------------|
| 2026-06-10 07:00–08:00 | PASS  | 166,169    | [BUY-39118](/BUY/issues/BUY-39118) |
| **2026-06-10 08:00–09:00** | **FAIL**  | **~31,189**  | **BUY-39162 (this fire)** |
| 2026-06-10 06:00–07:00 | PASS  | 519,464    | [BUY-39056](/BUY/issues/BUY-39056) |
| 2026-06-10 02:00–03:00 | FAIL  | 0          | [BUY-38999](/BUY/issues/BUY-38999) |

The 08:00 hour falls between two PASSes. The pattern is consistent with
fleet-level rate instability — sustained 3-4x target (per
[BUY-35444](/BUY/issues/BUY-35444) post-restart throughput) is not holding
this hour.

## Wider context (re-reading memory index)

- [BUY-30590 driver issue IS the destination](/BUY/issues/BUY-30590) — maglev
  write contention is the named cap. The fleet appears to push through bursts
  rather than steady-state 150K+/hr.
- maglev DDL is ops-only per [charter Rule 14](feedback_maglev_ddl_ops_only.md).
- The BUY-33694 cron is still broken (missing `cd` + wrong path; see
  [BUY-33694 dispatcher cron broken](/BUY/issues/BUY-33694)). This manual
  heartbeat is the only path producing hourly children today.
- `products_created_at_idx` remains INVALID ([BUY-32878](/BUY/issues/BUY-32878))
  but does not block the n_tup_ins accounting path.

## State file after this fire

Will be updated to reflect the 08:00-09:00 hour result so the next fire
(09:00-10:00Z window) has a clean baseline. Pre-fire snapshot:
`data/.throughput_state.json.snapshot-pre-buy-39162-fire-20260610T0901Z`.

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, a failure
child was filed under [BUY-29861](/BUY/issues/BUY-29861) and assigned to user
`MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, and state was advanced for the next fire.
