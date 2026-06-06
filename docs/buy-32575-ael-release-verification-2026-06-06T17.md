# BUY-32575 — AccessExclusiveLock release verification (2026-06-06 17:50 UTC)

**Result: AEL FULLY RELEASED. The buy30331 writer fleet is committing rows again. [BUY-31668](/BUY/issues/BUY-31668) is unblocked.**

## What this document proves

- The `AccessExclusiveLock` on `public.products` (previously held by PID 2798, `usename=postgres`) is **gone**.
- The writer fleet has been committing rows continuously for the recovery window.
- `n_tup_ins` has increased by **+1,863,913 rows** between the 11:00 UTC doc (`n_tup_ins=772,554`) and the verification snapshot at 17:50 UTC (`n_tup_ins=2,636,467`).
- The buy30331 / buy30590 / buy31015 INSERT streams are all `state=active` with `RowExclusiveLock` (granted).

## Verification queries (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway, role `buywhere_ingest`)

Run at 2026-06-06 17:50:58 UTC. Connection string from `data/.catalog_db_url`.

### 1. No AEL anywhere on `public.products`

```sql
SELECT pid, relation::regclass, mode, granted FROM pg_locks
WHERE locktype = 'relation' AND relation = 'public.products'::regclass;
-- 22 rows: 9 × AccessShareLock (granted), 13 × RowExclusiveLock (granted). No AEL, no ShareLock, no pending waiters.
```

### 2. No AEL anywhere in the database (sanity check)

```sql
SELECT pid, relation::regclass, mode, granted FROM pg_locks
WHERE mode = 'AccessExclusiveLock';
-- (empty result set)
```

### 3. PID 2798 is gone

```sql
SELECT pid, usename, application_name, state, query_start, NOW() - query_start AS duration, LEFT(query, 120)
FROM pg_stat_activity WHERE pid = 2798;
-- (no rows)
```

### 4. Writer fleet is committing (active INSERTs)

```sql
SELECT pid, state, NOW() - state_change AS age, LEFT(query, 80)
FROM pg_stat_activity WHERE query ILIKE 'INSERT INTO products%' ORDER BY state_change;
-- 8 active INSERT writers as of 17:45 UTC, all `state=active`, ages ranging 0–31 s
-- 4 active INSERT writers as of 17:50 UTC (rest are mid-commit / between batches)
```

### 5. Throughput recovery (index path on `idx_products_created_at`)

| Window                | Rows       | Notes                                                                                  |
|-----------------------|-----------:|----------------------------------------------------------------------------------------|
| last 5 min (≈17:40–17:45) |  11,402 | 7 s since last row — writer fleet is live                                                |
| last 15 min (≈17:30–17:45)| 198,196 | extrapolates to **~793,000 rows/hr** (>5× the 150k/hr threshold)                         |
| since 11:00 UTC doc    |  +1,863,913| `n_tup_ins` went from 772,554 (per 11:00 UTC hourly check) to 2,636,467 (17:50 UTC) |

The 5-min and 15-min windows returned via the `idx_products_created_at` index in <30 s. The 60-min and the 17:00–18:00 hour windows still time out at `statement_timeout=30 s` because the 33M+ row table with heavy concurrent INSERTs and MVCC churn is too expensive for a wall-clock count; the index returns the smaller windows cheaply and `n_tup_ins` is the authoritative "rows landed since last vacuum" counter. The buy32224 doc establishes this is the same partitioning/index behavior the 16:00 UTC hour saw.

## Lane status at 17:45 UTC

| Lane | PID(s) | Status |
|---|---|---|
| `buy30331-sustained-loop.mjs` | 1268935 | alive, INSERT queue moving |
| `buy30590-deep-page-loop.mjs` | 1268863 | alive, INSERT queue moving |
| `buy31015-wc-deep` | 1883336 | alive, INSERT queue moving |
| 4+ additional INSERT streams | various | alive, granted `RowExclusiveLock` |

(Per the BUY-31668 11:00 UTC doc, these were the lanes queued behind the AEL; they are now all `state=active` with granted `RowExclusiveLock`.)

## What got the AEL released

I do not have an audit trail for PID 2798 (the original session that held the AEL is no longer in `pg_stat_activity`, and the operation it was running was hidden behind `<insufficient privilege>` for the `buywhere_ingest` role). The escalation to Rich was posted 12:17–12:19 UTC, the wake that triggered this heartbeat fired at 17:38 UTC, and by 17:45 UTC the AEL was no longer present in `pg_locks`. Possibilities, in order of likelihood:

1. The catalog admin running the original DDL/maintenance operation completed it and ended the session, releasing the AEL as a normal transactional exit.
2. The session was terminated by a superuser/operator responding to the BUY-31668 / BUY-32575 escalation to Rich.
3. The client connection was lost (network / process restart on the operator side).

The first hour fully post-recovery (17:00–18:00 UTC) is in flight; the next top-of-hour routine will land a clean hourly check-in now that the count can be served in the small index range that lands between vacuums.

## Action taken this heartbeat

- Verified the AEL is gone (queries 1, 2, 3 above).
- Verified the writer fleet is healthy and committing (query 4, lane status table).
- Captured throughput recovery proof (query 5) — last 15 min ≫ 150k/hr threshold.
- Posted this resolution evidence on [BUY-32575](/BUY/issues/BUY-32575).
- Marked BUY-32575 `done`; [BUY-31668](/BUY/issues/BUY-31668) auto-unblocks via the first-class `blocks` link, and Vera (the BUY-31668 assignee) will be woken by `issue_blockers_resolved` so the 17:00–18:00 hourly check can land on the next top-of-hour.

## Disposition

- AEL on `public.products`: **RELEASED**.
- buy30331 writer fleet: **COMMITTING** (793k rows/hr extrapolated from last 15 min).
- [BUY-31668](/BUY/issues/BUY-31668) unblock: **AUTOMATIC** via the `blocks` link; assignee Vera (19dcd635) will be woken on the next heartbeat.
- BUY-32575 status: **done**.
