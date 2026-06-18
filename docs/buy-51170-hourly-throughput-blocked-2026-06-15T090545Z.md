# BUY-51170 — Hourly throughput check blocked (2026-06-15 09:05:45 UTC)

## Summary

The standard hourly throughput dispatcher could not evaluate the just-completed
`2026-06-15 08:00–09:00 UTC` window because the canonical maglev catalog
endpoint in `data/.catalog_db_url` is still unhealthy.

This blocked the report before any DB-proof throughput number could be
computed. The harness `DATABASE_URL` is `roundhouse` and is not a valid
fallback for [BUY-29861](/BUY/issues/BUY-29861).

## Evidence

- Dispatcher path used: `scripts/hourly_throughput_dispatcher.py`
- Canonical DB pin: `data/.catalog_db_url`
- Fire time: `2026-06-15T09:05:45Z`
- Target hour: `2026-06-15 08:00–09:00 UTC`
- Existing unblock owner issue: [BUY-50740](/BUY/issues/BUY-50740)

Observed failure:

```text
window 2026-06-15T08:00:00+00:00 2026-06-15T09:00:00+00:00
OperationalError: connection to server at "maglev.proxy.rlwy.net" (66.33.22.251), port 31310 failed: SSL SYSCALL error: EOF detected
```

Related same-day failure mode from the earlier blocked hour:

```text
[throughput-dispatcher] Checking hour 2026-06-15T04:00:00+00:00 → 2026-06-15T05:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
psycopg2.OperationalError: connection to server at "maglev.proxy.rlwy.net" (66.33.22.251), port 31310 failed: FATAL:  the database system is in recovery mode
```

The endpoint is therefore still not usable for canonical hourly measurement,
even though the exact symptom has changed from recovery-mode refusal to an EOF
drop during connection setup.

## Impact

- No canonical PostgreSQL measurement is available for the `08:00–09:00 UTC`
  hour.
- No PASS/FAIL determination can be made for this execution until maglev is
  back on a healthy canonical endpoint.
- The missed hour remains retroactively measurable once canonical maglev access
  is healthy again.

## Unblock

- Owner: assignee of [BUY-50740](/BUY/issues/BUY-50740)
- Action: restore the production catalog endpoint behind `data/.catalog_db_url`
  so it no longer drops or serves a recovery DB, then rerun BUY-51170 for the
  `2026-06-15 08:00–09:00 UTC` window.
