# BUY-39805: Midnight-Boundary n_tup_ins Snapshot

## Mechanism shipped (2026-06-10)

### Files

- `scripts/midnight_snapshot.py` (new) — standalone CLI + `capture_closed_day_snapshot()` API
  - Reads `data/.catalog_db_url` (maglev only)
  - Detects UTC midnight boundary since last persisted reading
  - Writes `last_closed_day` + `last_midnight_recorded_date` to `data/.throughput_state.json`
  - Posts a comment to the BUY-33694 thread with the boundary read
  - Idempotent within a closed day; `--force` overrides
- `scripts/hourly_throughput_dispatcher.py` (modified) — calls `capture_closed_day_snapshot()` after every successful fire (passes `dry_run=args.dry_run` for safe dry-runs)

### State schema additions

`data/.throughput_state.json` now carries:

```json
{
  "last_midnight_recorded_date": "2026-06-09",
  "last_closed_day": {
    "date": "2026-06-09",
    "n_tup_ins_open":  21366014,
    "n_tup_ins_close": 29011756,
    "delta":           7645742,
    "n_live_tup_close": 64292485,
    "open_at":  "2026-06-09T23:03:00+00:00",
    "close_at": "2026-06-10T20:30:39.377056+00:00",
    "db_host":  "maglev.proxy.rlwy.net:31310/railway",
    "source":   "midnight_snapshot"
  }
}
```

### Verification done in this heartbeat

1. Dry-run with same-day state → `No UTC midnight boundary crossed; nothing to do.` (no-op confirmed)
2. Synthetic 2026-06-09 → 2026-06-10 boundary in dry-run → correctly detects closed day 2026-06-09, reads live maglev
3. Live fire (synthetic boundary) → wrote state, posted comment `c11dd07e-7c0d-4f73-8e52-34c881a16e77` to BUY-33694 thread
4. Idempotency: `last_midnight_recorded_date` guard rejects re-fire for the same closed day; `--force` overrides
5. Dispatcher dry-run smoke: integration is wired; passes `dry_run=args.dry_run` through to the snapshot

### What is NOT done in this heartbeat (deferred to next-boundary verification)

- The 2026-06-10 → 2026-06-11 boundary has not yet been crossed. The success criterion is the 2026-06-11 daily CEO report citing an exact `n_tup_ins` delta for the closed 2026-06-10 day, without reconstruction. That requires the next dispatcher fire (or manual heartbeat) at 00:01+ on 2026-06-11 to detect the boundary and record the closed day.

### Next action

- The first agent (Vera) or dispatcher fire at 00:01+ on 2026-06-11 will detect the 2026-06-10 → 2026-06-11 boundary and record `last_closed_day.date = 2026-06-10` automatically.
- The 2026-06-11 daily CEO report (Vera) cites `state.last_closed_day.delta` directly in the `Daily Failure Summary` / `Incidents And Execution Path` section, without bracketing reads.
- After the 2026-06-11 daily report cites the result, this issue can be closed as `done`.

### Cron wiring (deferred, non-blocking)

- The dispatcher cron is still broken per BUY-33694. The mechanism works without it via the manual heartbeat path. Once the cron is fixed, the dispatcher integration will make the snapshot fully automatic.
