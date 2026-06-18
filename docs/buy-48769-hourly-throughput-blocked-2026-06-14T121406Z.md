# BUY-48769 — Hourly throughput check blocked (2026-06-14 12:14:06 UTC)

## Summary

The standard hourly throughput dispatcher could not evaluate the just-completed
`2026-06-14 11:00–12:00 UTC` window because the canonical maglev catalog
credential in `data/.catalog_db_url` no longer has login permission.

This blocked the report before any DB-proof throughput number could be
computed. The harness `DATABASE_URL` is `roundhouse` and is not a valid
fallback for [BUY-29861](/BUY/issues/BUY-29861).

## Evidence

- Dispatcher path used: `scripts/hourly_throughput_dispatcher.py`
- Canonical DB pin: `data/.catalog_db_url`
- Fire time: `2026-06-14T12:14:06Z`
- Target hour: `2026-06-14 11:00–12:00 UTC`

Observed failure:

```text
[throughput-dispatcher] Checking hour 2026-06-14T11:00:00+00:00 → 2026-06-14T12:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
psycopg2.OperationalError: connection to server at "maglev.proxy.rlwy.net" (66.33.22.251), port 31310 failed: FATAL:  role "buywhere_ingest" is not permitted to log in
```

## Impact

- No canonical PostgreSQL measurement is available for the 11:00–12:00 UTC hour.
- No PASS/FAIL determination can be made for this execution without restoring
  maglev access.
- The missed hour remains retroactively measurable once a valid canonical
  credential is restored.

## Unblock

- Owner: Rich / platform owner
- Action: restore a login-capable canonical maglev credential for
  `data/.catalog_db_url` or provide a replacement canonical read credential,
  then rerun BUY-48769 for the `2026-06-14 11:00–12:00 UTC` window.
