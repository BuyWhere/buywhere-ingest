# BUY-39992 — Hourly throughput check (2026-06-10 20:03 UTC fire, 19:00–20:00 UTC window)

**Result: PASS — ~576,412 / 150,000 (384.3% of threshold; rate ~561,237/hr across the 19:01:54Z → 20:03:32Z sample window). maglev is in a high-throughput run after the BUY-35444 restart is now 58h+ old, and the 19:00–20:00Z window saw very strong writes from the deep_page + sustained lanes. No new failure child filed under [BUY-29861](/BUY/issues/BUY-29861) per the BUY-29861 rule ("If 150,000+ products were added, do not create the issue"). This dispatcher ([BUY-39992](/BUY/issues/BUY-39992)) closes at `done` after the state file is updated and the heartbeat comment is posted.**

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-10T19:00:00Z → 2026-06-10T20:00:00Z

| Metric | Value |
|---|---|
| Estimated net inserts in 19:00–20:00Z (`n_tup_ins` delta across the window) | **~576,412** |
| Threshold | 150,000 |
| Margin vs. threshold | **+426,412 (+284.3%)** |
| % of 150,000/hr target | **384.3%** |
| Per-hour rate (window 19:01:54Z → 20:03:32Z, ~1.0271h) | **~561,237/hr** (576,412 / 1.0271h = 561,237/hr) |
| `n_tup_ins` at 19:01:54Z (prior fire's sample, [BUY-39891](/BUY/issues/BUY-39891) heartbeat) | **28,083,250** |
| `n_tup_ins` at 20:03:32Z (this fire's sample) | **28,659,662** |
| `n_tup_ins` delta (19:01:54Z → 20:03:32Z) | **+576,412** (over 1.0271h = 561,237/hr) |
| `n_live_tup` @ 20:03:32Z | **64,010,584** (up from 63,554,602 @ 19:01:54Z = +455,982 in ~1.03h ≈ 444K live-tup growth/hr — consistent with the n_tup_ins rate minus VACUUM/decay) |
| `reltuples` for `products` | **61,767,104** (stale from pre-2026-06-08T10:21:09Z restart; ANALYZE not yet run for the post-restart rows) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T10:21:09.112373+00** (the [BUY-35444](/BUY/issues/BUY-35444) restart is **~57.7h old** at this fire — well outside the 19:00–20:00Z window, so the n_tup_ins delta method is valid and not contaminated by counter reset) |
| Maglev uptime at fire | **2 days 09:42:23** (well outside the 19:00–20:00Z window) |
| `relkind` for `products` | **r** (regular table, NOT partitioned) — no `products_sg`/`products_us`/`products_default` partition children (per [BUY-32878](/BUY/issues/BUY-32878) partition-children check) |
| Direct hourly COUNT(*) | **TIMEOUT** — `products_created_at_idx` is INVALID (`indisvalid=f`, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy); seq scan with `enable_indexscan=off` exceeds `statement_timeout` (30s tested) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **did not fire** for 19:00–20:00Z — cron entry is broken ([BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken since 2026-06-08T04:06Z); this BUY-39992 heartbeat is the canonical hourly fire for that missed window |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. We have two clean n_tup_ins readings bracketing the 19:00–20:00Z window:

1. **19:01:54Z** — the prior fire's sample = **28,083,250** (per `data/.throughput_state.json` snapshot before this fire at `data/.throughput_state.json.snapshot-pre-buy-39992-fire-20260610T200354Z`, which records the BUY-39891 fire's final state).
2. **20:03:32Z** — this fire's sample = **28,659,662**.

Net inserts during 19:00–20:00Z ≈ `n_tup_ins(20:03:32Z) - n_tup_ins(19:01:54Z)` = **576,412** rows over 1.0271h = **~561,237/hr**. Well above the 150K threshold — **PASS**.

This is a fair estimate of the actual rows added in the window because:
- The 19:01:54Z reading is 1m54s after window start, so the first 1m54s of the window are NOT counted in the start value but ARE counted in the end value → small over-count (~18K rows at the 561K/hr rate).
- The 20:03:32Z value is 3m32s after window end, so the post-window drift is also captured in the end value (~33K rows at the 561K/hr rate).
- Net effect: end-side over-count (~33K) and start-side under-count (~18K) → net over-count ~15K, i.e., actual 19:00–20:00Z inserts ≈ **561,000 rows** (rounding to the nearest thousand). Either way, the PASS is comfortable at **>3.7× the 150K threshold**.
- `n_tup_ins` is monotonic in the absence of VACUUM FULL or table truncation; maglev has not been restarted since 2026-06-08T10:21:09Z, and there has been no TRUNCATE, so the counter is a clean cumulative count.

### Rate trajectory across the 19:00–20:00Z window

Per the prior fire (18:00–19:00Z, [BUY-39891](/BUY/issues/BUY-39891) heartbeat) and this fire (19:00–20:00Z):

```
T_b=19:01:54Z N_b=28,083,250  (prior fire sample, post-18:00-19:00 hour)
T_d=20:03:32Z N_d=28,659,662  (this fire sample, post-19:00-20:00 hour)
```

The 18:00–19:00Z hour ([BUY-39891](/BUY/issues/BUY-39891) heartbeat) closed at **282,881 rows / 0.9482h = 298,337/hr**. The 19:00–20:00Z hour ran at **~561,237/hr** — an **~88% jump** from the prior hour, indicating deep_page + sustained lanes hit a high-rate stretch in the 19:00Z hour. This is the strongest hourly throughput reading since the BUY-35444 restart and is well above the 150K threshold.

## Why no child BUY-#### was filed

The BUY-29861 rule fires a child issue ONLY if real_rows < 150,000. This hour delivered **576,412 rows**, which is **384.3% of the threshold**. The dispatcher confirmed:

```
[throughput-dispatcher] Checking hour 2026-06-10T19:00:00+00:00 → 2026-06-10T20:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=576,412 target=150,000 (384.3%) source=n_tup_ins_delta
[throughput-dispatcher] PASS — 576,412 >= 150,000. No issue filed.
```

No `create_stall_issue` was called. The deduplication path was not exercised. The 19:00–20:00Z hour is recorded in `data/.throughput_state.json` as PASS.

## State file record (post-fire)

`data/.throughput_state.json` was updated by this heartbeat fire at 2026-06-10T20:03:54Z with:

- `last_n_tup_ins`: 28,659,662
- `last_n_tup_ins_at`: 2026-06-10T20:03:32.714000+00:00
- `last_hour_checked`: 2026-06-10T19:00:00+00:00
- `last_hour_window_start`: 2026-06-10T19:00:00+00:00
- `last_hour_window_end`: 2026-06-10T20:00:00+00:00
- `last_check_result`: PASS
- `last_check_real_rows`: 576,412
- `last_check_source`: n_tup_ins_delta
- `last_n_live_tup`: 64,010,584
- `last_db_host`: maglev.proxy.rlwy.net:31310/railway
- `last_pm_start`: 2026-06-08T10:21:09.112373+00:00
- `last_check_delta_rows`: 576,412
- `last_check_delta_hours`: 1.0271
- `last_check_rate`: 561,237
- `last_check_threshold`: 150,000
- `last_issue_identifier`: BUY-39992
- `last_fire_timestamp`: 2026-06-10T20:03:54Z

## Cross-checks

- `n_live_tup` grew from 63,554,602 → 64,010,584 = +455,982 over ~1.03h ≈ 444K/hr. The lower live-tup growth vs. n_tup_ins delta (561K/hr) is consistent with VACUUM/cleanup activity reclaiming ~117K rows/hr — typical for maglev at this scale during a high-throughput stretch.
- `reltuples` (61,767,104) is stale (no ANALYZE since pre-2026-06-08T10:21:09Z restart). Per [feedback-reltuples-canonical-proxy](/.claude/memory), `reltuples` is the canonical proxy for **catalog counts** (not hourly throughput). n_tup_ins delta is the correct primary signal here.
- `pg_postmaster_start_time` = 2026-06-08T10:21:09Z, uptime = 2d9h42m. The 19:00–20:00Z window is well outside any restart boundary, so the n_tup_ins counter is monotonic across the window. No baseline reset.

## Tools / scripts touched

- `data/.throughput_state.json` — updated with the 19:00–20:00Z PASS record.
- `data/.throughput_state.json.snapshot-pre-buy-39992-fire-20260610T200354Z` — pre-fire snapshot of the state file (preserves BUY-39891's 18:00–19:00Z record).
- This doc — written under `docs/buy-39992-hourly-throughput-check-2026-06-10T19.md`.
- [BUY-39992](/BUY/issues/BUY-39992) — heartbeat comment posted, status set to `done`.

## Remaining

- (none) — 19:00–20:00Z hour PASS, no child needed. Next fire is the 20:00–21:00Z hour at ~21:00Z. The hourly auto-dispatcher cron remains broken ([BUY-33694](/BUY/issues/BUY-33694)); manual heartbeats continue.
- The BUY-35444 escalation condition (3 maglev restarts in <24h, escalate on 4th) is still armed but **NOT** triggered — uptime is now 57.7h, well past the 24h watch window.
- The 19:00–20:00Z rate of ~561K/hr is the **strongest** hourly reading since the BUY-35444 restart and a positive signal for the deep_page + sustained lanes; if this rate holds across the next several hours, throughput is well-positioned to clear the 150K/hr threshold comfortably going into 2026-06-11.
