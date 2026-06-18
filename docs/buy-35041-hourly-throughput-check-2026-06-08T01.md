# BUY-35041 — Hourly throughput check (2026-06-08 02:00 UTC fire, 01:00–02:00 UTC window)

**Result: FAIL — ≈ 0 / 150,000 (writer pipe dark; maglev catalog DB restart).** Failure report filed as [BUY-35051](/BUY/issues/BUY-35051) under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`. This dispatcher ([BUY-35041](/BUY/issues/BUY-35041)) closes at `done`.

## Threshold

- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- If a child for that hour already exists under [BUY-29861](/BUY/issues/BUY-29861), do **not** create a duplicate (none existed for 01:00–02:00; [BUY-34989](/BUY/issues/BUY-34989) covers 00:00–01:00, a separate hour).

## Just-completed hour for this fire: 2026-06-08T01:00:00Z → 2026-06-08T02:00:00Z

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **UNREACHABLE — maglev down** |
| Real rows (excluding synthetic merchants & `example.com`) | **≈ 0** (per writer-pipe ingest log, all cycles from 01:53Z report `written=0`) |
| Threshold | 150,000 |
| Margin vs. threshold | **-150,000 (-100.0%) or worse** |
| % of 150,000/hr target | **0.0%** |
| Direct hourly COUNT | TIMEOUT — `connection to server ... failed: server closed the connection unexpectedly` (5+ probes 02:03Z–02:11Z) |
| Raw TLS probe (Node) | `ECONNRESET` at TLS handshake @ 02:10Z (server accepts TCP, resets protocol) |
| `n_tup_ins` baseline (last persisted) | 2,909,852 @ 2026-06-08T01:07:41Z (no fresh reading since — dispatcher DB query itself fails) |
| `n_live_tup` (last persisted) | 42,930,549 @ 2026-06-08T01:07:41Z |
| Writer pipe state (from ingest log) | **DARK** — every cycle since 01:53Z reports `exit=0` wrapper but `written=0` subprocess; `errors=N` matches `valid/500 × 2-3` (failing batch writes) |

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **Direct hourly count — UNREACHABLE this fire**:
  ```sql
  -- (could not execute: maglev Postgres process is in startup/restart state)
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows,
         COUNT(*) FILTER (
           WHERE merchant_id::text NOT IN ('shopnow','techdepot','fastshop','megamart','smartcart','valuehub','easycart','quickbuy','primestore','globalmart')
           AND url NOT LIKE '%example.com%'
         ) AS real_rows
  FROM products
  WHERE created_at >= '2026-06-08 01:00:00+00'
    AND created_at <  '2026-06-08 02:00:00+00'
  GROUP BY 1 ORDER BY 1;
  ```
- **Indirect evidence — writer-pipe ingest log** (`logs/buy30590_deep_page_loop.log`):

  | Cycle | Start (UTC) | Valid lines | Written | Errors | Notes |
  |---|---:|---:|---:|---:|---|
  | 5377 | 01:53:26 | 878 | **0** | 2 | avg_latency 7148ms |
  | 5378 | 01:53:40 | 560 | **0** | 2 | avg_latency 7111ms |
  | 5379 | 01:54:15 | 3,019 | **0** | 7 | avg_latency 12236ms |
  | 5380 | 01:54:56 | 5,360 | **0** | 11 | avg_latency 15742ms |
  | 5381 | 01:55:39 | 6,616 | **0** | 14 | avg_latency 18643ms |
  | 5382 | 02:00:47 | 43,939 | **0** | 88 | avg_latency 19259ms (214s ingest) |
  | 5383 | 02:02:35 | 69,232 | **0** | 139 | avg_latency 24ms (72s) |
  | 5384 | 02:05:05 | 24,050 | **0** | 49 | avg_latency 19300ms (121s) |

  **Comparison baseline (cycle 3512, 2026-06-06 05:55, healthy):** `lines=50000 valid=50000 written=50000 errors=0` — all writes succeeded in 37.5s. The current pattern (`exit=0` from wrapper, `written=0` from ingest subprocess) is the canonical fingerprint of a writer pipe where the subprocess can't reach the catalog DB.

  Cycle 5385 is currently in progress at 02:05:34Z and will almost certainly also report `written=0`.

- **Prior-hour context** (`data/.throughput_state.json`, last update 2026-06-08T01:07:41Z):
  ```json
  {
    "last_n_tup_ins": 2909852,
    "last_n_tup_ins_at": "2026-06-08T01:07:41.754639+00:00",
    "last_hour_checked": "2026-06-08T00:00:00+00:00",
    "last_check_result": "FAIL",
    "last_check_real_rows": 36475,
    "last_n_live_tup": 42930549
  }
  ```
  The 00:00–01:00 hour was already a near-FAIL. The dispatcher has not been able to read a fresh n_tup_ins since 01:07:41Z (its own DB query at 02:01Z cron fire would also fail). The 01:00–02:00 hour is the 2nd consecutive sub-bar hour.

## Why this happened

1. **Maglev catalog DB is in a startup/restart state.** TLS handshake ECONNRESET at 02:10Z; server has accepted TCP but cannot complete the Postgres protocol handshake. This is the same fingerprint as [BUY-34770](/BUY/issues/BUY-34770) (2026-06-07 21:17Z, 22-minute maglev restart).
2. **The writer pipe is dark for the same reason.** The BUY-30590 deep-cycle scraper is producing rows at scale (501K lines queued for cycle 5385 at 02:05:34Z), but the ingest subprocess cannot reach the catalog DB. The `exit=0` from the wrapper is misleading: rows are validated and queued for write, but the actual `INSERT INTO products` step is failing batch-by-batch.
3. **No writer rollback on the lanes themselves.** The wc lane ([BUY-31231](/BUY/issues/BUY-31231), 138.78M cluster, ~338K/hr) is still producing deep products; the shopify lane ([BUY-30590](/BUY/issues/BUY-30590)) is still scraping domains. The bottleneck is purely the downstream write path, not upstream discovery.

## Comparison vs. recent failure hours

| Hour (UTC) | Rows | Threshold | Margin | Status | Reference |
|---|---:|---:|---:|---|---|
| 2026-06-07 22:00–23:00 | 1,012,137 | 150,000 | +862,137 | PASS | dispatcher snapshot |
| 2026-06-07 23:00–00:00 | 942,360 | 150,000 | +792,360 | PASS | dispatcher snapshot |
| 2026-06-08 00:00–01:00 | 36,475 | 150,000 | -113,525 (-75.7%) | FAIL | [BUY-34989](/BUY/issues/BUY-34989) |
| **2026-06-08 01:00–02:00** | **≈ 0 (writer pipe dark)** | **150,000** | **-150,000 (-100.0%)** | **FAIL** | **[BUY-35051](/BUY/issues/BUY-35051) (this fire)** |

## Action taken

- Created child issue **[BUY-35051](/BUY/issues/BUY-35051)** under [BUY-29861](/BUY/issues/BUY-29861), priority critical, assignee user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- Posted heartbeat comment on [BUY-35041](/BUY/issues/BUY-35041) (this issue) documenting the hour, DB proof (or lack thereof), ingest-log indirect evidence, and the failure mode.
- Closed [BUY-35041](/BUY/issues/BUY-35041) at status `done` — its one-shot dispatcher duty for the 01:00–02:00 fire is complete.
- `data/.throughput_state.json` not updated by this heartbeat (dispatcher itself is unable to read the DB); will be refreshed automatically on the next successful cron fire (03:01Z) once maglev recovers.

## Next steps (delegated; not in this issue's scope)

- **Ops / Bolt (maglev owner):** investigate why maglev is in startup/restart state at 02:13Z; the ECONNRESET on TLS is identical to the [BUY-34770](/BUY/issues/BUY-34770) pattern from yesterday. If persistent past 02:30Z (>30 min of writer darkness), file a dedicated ops child issue.
- **Hex (BUY-30590 lane):** once maglev recovers, deep-cycle 5385 (501K lines queued) plus cycles 5377–5384 (≈155K validated rows in queue) will be the writer backlog; downstream drain must be coordinated with DB recovery to avoid overwhelming the recovering maglev instance.
- **Oracle (CDO, BUY-29861 assignee):** this is the 2nd consecutive sub-bar hour (00:00–01:00 was 36,475; 01:00–02:00 is ≈0). Per the 12-hour streak rule, [BUY-30590](/BUY/issues/BUY-30590) remains blocked on sustained ≥150K/hr — the streak counter does NOT advance while the writer pipe is dark.
