# BUY-51266 blocked throughput check — 2026-06-15 09:00–10:00 UTC

## Summary

The BUY-29861 hourly throughput dispatcher could not evaluate the just-completed
`2026-06-15 09:00–10:00 UTC` window because the canonical catalog PostgreSQL
endpoint on maglev rejected both connection attempts with:

```text
FATAL: the database system is in recovery mode
```

Because BUY-29861 requires DB-proof numbers from canonical PostgreSQL, no PASS
or FAIL verdict can be issued for this hour from this heartbeat.

## Evidence

Time of repeated attempts: `2026-06-15T10:03:36Z`

Command:

```bash
python3 scripts/hourly_throughput_dispatcher.py --dry-run
```

Observed output on both attempts:

```text
[throughput-dispatcher] Checking hour 2026-06-15T09:00:00+00:00 → 2026-06-15T10:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
psycopg2.OperationalError: connection to server at "maglev.proxy.rlwy.net" (66.33.22.251), port 31310 failed: FATAL:  the database system is in recovery mode
```

## Impact

- No canonical throughput measurement is available for the `09:00–10:00 UTC`
  hour.
- No BUY-29861 failure child should be filed until canonical access is restored
  and the hour can be measured with DB-proof numbers.
- This hour remains retroactively reportable once maglev leaves recovery mode.

## Unblock

Owner: Rich / platform owner.

Action: restore canonical maglev availability for the pinned
`data/.catalog_db_url` target, then rerun the BUY-51266 hourly check for the
`2026-06-15 09:00–10:00 UTC` window.
