# BUY-50895 — Hourly throughput check blocked (2026-06-15 06:05:30 UTC)

## Summary

The standard hourly throughput dispatcher could not evaluate the just-completed
`2026-06-15 05:00–06:00 UTC` window because the canonical maglev catalog
endpoint in `data/.catalog_db_url` is still in PostgreSQL recovery and has not
yet reached a consistent state that accepts connections.

This blocked the report before any DB-proof throughput number could be
computed. The harness `DATABASE_URL` remains `roundhouse` and is not a valid
fallback for [BUY-29861](/BUY/issues/BUY-29861).

## Evidence

- Dispatcher path used: `scripts/hourly_throughput_dispatcher.py`
- Canonical DB pin: `data/.catalog_db_url`
- Fire time: `2026-06-15T06:05:30Z`
- Target hour: `2026-06-15 05:00–06:00 UTC`
- Existing unblock owner issue: [BUY-50740](/BUY/issues/BUY-50740)

Observed failure:

```text
[throughput-dispatcher] Checking hour 2026-06-15T05:00:00+00:00 → 2026-06-15T06:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
psycopg2.OperationalError: connection to server at "maglev.proxy.rlwy.net" (66.33.22.251), port 31310 failed: FATAL:  the database system is not yet accepting connections
DETAIL:  Consistent recovery state has not been yet reached.
```

## Impact

- No canonical PostgreSQL measurement is available for the `05:00–06:00 UTC`
  hour.
- No PASS/FAIL determination can be made for this execution until maglev is
  back on a healthy canonical endpoint.
- The missed hour remains retroactively measurable once canonical maglev access
  is restored.

## Unblock

- Owner: assignee of [BUY-50740](/BUY/issues/BUY-50740)
- Action: restore the production catalog endpoint behind `data/.catalog_db_url`
  so it accepts normal connections again, then rerun BUY-50895 for the
  `2026-06-15 05:00–06:00 UTC` window.
