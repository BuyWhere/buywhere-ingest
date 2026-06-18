# BUY-51638 — Hourly throughput check blocked (2026-06-15 14:06:11 UTC)

## Summary

The canonical maglev catalog accepted connections again for the
`2026-06-15 13:00–14:00 UTC` check, but the saved `n_tup_ins` baseline in
`data/.throughput_state.json` predated a database restart.

That made the dispatcher's primary signal invalid for this hour:
`pg_postmaster_start_time()` was `2026-06-15T09:56:28.874687+00:00`, while the
saved baseline timestamp was `2026-06-15T03:04:56.202238+00:00`. The secondary
hour-bucket `COUNT(*)` path still timed out under maglev contention, so no
canonical DB-proof PASS/FAIL number could be produced for the just-completed
hour.

## Evidence

- Dispatcher path used: `scripts/hourly_throughput_dispatcher.py`
- Canonical DB pin: `data/.catalog_db_url`
- Fire time: `2026-06-15T14:06:11Z`
- Target hour: `2026-06-15 13:00–14:00 UTC`
- Current maglev postmaster start: `2026-06-15T09:56:28.874687+00:00`
- Invalid saved baseline timestamp: `2026-06-15T03:04:56.202238+00:00`

Observed outcomes:

```text
[throughput-dispatcher] Checking hour 2026-06-15T13:00:00+00:00 → 2026-06-15T14:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
```

```text
SELECT COUNT(*)
FROM products
WHERE created_at >= '2026-06-15T13:00:00+00:00'
  AND created_at <  '2026-06-15T14:00:00+00:00';

ERROR: canceling statement due to statement timeout
```

```text
SELECT pg_postmaster_start_time(), n_tup_ins, n_live_tup
FROM pg_stat_user_tables
WHERE relname = 'products';

(2026-06-15 09:56:28.874687+00:00, 44019, 44019)
```

## Impact

- The initially filed children [BUY-51653](/BUY/issues/BUY-51653) and
  [BUY-51654](/BUY/issues/BUY-51654) were based on invalid cross-restart
  `n_tup_ins` deltas and should not stand as real hourly failure reports.
- No reliable canonical PASS/FAIL determination is available yet for the
  `13:00–14:00 UTC` hour.
- The dispatcher now rejects cross-restart `n_tup_ins` deltas so later hourly
  checks will not repeat this false-failure path.

## Unblock

- Owner: Oracle / platform owner on [BUY-50740](/BUY/issues/BUY-50740)
- Action: preserve or provide a post-restart canonical hourly anchor for the
  affected hour, or restore an exact per-hour counting path that can complete
  without timing out under maglev contention, then rerun the
  `2026-06-15 13:00–14:00 UTC` check.
