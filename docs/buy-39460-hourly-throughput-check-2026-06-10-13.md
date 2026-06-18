# BUY-39460 Hourly throughput check — 2026-06-10 13:00–14:00Z

- Issue: BUY-39460 (parent: BUY-29861)
- Window checked: 2026-06-10 13:00:00Z to 2026-06-10 14:00:00Z (just-completed hour)
- Verdict: **PASS** — rate well above 150,000 rows/hour threshold
- Action taken: **NO child BUY-#### filed** (per task contract)

## DB-proof numbers (maglev catalog — `data/.catalog_db_url`)

| Signal | Value | Note |
|---|---|---|
| `pg_postmaster_start_time()` | 2026-06-08 10:21:09.112373+00 (BUY-35444 3rd maglev restart) | Outside this hour, so n_tup_ins delta is valid (no restart baseline artifact) |
| State-file baseline `n_tup_ins` @ 13:01:47Z | 24,787,467 | Dispatcher's `data/.throughput_state.json` (12:00–13:00Z hour PASS, 731,402/hr) |
| 60-second sample: `n_tup_ins` @ 14:03:43Z | 25,627,092 | T0 |
| 60-second sample: `n_tup_ins` @ 14:04:43Z | 25,637,925 | T1 |
| Sample delta (60s) | 10,833 rows | |
| Live 60s rate | **649,980 rows/hour** | `10,833 × 3600 / 60` |
| Final `n_tup_ins` sample @ ~14:05Z | 25,646,091 | Steady climb, no stall |
| Final `n_live_tup` @ ~14:05Z | 61,557,380 | |
| `products` table size | 77 GB | |

## Estimated 13:00–14:00Z delta

- `n_tup_ins` at 13:00:00Z ≈ 24,765,746 (state-file 13:01:47Z value minus 107s × 203 rows/s — the 12:00–13:00Z rate)
- `n_tup_ins` at 14:00:00Z ≈ 25,586,829 (T1 sample minus 283s × 180.55 rows/s — the post-boundary 60s rate)
- **Estimated 13:00–14:00Z net products added ≈ 821,083 rows** (well above 150,000 threshold)

## Method notes

- Hour-bucket `COUNT(*)` on `created_at BETWEEN 13:00 AND 14:00` timed out at 8s statement_timeout (per `BUY-32878`: `products_created_at_idx` is INVALID, so a 61M-row range scan is unfeasible).
- Therefore: n_tup_ins delta + 60-second live-rate sample (the BUY-33694 dispatcher pattern, primary signal under maglev contention).
- Maglev restart is on 2026-06-08 10:21:09Z — outside the 13:00–14:00Z window — so the n_tup_ins cumulative counter is monotonic across the whole window (no post-restart baseline=0 artifact per the post-restart baseline rule).

## Cross-check

- `n_live_tup` = 61,557,380 (vs 60,827,763 at 13:01:47Z) — grew by 729,617 rows in ~63 minutes → ~695,000 rows/hour, consistent with n_tup_ins-derived rate within sampling noise.
- No instrumentation gap; pg_stat counters healthy.
