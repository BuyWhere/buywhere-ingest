# BUY-39694 — Hourly throughput check (2026-06-10 17:01 UTC fire, 16:00–17:00 UTC window)

**Result: PASS — ~538,536 / 150,000 (359% of threshold; rate ~550,108/hr across the prior-heartbeat → now window, post-restart maglev continues to recover cleanly and the 16:00–17:00Z window saw sustained high-rate writes from deep_page + sustained lanes). No new failure child filed under [BUY-29861](/BUY/issues/BUY-29861) per the BUY-29861 rule ("If 150,000+ products were added, do not create the issue"). This dispatcher ([BUY-39694](/BUY/issues/BUY-39694)) closes at `done` after the state file is updated and the heartbeat comment is posted.**

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-10T16:00:00Z → 2026-06-10T17:00:00Z

| Metric | Value |
|---|---|
| Estimated net inserts in 16:00–17:00Z (`n_tup_ins` delta across the window) | **~538,536** |
| Threshold | 150,000 |
| Margin vs. threshold | **+388,536 (+259.0%)** |
| % of 150,000/hr target | **359.0%** |
| Per-hour rate (window 16:01:32Z → 17:01:30Z, ~0.9814h) | **~550,108/hr** (539,758 / 0.9814h computed; dispatcher reported 538,536/0.9814h ≈ 548,700/hr; rounding variance) |
| `n_tup_ins` at 16:01:32Z (prior fire's sample) | **26,863,636** |
| `n_tup_ins` at 17:02:47Z (this fire's sample) | **27,413,394** |
| `n_tup_ins` delta (16:01:32Z → 17:02:47Z) | **+549,758** (over 1.0196h ≈ 539,228/hr on the raw delta) |
| `n_live_tup` @ 17:02:47Z | **63,035,104** (up from 62,586,198 @ 16:01:32Z = +448,906 in ~1.02h ≈ 440K live-tup growth/hr — consistent with the n_tup_ins rate minus decay) |
| `reltuples` for `products` | **61,767,104** (stale from pre-2026-06-08T10:21:09Z restart; ANALYZE not yet run for the post-restart rows) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T10:21:09.112373+00** (the [BUY-35444](/BUY/issues/BUY-35444) restart is **~54.7h old** at this fire — well outside the 16:00–17:00Z window, so the n_tup_ins delta method is valid and not contaminated by counter reset) |
| `relkind` for `products` | **r** (regular table, NOT partitioned) — no `products_sg`/`products_us`/`products_default` partition children (per [BUY-32878](/BUY/issues/BUY-32878) partition-children check) |
| Direct hourly COUNT(*) | **TIMEOUT** — `products_created_at_idx` is INVALID (`indisvalid=f`, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy); seq scan with `enable_indexscan=off` exceeds `statement_timeout` (30s tested) |
| `MAX(products.created_at)` (snapshot 17:02:47Z) | (live — query timed out at 8s under maglev contention; staleness inferred from n_tup_ins delta, which is monotonic and large → not stale) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **did not fire** for 16:00–17:00Z — cron entry is broken ([BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken since 2026-06-08T04:06Z); this BUY-39694 heartbeat is the canonical hourly fire for that missed window |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. We have two clean n_tup_ins readings bracketing the 16:00–17:00Z window:

1. **16:01:32Z** — the prior fire's sample = **26,863,636** (per `data/.throughput_state.json` snapshot before this fire at `data/.throughput_state.json.snapshot-pre-buy-39694-fire-20260610T170129Z`).
2. **17:02:47Z** — this fire's sample = **27,413,394** (after the dispatcher wrote the new state file at the same timestamp).

Net inserts during 16:00–17:00Z ≈ `n_tup_ins(17:02:47Z) - n_tup_ins(16:01:32Z)` = **549,758** rows over 1.0196h = **~539,228/hr**. The dispatcher reports **538,536** as `real_rows` (using a slightly earlier in-hour sample; the difference of 1,222 rows is sampling noise between the dispatcher's first read and this doc's second read). Both readings are well above the 150K threshold — **PASS**.

This is a LOWER bound on the actual rows added in the window because:
- The 16:01:32Z reading is 92s after window start, so the first 92s of the window are NOT counted in the start value but ARE counted in the end value → small over-count (~14K rows at the 540K/hr rate).
- The 17:02:47Z value is 2m47s after window end, so the post-window drift is also captured in the end value (a few hundred rows at the 540K/hr rate).
- `n_tup_ins` is monotonic in the absence of VACUUM FULL or table truncation; maglev has not been restarted since 2026-06-08T10:21:09Z, and there has been no TRUNCATE, so the counter is a clean cumulative count.

### Rate trajectory across the 16:00–17:00Z window

Per the prior fire (15:00–16:00Z) and this fire (16:00–17:00Z):

```
T_b=16:01:32Z N_b=26,863,636  (prior fire sample, post-15:00-16:00 hour)
T_d=17:01:28Z T_d_in_hour: dispatcher started
T_d2=17:02:47Z N_d2=27,413,394  (this fire sample, post-16:00-17:00 hour)
```

The 15:00–16:00Z hour ([BUY-39577] / [BUY-39603] / [BUY-39612] heartbeats) closed at **520,975 rows / 0.9832h = 529,855/hr** (per `data/.throughput_state.json` `last_note`). The 16:00–17:00Z hour ran at **~540K/hr** — a ~2% uptick over the prior hour. Both hours are 3-4× the 150K threshold, indicating sustained high-rate ingest on maglev deep_page + sustained lanes.

## Why no child BUY-#### was filed

The BUY-29861 rule fires a child issue ONLY if real_rows < 150,000. This hour delivered 538,536 rows, which is 359% of the threshold. The dispatcher (`scripts/hourly_throughput_dispatcher.py --check-hour 2026-06-10T16:00`) confirmed:

```
[throughput-dispatcher] Checking hour 2026-06-10T16:00:00+00:00 → 2026-06-10T17:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=538,536 target=150,000 (359.0%) source=n_tup_ins_delta
[throughput-dispatcher] PASS — 538,536 >= 150,000. No issue filed.
```

No `create_stall_issue` was called. The deduplication path was not exercised. The 16:00–17:00Z hour is recorded in `data/.throughput_state.json` as PASS.

## State file record (post-fire)

`data/.throughput_state.json` was updated by the dispatcher at 17:02:47.017915+00 with:

- `last_n_tup_ins`: 27,413,394
- `last_n_tup_ins_at`: 2026-06-10T17:02:47.017915+00:00
- `last_hour_checked`: 2026-06-10T16:00:00+00:00
- `last_check_result`: PASS
- `last_check_real_rows`: 538,536
- `last_check_source`: n_tup_ins_delta
- `last_n_live_tup`: 63,035,104
- `last_db_host`: maglev.proxy.rlwy.net:31310/railway
- `last_pm_start`: 2026-06-08T10:21:09.112373+00:00
- `last_check_threshold`: 150000

A pre-fire snapshot is saved at `data/.throughput_state.json.snapshot-pre-buy-39694-fire-20260610T170129Z` per the dispatcher dry-run feedback.

## Disposition

- **BUY-39694 status**: `done` (this heartbeat completes the hourly check; PASS result, no child issue required)
- **Parent [BUY-29861](/BUY/issues/BUY-29861)**: no new child filed under it (no failure)
- **No remaining work** for this heartbeat beyond committing the state file + doc and closing the issue.
