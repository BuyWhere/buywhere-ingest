# BUY-51084 — Hourly throughput check blocked (2026-06-15 08:05:20 UTC)

## Summary

The standard hourly throughput dispatcher could not evaluate the just-completed
`2026-06-15 07:00–08:00 UTC` window because the canonical maglev catalog
database is in recovery mode.

This blocked the report before any DB-proof throughput number could be
computed. The harness `DATABASE_URL` is `roundhouse` and is not a valid
fallback for [BUY-29861](/BUY/issues/BUY-29861).

## Evidence

- Dispatcher path used: `scripts/hourly_throughput_dispatcher.py`
- Canonical DB pin: `data/.catalog_db_url`
- Fire time: `2026-06-15T08:05:20Z`
- Target hour: `2026-06-15 07:00–08:00 UTC`

Observed failure:

```text
[throughput-dispatcher] Checking hour 2026-06-15T07:00:00+00:00 → 2026-06-15T08:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
psycopg2.OperationalError: connection to server at "maglev.proxy.rlwy.net" (66.33.22.251), port 31310 failed: FATAL:  the database system is in recovery mode
```

## Impact

- No canonical PostgreSQL measurement is available for the 07:00–08:00 UTC hour.
- No PASS/FAIL determination can be made for this execution until maglev exits
  recovery mode and accepts read sessions again.
- The missed hour remains retroactively measurable once the canonical database
  is healthy.

## Unblock

- Owner: Rich / platform owner
- Action: restore canonical maglev read availability, then rerun BUY-51084 for
  the `2026-06-15 07:00–08:00 UTC` window.
