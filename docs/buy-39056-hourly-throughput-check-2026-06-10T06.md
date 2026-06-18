# Hourly throughput check — 2026-06-10 05:00–06:00 UTC

**Verdict:** **PASS** — ~519,464 rows added in the 05:00–06:00Z hour
(150,000 threshold exceeded by ~3.46x). No failure report needed.

## Source of truth

- DB host: `maglev.proxy.rlwy.net:31310/railway` (canonical maglev catalog)
- Parent check: BUY-39056
- Parent of failure reports: BUY-29861
- Threshold: 150,000 rows / hour

## DB samples (pg_stat_user_tables.products)

| time (UTC)              | n_tup_ins     | n_live_tup     | n_tup_upd    | n_tup_del |
|-------------------------|---------------|----------------|--------------|-----------|
| 2026-06-10T05:09:37Z *  |  21,402,874   |  57,802,743    |  40,944,068  |  2,229    |
| 2026-06-10T06:04:31Z    |  21,965,782   |  58,301,497    |  41,338,238  |  2,238    |
| **delta (54.9 min)**    |  **+562,908** |  **+498,754**  |  +394,170    |  +9       |

\* = last dispatcher reading (data/.throughput_state.json, sampled 2026-06-10T05:12Z)

## Hour-window computation (05:00–06:00Z)

Sampled 4.5 min past 06:00Z; recent-window rate used to trim the 06:00–06:04 over-shoot.

- Rate over 54.9 min window: **615,253 rows/hr** (n_tup_ins delta)
- Cross-check: **545,133 rows/hr** (n_live_tup delta — slower because some inserts
  are also being updated within the window)
- n_tup_ins at 05:00:00Z (back-estimated from last dispatcher's 18,555/hr FAIL
  rate over the 9m37s pre-sample gap): 21,399,899
- Raw rows since 05:00:00Z: 565,883
- Trim 06:00:00–06:04:31 over-shoot at 615,253/hr: −46,419
- **05:00–06:00Z net new rows: 519,464**
- **Hour rate: ~519,464 / hr = 519K/hr** (3.46x the 150K bar)

## Post-restart context (BUY-35444 third maglev restart)

- `pg_postmaster_start_time()` = 2026-06-08T10:21:09Z (BUY-35444 third restart)
- Hours since restart at sample: 43.72h
- Total n_tup_ins since restart: 21,965,782
- Average since restart: **~502,439 rows/hr** (this hour is in line with the average)

The 150K/hr cap (per the BUY-30590 driver issue) is no longer binding —
throughput is running at 3-4x the cap and stable.

## Sanity checks

- n_tup_upd growth (+394K in 55 min) is consistent with active `buywhere_ingest`
  re-inserts / on-conflict updates — no idle time.
- n_tup_del +9 only — deletions negligible, as expected.
- Hour 04:00–05:00Z was FAIL at 18,555 rows (dispatcher's last verdict);
  the 05:00–06:00Z hour recovered strongly (28x).
- products_created_at_idx remains INVALID (BUY-32878) but does not block
  the n_tup_ins accounting path.

## Disposition

- BUY-39056 check completed for 2026-06-10 05:00–06:00Z window
- Verdict: **PASS** (519K rows, 3.46x threshold)
- No child failure report needed under parent BUY-29861
- Next hourly wake will be a fresh check on the 06:00–07:00Z window
