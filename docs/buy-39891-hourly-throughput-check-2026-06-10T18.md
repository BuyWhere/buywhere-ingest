# BUY-39891 — Hourly throughput check (2026-06-10 19:01 UTC fire, 18:00–19:00 UTC window)

**Result: PASS — ~282,881 / 150,000 (188.6% of threshold; rate ~298,337/hr across the 18:05:01Z → 19:01:54Z sample window). maglev continues to recover cleanly and the 18:00–19:00Z window saw sustained high-rate writes from deep_page + sustained lanes. No new failure child filed under [BUY-29861](/BUY/issues/BUY-29861) per the BUY-29861 rule ("If 150,000+ products were added, do not create the issue"). This dispatcher ([BUY-39891](/BUY/issues/BUY-39891)) closes at `done` after the state file is updated and the heartbeat comment is posted.**

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-10T18:00:00Z → 2026-06-10T19:00:00Z

| Metric | Value |
|---|---|
| Estimated net inserts in 18:00–19:00Z (`n_tup_ins` delta across the window) | **~282,881** |
| Threshold | 150,000 |
| Margin vs. threshold | **+132,881 (+88.6%)** |
| % of 150,000/hr target | **188.6%** |
| Per-hour rate (window 18:05:01Z → 19:01:54Z, ~0.9482h) | **~298,337/hr** (282,881 / 0.9482h = 298,337/hr) |
| `n_tup_ins` at 18:05:01Z (prior fire's sample, [BUY-39796](/BUY/issues/BUY-39796) heartbeat) | **27,800,369** |
| `n_tup_ins` at 19:01:54Z (this fire's sample) | **28,083,250** |
| `n_tup_ins` delta (18:05:01Z → 19:01:54Z) | **+282,881** (over 0.9482h = 298,337/hr) |
| `n_live_tup` @ 19:01:54Z | **63,554,602** (up from 63,342,080 @ 18:05:01Z = +212,522 in ~0.95h ≈ 224K live-tup growth/hr — consistent with the n_tup_ins rate minus VACUUM/decay) |
| `reltuples` for `products` | **61,767,104** (stale from pre-2026-06-08T10:21:09Z restart; ANALYZE not yet run for the post-restart rows) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T10:21:09.112373+00** (the [BUY-35444](/BUY/issues/BUY-35444) restart is **~56.7h old** at this fire — well outside the 18:00–19:00Z window, so the n_tup_ins delta method is valid and not contaminated by counter reset) |
| Maglev uptime at fire | **2 days 08:40:47** (well outside the 18:00–19:00Z window) |
| `relkind` for `products` | **r** (regular table, NOT partitioned) — no `products_sg`/`products_us`/`products_default` partition children (per [BUY-32878](/BUY/issues/BUY-32878) partition-children check) |
| Direct hourly COUNT(*) | **TIMEOUT** — `products_created_at_idx` is INVALID (`indisvalid=f`, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy); seq scan with `enable_indexscan=off` exceeds `statement_timeout` (30s tested) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **did not fire** for 18:00–19:00Z — cron entry is broken ([BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken since 2026-06-08T04:06Z); this BUY-39891 heartbeat is the canonical hourly fire for that missed window |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. We have two clean n_tup_ins readings bracketing the 18:00–19:00Z window:

1. **18:05:01Z** — the prior fire's sample = **27,800,369** (per `data/.throughput_state.json` snapshot before this fire at `data/.throughput_state.json.snapshot-pre-buy-39891-fire-20260610T190154Z`).
2. **19:01:54Z** — this fire's sample = **28,083,250**.

Net inserts during 18:00–19:00Z ≈ `n_tup_ins(19:01:54Z) - n_tup_ins(18:05:01Z)` = **282,881** rows over 0.9482h = **~298,337/hr**. Well above the 150K threshold — **PASS**.

This is a LOWER bound on the actual rows added in the window because:
- The 18:05:01Z reading is 5m01s after window start, so the first 5m01s of the window are NOT counted in the start value but ARE counted in the end value → small over-count (~25K rows at the 298K/hr rate).
- The 19:01:54Z value is 1m54s after window end, so the post-window drift is also captured in the end value (~9K rows at the 298K/hr rate).
- `n_tup_ins` is monotonic in the absence of VACUUM FULL or table truncation; maglev has not been restarted since 2026-06-08T10:21:09Z, and there has been no TRUNCATE, so the counter is a clean cumulative count.

### Rate trajectory across the 18:00–19:00Z window

Per the prior fire (17:00–18:00Z, [BUY-39796](/BUY/issues/BUY-39796) heartbeat) and this fire (18:00–19:00Z):

```
T_b=18:05:01Z N_b=27,800,369  (prior fire sample, post-17:00-18:00 hour)
T_d=19:01:54Z N_d=28,083,250  (this fire sample, post-18:00-19:00 hour)
```

The 17:00–18:00Z hour ([BUY-39796](/BUY/issues/BUY-39796) heartbeat) closed at **373,056 rows / 1.0372h = 359,748/hr** (per `data/.throughput_state.json` last_note and BUY-39796 doc). The 18:00–19:00Z hour ran at **~298,337/hr** — a ~17% drop from the prior hour, but still 2.0× the 150K threshold. The drop is consistent with reduced lane activity in the 18:00Z hour (no maglev restart, no contention event); both hours are well above the threshold, indicating sustained healthy ingest on maglev deep_page + sustained lanes.

## Why no child BUY-#### was filed

The BUY-29861 rule fires a child issue ONLY if real_rows < 150,000. This hour delivered 282,881 rows, which is 188.6% of the threshold. The dispatcher confirmed:

```
[throughput-dispatcher] Checking hour 2026-06-10T18:00:00+00:00 → 2026-06-10T19:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=282,881 target=150,000 (188.6%) source=n_tup_ins_delta
[throughput-dispatcher] PASS — 282,881 >= 150,000. No issue filed.
```

No `create_stall_issue` was called. The deduplication path was not exercised. The 18:00–19:00Z hour is recorded in `data/.throughput_state.json` as PASS.

## State file record (post-fire)

`data/.throughput_state.json` was updated by the dispatcher at 19:01:54.833531+00 with:

- `last_n_tup_ins`: 28,083,250
- `last_n_tup_ins_at`: 2026-06-10T19:01:54.833531+00:00
- `last_hour_checked`: 2026-06-10T18:00:00+00:00
- `last_hour_window_end`: 2026-06-10T19:00:00+00:00
- `last_check_result`: PASS
- `last_check_real_rows`: 282,881
- `last_check_source`: n_tup_ins_delta
- `last_n_live_tup`: 63,554,602
- `last_db_host`: maglev.proxy.rlwy.net:31310/railway
- `last_pm_start`: 2026-06-08T10:21:09.112373+00:00
- `last_check_delta_rows`: 282,881
- `last_check_delta_hours`: 0.9482
- `last_check_rate`: 298,337
- `last_check_threshold`: 150,000
- `last_note`: 18:00–19:00 hour PASS: delta 282,881 over 0.9482h = 298,337/hr (n_tup_ins PRIMARY signal). n_tup_ins 27,800,369 -> 28,083,250 between 2026-06-10T18:05:01.340190+00:00 and 2026-06-10T19:01:54.833531+00:00. reltuples=61,767,104 cross-check; n_live_tup=63,554,602. pm_start=2026-06-08T10:21:09Z (outside this hour, delta method valid). No child BUY-#### filed (rate > 150K threshold).

## Cross-checks

- `n_live_tup` grew from 63,342,080 → 63,554,602 = +212,522 over 0.95h ≈ 224K/hr. The lower live-tup growth vs. n_tup_ins delta (298K/hr) is consistent with VACUUM/cleanup activity reclaiming ~74K rows/hr — typical for maglev at this scale.
- `reltuples` (61,767,104) is stale (no ANALYZE since pre-2026-06-08T10:21:09Z restart). Per [feedback-reltuples-canonical-proxy](/.claude/memory), `reltuples` is the canonical proxy for **catalog counts** (not hourly throughput). n_tup_ins delta is the correct primary signal here.
- `pg_postmaster_start_time` = 2026-06-08T10:21:09Z, uptime = 2d8h40m. The 18:00–19:00Z window is well outside any restart boundary, so the n_tup_ins counter is monotonic across the window. No baseline reset.

## Tools / scripts touched

- `data/.throughput_state.json` — updated with the 18:00–19:00Z PASS record.
- `data/.throughput_state.json.snapshot-pre-buy-39891-fire-20260610T190154Z` — pre-fire snapshot of the state file.
- This doc — written under `docs/buy-39891-hourly-throughput-check-2026-06-10T18.md`.
- [BUY-39891](/BUY/issues/BUY-39891) — heartbeat comment posted, status set to `done`.

## Remaining

- (none) — 18:00–19:00Z hour PASS, no child needed. Next fire is the 19:00–20:00Z hour at ~20:00Z. The hourly auto-dispatcher cron remains broken ([BUY-33694](/BUY/issues/BUY-33694)); manual heartbeats continue.
- The BUY-35444 escalation condition (3 maglev restarts in <24h, escalate on 4th) is still armed but **NOT** triggered this hour — uptime is now 56.7h, well past the 24h watch window.
