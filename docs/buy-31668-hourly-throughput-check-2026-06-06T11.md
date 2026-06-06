# BUY-31668 — Hourly sustained-throughput check (2026-06-06 10:00–11:00 UTC)

**Result: UNCONFIRMABLE — canonical `public.products` held in AccessExclusiveLock by a superuser session for the full window.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no action beyond posting the parent check-in.
- Net products added < 150,000 → raise a child issue restating the directive.
- The exact-hour `COUNT(*)` cannot be obtained for this hour because of the lock; **no child failure report created** because the data is not yet decidable, and the buy30331 writer fleet is itself stalled (writers wait on the same relation lock).

## Just-completed hour: 2026-06-06T10:00:00+00:00 → 2026-06-06T11:00:00+00:00

| Metric | Value |
|---|---|
| `products.created_at` rows in window | **unconfirmable** — query times out on lock acquisition (3 s `lock_timeout`) |
| Threshold | 150,000 |
| Margin | n/a (lock-induced stall, not a throughput decision) |

## DB proof attempt (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (workspace data dir). Session verified as maglev: `current_user=buywhere_ingest, current_database=railway`.

- `pg_locks` snapshot at **2026-06-06 12:13 UTC**:
  - 1 × `AccessExclusiveLock` on `public.products` (PID 2798, `usename=postgres`, `application_name=psql`, query hidden by `<insufficient privilege>`)
  - 3 × `ShareLock` on `public.products` (PIDs 2798, 3412, 3413 — same superuser cohort)
  - 1 × `AccessShareLock` pending (this session's count query, waiting for AEL to release)
  - 6 × `RowExclusiveLock` pending — the buy30331-sustained-loop / buy30590-deep-page-loop / buy31015-wc-deep ingest-stream writers, all queued behind the AEL
- Direct `COUNT(*)` for the measured hour (and even a single-row `ORDER BY id DESC LIMIT 1`) **all return `ERROR: canceling statement due to lock timeout`** when `lock_timeout=3s` is set; without `lock_timeout` the same queries hang.
- `idx_products_created_at` (the canonical hour-bucket path from [BUY-32334](/BUY/issues/BUY-32334)) is present in `pg_indexes`, but cannot be exercised while the table itself is AEL-locked.
- `pg_stat_user_tables` (catalog view, no data scan required) reports `n_live_tup=33,596,984`, `n_tup_ins=772,554` since the last vacuum at 2026-06-06 10:07:22 UTC — consistent with heavy sustained write traffic, but does not break that count down by hour.

## Lane status at 2026-06-06 12:13 UTC

| Lane | PID | Started | Status |
|---|---:|---|---|
| `buy30590-deep-page-loop.mjs` | 1268863 | 07:07 UTC | alive (CPU ~3%) |
| `buy30331-sustained-loop.mjs` | 1268935 | 07:07 UTC | alive (CPU ~4%) |
| `buy30331-ingest-stream` (cycle-3149) | 1882938 | 11:01 UTC | alive, INSERT queued on relation lock |
| `buy30331-ingest-stream` (deep-cycle-3765) | 1882953 | 11:01 UTC | alive, INSERT queued on relation lock |
| `buy30331-ingest-stream` (wc-deep-cycle-471) | 1883336 | 11:01 UTC | alive, INSERT queued on relation lock |
| `cc-shopify-discover-v2.mjs` | 1452167 | 08:07 UTC | alive (CPU ~3%) |
| `buy30619-s3cdx-lane.mjs` (cc_main_2023_50) | 2067364 | 12:04 UTC | alive, freshly respawned |
| `buy30727-supervisor-smoke-lane` (4 procs) | 1126458/1126663/1129028/1129084 | 06:25–06:26 UTC | idle smoke lanes (expected idle) |

**No lane died during this heartbeat.** All required processes are alive, and the live continuation path is intact. The fleet is healthy except for being unable to commit INSERTs while the AEL is held.

## Dash / Hex / Shopper

No idle/quiet check was required this heartbeat — the canonical read itself is blocked, and the writer streams are queued waiting on the same lock. The hourly check-in for 11:00–12:00 UTC (the next fire) will need to retry once the AEL is released.

## Action taken this heartbeat
- Waited ~25 minutes polling `pg_locks` for AEL release on `public.products`. Lock held the entire window.
- Re-attempted the exact count with `lock_timeout=3s` and `statement_timeout=10s`. Both confirm AEL is the blocker, not the index path.
- Verified `idx_products_created_at` is still present (the BUY-32334 fix is in place and would let the count return in ~1.2 s once the lock clears).
- Posted the parent check-in on [BUY-30590](/BUY/issues/BUY-30590) with this same evidence.
- Marked [BUY-31668](/BUY/issues/BUY-31668) `blocked` with the AccessExclusiveLock as the named first-class blocker; unblock owner is the catalog admin running PID 2798 on the maglev `postgres` role.

## Disposition
- BUY-30590 hour status: **unconfirmable** for 2026-06-06 10:00–11:00 UTC. Consecutive ≥150k streak remains **0/12** (last clear was 2026-06-05 21:00 UTC; the 20:00 hour broke the prior 9-hour run; nothing confirmed since).
- The buy30331 writer fleet is itself stalled by the same AEL. **This is a real infrastructure cap, not a writer regression.** Escalated via the issue-blocked handoff below.
- No `done` for BUY-30590 — the close criterion is 12 consecutive ≥150k hours, and this hour cannot be counted either way while the table is locked.

## Next fire
- Hourly routine will fire again at the next top-of-hour. If the AEL is released by then, the count query should return in ~1.2 s using `idx_products_created_at`. If still locked, the next heartbeat will repeat the wait and post another unconfirmable check-in.
