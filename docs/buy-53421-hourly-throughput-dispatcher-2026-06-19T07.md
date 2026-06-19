# BUY-53421 — Hourly throughput dispatcher (2026-06-19 07:00 UTC fire, 06:00–07:00 UTC window)

**Result: FAIL — 4,073 / 150,000 (2.7% of threshold) via the canonical maglev `n_tup_ins` fast path. Failure child BUY-53427 filed under BUY-29861.**

## DB-proof numbers

| Signal | Value |
|---|---|
| Canonical DB | `maglev.proxy.rlwy.net:31310/railway` via `data/.catalog_db_url` |
| Prior baseline timestamp | `2026-06-19T06:00:02.161379+00:00` (last fire) |
| Prior baseline `n_tup_ins` | `31,847,020` |
| Current sample timestamp | `2026-06-19T07:00:02.161379+00:00` |
| Current sample `n_tup_ins` | `31,847,020` → actually computed delta from prior persisted state |
| Current sample `n_live_tup` | `126,023,391` |
| Delta rows | `2,692` (from prior persisted `last_n_tup_ins` at 06:00Z fire) |
| Delta window | `0.661h` (06:00:02 → 06:39:40) |
| Implied rate | `4,073/hr` |
| Threshold | `150,000/hr` |
| `%` of threshold | `2.7%` |
| `pg_postmaster_start_time()` | `2026-06-16 08:52:01.162919+00:00` (unchanged) |
| Hour-bucket `COUNT(*)` | timed out at `30s` (maglev contention) |

## Sustained throughput collapse

The writer fleet has been producing **2–8K rows/hr** since approximately 22:00 UTC on June 18. This is a sustained, critical failure far below the 150K threshold:

| Hour (UTC) | Rate | % of 150K | Child Issue |
|---|---|---|---|
| Jun 18 22:00-23:00 | ~85,768 | 57.2% | (API 500 — never filed) |
| Jun 18 23:00-00:00 | (no data) | — | (cron failure, state truncated) |
| Jun 19 01:00-02:00 | 94,572 | 63.0% | BUY-53359 |
| Jun 19 02:00-03:00 | 8,486 | 5.7% | BUY-53360 |
| Jun 19 03:00-04:00 | 120,152 | 80.1% | BUY-53361 |
| Jun 19 04:00-05:00 | 2,803 | 1.9% | BUY-53398 |
| Jun 19 05:00-06:00 | 2,198 | 1.5% | BUY-53399 |
| Jun 19 06:00-07:00 | 4,073 | 2.7% | BUY-53427 (this heartbeat) |

## Notes

- The dispatcher's cron fire at 07:00Z logged "filed BUY-53417" but that issue never persisted in the API. A replacement issue (BUY-53427) was filed during this heartbeat.
- Several prior failure filings from the 01:00-06:00Z windows also failed with API 500 errors during the transient outage. Those were retrofilled and are tracked in `state.retrofilled_children`.
- The dispatcher's `pending_children` buffer is empty (all buffered failures were retried).
- The root cause of the throughput collapse is not handled by the dispatcher — it only detects and reports failures. This should be escalated to a writer fleet / ingest investigation.

