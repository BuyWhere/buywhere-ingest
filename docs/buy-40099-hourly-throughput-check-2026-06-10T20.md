# BUY-40099 — Hourly throughput check (2026-06-10 21:04 UTC fire, 20:00–21:00 UTC window)

**Result: PASS — ~536,364 / 150,000 (357.6% of threshold; rate ~529,378/hr across the 20:03:32Z → 21:04:21Z sample window). maglev is in a high-throughput run after the [BUY-35444](/BUY/issues/BUY-35444) restart is now 62h+ old, and the 20:00–21:00Z window saw strong sustained writes (deep_page + sustained lanes) — slightly above the 19:00–20:00Z hour's 576,412/561,237hr but still in the same "writer fleet healthy" band. No new failure child filed under [BUY-29861](/BUY/issues/BUY-29861) per the BUY-29861 rule ("If 150,000+ products were added, do not create the issue"). This dispatcher ([BUY-40099](/BUY/issues/BUY-40099)) closes at `done` after the state file is updated and the heartbeat comment is posted.**

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-10T20:00:00Z → 2026-06-10T21:00:00Z

| Metric | Value |
|---|---|
| Estimated net inserts in 20:00–21:00Z (`n_tup_ins` delta across the window) | **~536,364** |
| Threshold | 150,000 |
| Margin vs. threshold | **+386,364 (+257.6%)** |
| % of 150,000/hr target | **357.6%** |
| Per-hour rate (window 20:03:32Z → 21:04:21Z, ~1.0130h) | **~529,378/hr** (536,364 / 1.0130h ≈ 529K/hr) |
| `n_tup_ins` at 20:03:32Z (prior fire's sample, [BUY-39992](/BUY/issues/BUY-39992) heartbeat) | **28,659,662** |
| `n_tup_ins` at 21:04:21Z (this fire's sample) | **29,216,878** |
| `n_tup_ins` delta (20:03:32Z → 21:04:21Z) | **+557,216** (over 1.0130h ≈ 550,058/hr raw; 536,364 / 1.0130h ≈ 529K/hr dispatcher-computed, using the dispatcher's `(now-last) / (now-last_at)` window — the dispatcher formula spreads the delta over the inter-fire elapsed time) |
| `n_live_tup` @ 21:04:21Z | **64,463,464** (up from 64,010,584 @ 20:03:32Z = +452,880 in ~1.01h ≈ 448K live-tup growth/hr — consistent with the n_tup_ins rate minus VACUUM/decay) |
| `reltuples` for `products` | **61,767,104** (stale from pre-2026-06-08T10:21:09Z restart; ANALYZE not yet run for the post-restart rows) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T10:21:09.112373+00** (the [BUY-35444](/BUY/issues/BUY-35444) restart is **~62.7h old** at this fire — well outside the 20:00–21:00Z window, so the n_tup_ins delta method is valid and not contaminated by counter reset) |
| Maglev uptime at fire | **2 days 10:43:12** (well outside the 20:00–21:00Z window) |
| `relkind` for `products` | **r** (regular table, NOT partitioned) — no `products_sg`/`products_us`/`products_default` partition children (per [BUY-32878](/BUY/issues/BUY-32878) partition-children check) |
| Direct hourly COUNT(*) | **TIMEOUT** — `products_created_at_idx` is INVALID (`indisvalid=f`, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy); seq scan with `enable_indexscan=off` exceeds `statement_timeout` (30s tested) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **did not fire** for 20:00–21:00Z — cron entry is broken ([BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken since 2026-06-08T04:06Z); this BUY-40099 heartbeat is the canonical hourly fire for that missed window |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. We have two clean n_tup_ins readings bracketing the 20:00–21:00Z window:

1. **20:03:32Z** — the prior fire's sample = **28,659,662** (per the [BUY-39992](/BUY/issues/BUY-39992) heartbeat fire at 2026-06-10T20:03:54Z, and the post-fire `data/.throughput_state.json` snapshot which recorded `last_n_tup_ins=28,659,662` at `last_n_tup_ins_at=2026-06-10T20:03:32.714000+00:00`).
2. **21:04:21Z** — this fire's sample = **29,216,878** (per this fire's `data/.throughput_state.json` post-fire snapshot).

Net inserts during 20:00–21:00Z ≈ `n_tup_ins(21:04:21Z) - n_tup_ins(20:03:32Z)` = **557,216** rows over 1.0130h = **~550,058/hr**. The dispatcher's canonical report is **536,364 / 1.0130h = 529,378/hr** using its `(now_n - last_n) / (now - last_at)` formula. Both numbers are well above the 150K threshold — **PASS**.

This is a fair estimate of the actual rows added in the window because:
- The 20:03:32Z reading is 3m32s after window start, so the first 3m32s of the window are NOT counted in the start value but ARE counted in the end value → small over-count (~31K rows at the 550K/hr rate).
- The 21:04:21Z value is 4m21s after window end, so the post-window drift is also captured in the end value (~40K rows at the 550K/hr rate).
- Net effect: both end-side over-count (~40K) and start-side under-count (~31K) → net over-count ~9K, i.e., actual 20:00–21:00Z inserts ≈ **548,000 rows** (rounding to the nearest thousand). Either way, the PASS is comfortable at **>3.6× the 150K threshold**.
- `n_tup_ins` is monotonic in the absence of VACUUM FULL or table truncation; maglev has not been restarted since 2026-06-08T10:21:09Z, and there has been no TRUNCATE, so the counter is a clean cumulative count.

### Rate trajectory across the 20:00–21:00Z window

Per the prior fire (19:00–20:00Z, [BUY-39992](/BUY/issues/BUY-39992) heartbeat) and this fire (20:00–21:00Z):

```
T_b=20:03:32Z N_b=28,659,662  (prior fire sample, post-19:00-20:00 hour)
T_d=21:04:21Z N_d=29,216,878  (this fire sample, post-20:00-21:00 hour)
```

The 19:00–20:00Z hour ([BUY-39992](/BUY/issues/BUY-39992) heartbeat) closed at **576,412 rows / 1.0271h = 561,237/hr**. The 20:00–21:00Z hour ran at **~529,378/hr** — a small **~6% dip** from the prior hour, but still well above the 150K threshold. This is consistent with the deep_page + sustained lanes continuing at a steady-state ~500K/hr baseline after the BUY-35444 restart is now >60h old.

## Why no child BUY-#### was filed

The BUY-29861 rule fires a child issue ONLY if real_rows < 150,000. This hour delivered **536,364 rows** (or **557,216** by raw delta), both of which are **357.6% / 371.5% of the threshold**. The dispatcher confirmed:

```
[throughput-dispatcher] Checking hour 2026-06-10T20:00:00+00:00 → 2026-06-10T21:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=536,364 target=150,000 (357.6%) source=n_tup_ins_delta
[throughput-dispatcher] PASS — 536,364 >= 150,000. No issue filed.
```

No `create_stall_issue` was called. The deduplication path was not exercised. The 20:00–21:00Z hour is recorded in `data/.throughput_state.json` as PASS.

## State file record (post-fire)

`data/.throughput_state.json` was updated by this heartbeat fire at 2026-06-10T21:04:21Z with:

- `last_n_tup_ins`: 29,216,878
- `last_n_tup_ins_at`: 2026-06-10T21:04:21.479081+00:00
- `last_hour_checked`: 2026-06-10T20:00:00+00:00
- `last_hour_window_start`: 2026-06-10T20:00:00+00:00
- `last_hour_window_end`: 2026-06-10T21:00:00+00:00
- `last_check_result`: PASS
- `last_check_real_rows`: 536,364
- `last_check_source`: n_tup_ins_delta
- `last_n_live_tup`: 64,463,464
- `last_pm_start`: 2026-06-08T10:21:09.112373+00 (BUY-35444 restart baseline)
- `last_db_host`: maglev.proxy.rlwy.net:31310/railway
- `last_fire_timestamp`: 2026-06-10T21:04:21Z
- `last_issue_identifier`: BUY-40099

A pre-fire snapshot of the state file was saved to `/tmp/throughput_state.snapshot-pre-buy40099.json` (preserves the BUY-39992 baseline at 28,659,662 / 20:03:32Z for the next hour's audit trail).

## Cross-checks

- **n_live_tup trajectory**: 64,010,584 @ 20:03:32Z → 64,463,464 @ 21:04:21Z = **+452,880** rows in ~1.01h ≈ **448K live-tup growth/hr**. The live-tup counter accumulates the same inserts (minus VACUUM/dead-tup reclamation) and is consistent with the n_tup_ins rate minus a small decay component. ✓
- **pm_start check**: `2026-06-08T10:21:09.112373+00` (62.7h old at fire) — confirms the maglev counter has not been reset during the 20:00–21:00Z window. ✓
- **relkind check**: products is `relkind=r` (regular table) — no partitioned children (e.g. products_sg / products_us / products_default) to confuse the n_tup_ins delta. ✓
- **reltuples cross-check**: 61,767,104 (stale, from the pre-2026-06-08T10:21:09Z restart; ANALYZE hasn't run for the post-restart rows). Not used as a primary signal — the reltuples drift would have caused BUY-32950 to under-count, but the n_tup_ins delta method is the canonical one under maglev contention. ✓
- **Indexer health**: `products_created_at_idx` remains INVALID (per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy) — the secondary COUNT(*) path times out, but the n_tup_ins PRIMARY signal works fine. ✓
- **Hour-window COUNT(*) (best-effort secondary)**: TIMEOUT after 30s — `statement_timeout` triggered on the seq scan with `enable_indexscan=off` (forced because the only created_at index is INVALID). Expected and not a defect. ✓
- **Midnight snapshot**: No UTC midnight boundary crossed at this fire (21:04:21Z, well past the 00:00Z boundary) — the [BUY-33694](/BUY/issues/BUY-33694) midnight-snapshot logic in the dispatcher correctly no-ops. The last closed midnight snapshot was for 2026-06-09 → 2026-06-10, recorded in the state file with `last_closed_day.date = "2026-06-09"` and `n_tup_ins_open=21,366,014 → n_tup_ins_close=29,011,756` (delta 7,645,742). The 2026-06-10 → 2026-06-11 midnight will be captured at the 00:00–01:00Z BUY-40### fire. ✓

## Why this is the canonical fire (auto-dispatcher still broken)

The auto-dispatcher cron entry ([BUY-33694](/BUY/issues/BUY-33694)) is still broken since 2026-06-08T04:06Z (`MODULE_NOT_FOUND` errors — crontab references `/home/paperclip/scripts/...` and lacks the required `cd` into the workspace). Per the established pattern from [BUY-39694](/BUY/issues/BUY-39694), [BUY-39796](/BUY/issues/BUY-39796), [BUY-39891](/BUY/issues/BUY-39891), and [BUY-39992](/BUY/issues/BUY-39992), the manual heartbeat fire IS the canonical hourly check until the cron is repaired. This is the 5th consecutive manual hourly fire after the auto-dispatcher went dark, and the fleet has been comfortably above 150K/hr for every hour since 2026-06-09T22 (per the [BUY-39694](/BUY/issues/BUY-39694) → [BUY-39992](/BUY/issues/BUY-39992) chain).

## Sources / References

- [BUY-29861](/BUY/issues/BUY-29861) — Hourly throughput failure report (the rule: 150K/hr gate, parent of every hourly check)
- [BUY-33694](/BUY/issues/BUY-33694) — Hourly throughput dispatcher (canonical cron-driven check; cron still broken, manual heartbeats are the canonical fire)
- [BUY-32878](/BUY/issues/BUY-32878) — products_created_at_idx INVALID + no-DDL-on-maglev policy
- [BUY-35444](/BUY/issues/BUY-35444) — Third maglev restart (2026-06-08T10:21:09Z, ~62.7h old at this fire; counter not reset since)
- [BUY-39992](/BUY/issues/BUY-39992) — Prior hour check (19:00–20:00Z PASS, 576,412 rows / 561,237/hr)
- [BUY-32950](/BUY/issues/BUY-32950) — "Count(*) on products" issue (the wrong fix; reltuples is the canonical proxy per the BUY-33694 design)
- `data/.throughput_state.json` — State file (post-fire snapshot: last_n_tup_ins=29,216,878 @ 21:04:21.479081+00:00, real_rows=536,364)
- `/tmp/throughput_state.snapshot-pre-buy40099.json` — Pre-fire snapshot of the state file
- `docs/buy-40099-hourly-throughput-check-2026-06-10T20.md` — This doc
