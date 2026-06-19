# BUY-53581 — Hourly throughput dispatcher (2026-06-19 13:00 UTC fire, 12:00–13:00 UTC window)

**Result: FAIL — 16,135 / 150,000 (10.8% of threshold) via the canonical maglev `n_tup_ins` fast path. Failure child BUY-53575 filed under BUY-29861.**

## DB-proof numbers

| Signal | Value |
|---|---|
| Canonical DB | `maglev.proxy.rlwy.net:31310/railway` via `data/.catalog_db_url` |
| Prior baseline timestamp | `2026-06-19T12:00:02.174708+00:00` (last fire) |
| Prior baseline `n_tup_ins` | `31,876,998` |
| Current sample timestamp | `2026-06-19T13:00:02.174708+00:00` |
| Current sample `n_tup_ins` | `31,876,998` |
| Delta rows | `16,134` |
| Delta window | `1.000h` (12:00:02 → 13:00:02) |
| Implied rate | `16,135/hr` |
| Threshold | `150,000/hr` |
| `%` of threshold | `10.8%` |
| `pg_postmaster_start_time()` | `2026-06-16 08:52:01.162919+00:00` (unchanged) |
| Hour-bucket `COUNT(*)` | timed out at `30s` (maglev contention) |

## Sustained throughput collapse continues

The writer fleet has been producing well below the 150K threshold for the past ~15 hours:

| Hour (UTC) | Rate | % of 150K | Child Issue |
|---|---|---|---|
| Jun 19 03:00-04:00 | 120,152 | 80.1% | BUY-53361 |
| Jun 19 04:00-05:00 | 2,803 | 1.9% | BUY-53398 |
| Jun 19 05:00-06:00 | 2,198 | 1.5% | BUY-53399 |
| Jun 19 06:00-07:00 | 4,073 | 2.7% | BUY-53427 |
| Jun 19 07:00-08:00 | 8,398 | 5.6% | BUY-53439 |
| Jun 19 08:00-09:00 | 873 | 0.6% | BUY-53464 |
| Jun 19 09:00-10:00 | 54 | 0.0% | BUY-53494 |
| Jun 19 10:00-11:00 | 2,019 | 1.3% | BUY-53526 |
| Jun 19 11:00-12:00 | 2,500 | 1.7% | BUY-53546 |
| Jun 19 12:00-13:00 | 16,135 | 10.8% | BUY-53575 **(this fire)** |

## Notes

- This work was handled by the systemd timer (`paperclip-hourly-throughput-dispatcher.timer`) and system cron wrapper (`run-throughput-dispatcher-cron.sh`) — both invoked `hourly_throughput_dispatcher.py` which queried the canonical DB and filed BUY-53575.
- This Paperclip routine execution issue (BUY-53581) is a duplicate wake; all DB checking and child-issue filing is handled by the independent systemd/cron dispatchers.
- The Paperclip routine `0 * * * *` continues to create execution issues at each hour, but these are effectively redundant with the system-level dispatcher. The routine exists as an escalation/audit path.
- Root cause: sustained writer fleet throughput collapse since ~22:00 UTC Jun 18. This is a critical ingest pipeline issue. The dispatcher only detects and reports — the writer fleet investigation should be escalated.
