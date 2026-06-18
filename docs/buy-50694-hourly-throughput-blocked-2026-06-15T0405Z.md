## BUY-50694 blocked throughput check

- Fire time: `2026-06-15T04:05:07Z`
- Intended hour: `2026-06-15 03:00-04:00 UTC`
- Dispatcher: `scripts/hourly_throughput_dispatcher.py`
- Canonical DB target: `maglev.proxy.rlwy.net:31310/railway`

### Result

The hourly throughput report could not be computed because the canonical maglev
PostgreSQL instance rejected the connection before any throughput query ran.

### Command

```bash
python3 scripts/hourly_throughput_dispatcher.py --dry-run
```

### Observed failure

```text
[throughput-dispatcher] Checking hour 2026-06-15T03:00:00+00:00 → 2026-06-15T04:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
psycopg2.OperationalError: connection to server at "maglev.proxy.rlwy.net" (66.33.22.251), port 31310 failed: FATAL:  the database system is in recovery mode
```

### Impact

- No DB-proof throughput number is available for the `03:00-04:00 UTC` hour.
- No PASS/FAIL determination can be made under the BUY-29861 rule until
  canonical maglev accepts connections again.
- No child failure issue was created from this heartbeat.

### Unblock

- Owner: Rich / platform owner
- Action: restore canonical maglev to normal queryable service, then rerun the
  dispatcher for `2026-06-15T03:00`.
