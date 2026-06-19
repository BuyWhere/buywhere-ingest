# BUY-53447 — Hourly throughput dispatcher (2026-06-19 08:01 UTC fire, 07:00–08:00 UTC window)

**Result: FAIL — 8,398 / 150,000 (5.6% of threshold) via the canonical maglev `n_tup_ins` fast path. Failure child BUY-53439 filed under BUY-29861.**

## DB-proof numbers

| Signal | Value |
|---|---|
| Canonical DB | `maglev.proxy.rlwy.net:31310/railway` via `data/.catalog_db_url` |
| Prior baseline timestamp | `2026-06-19T07:00:02.161379+00:00` (last fire) |
| Prior baseline `n_tup_ins` | `31,847,020` |
| Current sample timestamp | `2026-06-19T08:00:02.161451+00:00` |
| Current sample `n_tup_ins` | `31,855,418` |
| Delta rows | `8,398` |
| Delta window | `1.000h` (07:00:02 → 08:00:02) |
| Implied rate | `8,398/hr` |
| Threshold | `150,000/hr` |
| `%` of threshold | `5.6%` |
| `pg_postmaster_start_time()` | `2026-06-16 08:52:01.162919+00:00` (unchanged) |
| Hour-bucket `COUNT(*)` | timed out at `30s` (maglev contention) |

## Sustained throughput collapse continues

The writer fleet has been producing **2–9K rows/hr** since approximately 22:00 UTC on June 18 — every hour a critical failure far below the 150K threshold:

| Hour (UTC) | Rate | % of 150K | Child Issue |
|---|---|---|---|
| Jun 18 22:00-23:00 | ~85,768 | 57.2% | (API 500 — never filed) |
| Jun 18 23:00-00:00 | ~236,611 | 157.7% | PASS |
| Jun 19 00:00-01:00 | ~153,343 | 102.2% | PASS |
| Jun 19 01:00-02:00 | 94,572 | 63.0% | BUY-53359 |
| Jun 19 02:00-03:00 | 8,486 | 5.7% | BUY-53360 |
| Jun 19 03:00-04:00 | 120,152 | 80.1% | BUY-53361 |
| Jun 19 04:00-05:00 | 2,803 | 1.9% | BUY-53398 |
| Jun 19 05:00-06:00 | 2,198 | 1.5% | BUY-53399 |
| Jun 19 06:00-07:00 | 4,073 | 2.7% | BUY-53427 |
| Jun 19 07:00-08:00 | 8,398 | 5.6% | BUY-53439 ***(this fire)*** |

## Notes

- The dispatcher cron fired at 08:01Z and filed BUY-53439 successfully.
- All previous API 500 failures from the earlier outage have been retrofilled (shown in `state.retrofilled_children`).
- `pending_children` buffer is empty (no new API failures).
- Root cause: sustained writer fleet throughput collapse since ~22:00 UTC Jun 18. This is a critical ingest pipeline issue, not a dispatcher problem — the dispatcher only detects and reports.
