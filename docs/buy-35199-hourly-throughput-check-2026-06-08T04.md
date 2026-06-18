# BUY-35199 — Hourly throughput check (2026-06-08 05:01 UTC fire, 04:00–05:00 UTC window)

**Result: FAIL — 0 / 150,000 (writer pipe dark; maglev catalog DB still in startup/restart).** Failure report filed as a new child of [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`. This dispatcher ([BUY-35199](/BUY/issues/BUY-35199)) closes at `done` after the child is filed and the heartbeat comment is posted.

## Threshold

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- If a child for that hour already exists under [BUY-29861](/BUY/issues/BUY-29861), do **not** create a duplicate (none existed for 04:00–05:00; [BUY-35157](/BUY/issues/BUY-35157) covers 03:00–04:00, a separate hour).

## Just-completed hour for this fire: 2026-06-08T04:00:00Z → 2026-06-08T05:00:00Z

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **UNREACHABLE — maglev down (4th consecutive fire)** |
| Real rows (excluding synthetic merchants & `example.com`) | **0** (per writer-pipe ingest log, all 20 cycles from 04:00Z to 05:00Z report `written=0`) |
| Threshold | 150,000 |
| Margin vs. threshold | **-150,000 (-100.0%) or worse** |
| % of 150,000/hr target | **0.0%** |
| Direct hourly COUNT | TIMEOUT — `connection to server ... failed: server closed the connection unexpectedly` (5 retries at 05:01:01Z–05:01:25Z) |
| Raw TLS probe (Node) | not re-probed (same fingerprint as 02:00Z–04:00Z fires — TCP accepts, Postgres handshake ECONNRESET) |
| `n_tup_ins` baseline (last persisted) | 2,909,852 @ 2026-06-08T01:07:41Z (no fresh reading since 01:07Z — dispatcher DB query itself fails) |
| `n_live_tup` (last persisted) | 42,930,549 @ 2026-06-08T01:07:41Z |
| Writer pipe state (from ingest log) | **DARK** — every cycle in the 04:00Z–05:00Z window reports `exit=0` wrapper but `written=0` subprocess; `errors ≈ ceil(valid/500)` (failing batch writes) |

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **Direct hourly count — UNREACHABLE this fire** (5 retries at 05:01:01Z–05:01:25Z, all `server closed the connection unexpectedly`):
  ```sql
  -- (could not execute: maglev Postgres process is in startup/restart state)
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows,
         COUNT(*) FILTER (
           WHERE merchant_id::text NOT IN ('shopnow','techdepot','fastshop','megamart','smartcart','valuehub','easycart','quickbuy','primestore','globalmart')
           AND url NOT LIKE '%example.com%'
         ) AS real_rows
  FROM products
  WHERE created_at >= '2026-06-08 04:00:00+00'
    AND created_at <  '2026-06-08 05:00:00+00'
  GROUP BY 1 ORDER BY 1;
  ```
- **Indirect evidence — writer-pipe ingest log** (`logs/buy30590_deep_page_loop.log`), 20 cycles with hits in the 04:00Z–05:00Z window:

  | Cycle | Start (UTC) | Valid lines | Written | Errors | Avg latency (ms) | Batches | Notes |
  |---:|---:|---:|---:|---:|---:|---:|---|
  | 5437 | 04:03:41 | 26,929 | **0** | 54 | ~18,629 | 54 | |
  | 5438 | 04:05:35 | 14,398 | **0** | 29 | ~19,280 | 29 | |
  | 5439 | 04:08:18 | 23,181 | **0** | 47 | ~19,286 | 47 | |
  | 5440 | 04:08:32 | 360 | **0** | 1 | ~7,158 | 1 | tiny tail |
  | 5441 | 04:09:39 | 6,158 | **0** | 13 | ~17,863 | 13 | |
  | 5442 | 04:10:15 | 3,353 | **0** | 7 | ~12,213 | 7 | |
  | 5443 | 04:12:35 | 23,949 | **0** | 48 | ~18,590 | 48 | |
  | 5444 | 04:14:54 | 11,293 | **0** | 23 | ~19,306 | 23 | |
  | 5445 | 04:16:57 | 15,338 | **0** | 31 | ~19,333 | 31 | |
  | 5449 | 04:17:34 | 250 | **0** | 1 | ~7,129 | 1 | tiny tail (post 0-hit 5446-5448) |
  | 5486 | 04:22:31 | 5,497 | **0** | 11 | ~15,807 | 11 | |
  | 5487 | 04:24:50 | 22,034 | **0** | 45 | ~18,559 | 45 | |
  | 5489 | 04:25:40 | 3,400 | **0** | 7 | ~12,216 | 7 | |
  | 5490 | 04:27:59 | 18,886 | **0** | 38 | ~19,301 | 38 | |
  | 5491 | 04:31:08 | 30,502 | **0** | 62 | ~19,259 | 62 | |
  | 5492 | 04:33:20 | 87,554 | **0** | 176 | ~2,147 | 176 | 57s ingest (shortest — no contention) |
  | 5493 | 04:36:08 | 25,688 | **0** | 52 | ~19,294 | 52 | |
  | 5494 | 04:39:10 | 19,447 | **0** | 39 | ~18,640 | 39 | |
  | 5495 | 04:46:21 | 60,662 | **0** | 122 | ~19,347 | 122 | 293s ingest |
  | 5496 | 04:55:59 | 100,341 | **0** | 201 | ~18,658 | 201 | 480s ingest; spans 05:00Z boundary |
  | **Total** | | **499,220 valid** | **0 written** | **1,007** | | **1,008 batches** | **20 cycles, all dark** |

  (Cycles 5446–5448, 5450–5485 are recorded as `0 hit → 0 deep products` empty cycles — the per-cycle discovery runner was making restart attempts in the 04:18Z–04:22Z window; those generate no ingest lines because there are no products to write. The dark-pipe condition affects only cycles with real candidates.)

  **Comparison baseline (cycle 3512, 2026-06-06 05:55, healthy):** `lines=50000 valid=50000 written=50000 errors=0` — all writes succeeded in 37.5s. The current pattern (`exit=0` from wrapper, `written=0` from ingest subprocess) is the canonical fingerprint of a writer pipe where the subprocess can't reach the catalog DB. `errors ≈ ceil(valid/500)` confirms every batch is failing.

- **Prior-hour context** (`data/.throughput_state.json`, last update 2026-06-08T01:07:41Z):
  ```json
  {
    "last_n_tup_ins": 2909852,
    "last_n_tup_ins_at": "2026-06-08T01:07:41.754639+00:00",
    "last_hour_checked": "2026-06-08T02:00:00+00:00",
    "last_check_result": "FAIL",
    "last_check_real_rows": 0,
    "last_check_source": "maglev_unreachable",
    "last_n_live_tup": 42930549,
    "last_db_host": "maglev.proxy.rlway.net:31310/railway",
    "last_fire_buy": "BUY-35085",
    "last_filed_child": "BUY-35092",
    "last_fire_note": "Maglev Postgres in startup/restart (TCP accepts, Postgres handshake ECONNRESET). Same fingerprint as BUY-34770 + BUY-35041. Writer pipe dark."
  }
  ```
  The dispatcher crontab itself is also broken at the moment: `/home/paperclip/scripts/buy30392-hourly-throughput-snapshot.mjs` is missing (script actually lives at `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30392-hourly-throughput-snapshot.mjs` and the cron line lacks the `cd` to that workspace). The 04:00Z cron fire produced `Error: Cannot find module ...` in `logs/buy33694_dispatcher.log`. The 04:00Z-05:00Z window is unverified by the auto-dispatcher but is verified manually here from the writer-pipe ingest log.

## Why this happened

1. **Maglev catalog DB is still in startup/restart state** at 05:01Z (4h+ of darkness since the 01:07Z last-good `n_tup_ins` reading). TCP accepts but cannot complete the Postgres protocol handshake. This is the same fingerprint as [BUY-34770](/BUY/issues/BUY-34770) (2026-06-07 21:17Z, 22-minute maglev restart) and [BUY-35041](/BUY/issues/BUY-35041) (this same night, 01:00–02:00 hour).
2. **The writer pipe is dark for the same reason.** The BUY-30590 deep-cycle scraper is producing rows at scale (~499K validated in the 04:00Z–05:00Z window alone), but the ingest subprocess cannot reach the catalog DB. The `exit=0` from the wrapper is misleading: rows are validated and queued for write, but the actual `INSERT INTO products` step is failing batch-by-batch (`errors ≈ ceil(valid/500) = 1,007`).
3. **No writer rollback on the lanes themselves.** The wc lane ([BUY-31231](/BUY/issues/BUY-31231), 138.78M cluster, ~338K/hr) is still producing deep products; the shopify lane ([BUY-30590](/BUY/issues/BUY-30590)) is still scraping domains. The bottleneck is purely the downstream write path, not upstream discovery.
4. **Cycle 5496 spans the 05:00Z boundary** — its ingest finished at 04:55:59Z. The next cycle (5497) was 87738 valid, 0 written, errors=176. This fire window is the 04:00Z hour; the 05:00Z fire will pick up the 5497 cycle.

## Comparison vs. recent failure hours

| Hour (UTC) | Rows | Threshold | Margin | Status | Reference |
|---|---:|---:|---:|---|---|
| 2026-06-07 22:00–23:00 | 1,012,137 | 150,000 | +862,137 | PASS | dispatcher snapshot |
| 2026-06-07 23:00–00:00 | 942,360 | 150,000 | +792,360 | PASS | dispatcher snapshot |
| 2026-06-08 00:00–01:00 | 36,475 | 150,000 | -113,525 (-75.7%) | FAIL | [BUY-34989](/BUY/issues/BUY-34989) |
| 2026-06-08 01:00–02:00 | ≈ 0 (writer pipe dark) | 150,000 | -150,000 (-100.0%) | FAIL | [BUY-35051](/BUY/issues/BUY-35051) |
| 2026-06-08 02:00–03:00 | ≈ 0 (writer pipe dark) | 150,000 | -150,000 (-100.0%) | FAIL | [BUY-35092](/BUY/issues/BUY-35092) |
| 2026-06-08 03:00–04:00 | ≈ 0 (writer pipe dark, 28 cycles 0/646,808 valid) | 150,000 | -150,000 (-100.0%) | FAIL | [BUY-35157](/BUY/issues/BUY-35157) |
| **2026-06-08 04:00–05:00** | **0 (writer pipe dark, 20 cycles 0/499,220 valid, 1,007 batch errors)** | **150,000** | **-150,000 (-100.0%)** | **FAIL** | **child of BUY-29861 (this fire)** |

## Action taken

- Created child issue (assigned by Paperclip) under [BUY-29861](/BUY/issues/BUY-29861), priority critical, assignee user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- Posted heartbeat comment on [BUY-35199](/BUY/issues/BUY-35199) (this issue) documenting the hour, DB proof (or lack thereof), ingest-log indirect evidence, and the failure mode.
- Closed [BUY-35199](/BUY/issues/BUY-35199) at status `done` — its one-shot dispatcher duty for the 04:00–05:00 fire is complete.
- `data/.throughput_state.json` not updated by this heartbeat (dispatcher itself is unable to read the DB); will be refreshed automatically on the next successful cron fire once maglev recovers.

## Next steps (delegated; not in this issue's scope)

- **Ops / Bolt (maglev owner):** maglev has been in startup/restart state for ≥4h (since 01:07Z). This is now well past the 30-min threshold for a dedicated ops child issue. The 05:00Z fire should include a separate ops child of [BUY-29861](/BUY/issues/BUY-29861) escalating the maglev recovery and tagged P0. (Filed by Oracle at 05:01Z.)
- **Hex (BUY-30590 lane):** the writer backlog is now ~2M+ validated rows stranded across cycles 5385–5497; downstream drain must be coordinated with DB recovery to avoid overwhelming the recovering maglev instance.
- **Oracle (CDO, BUY-29861 assignee):** this is the 4th consecutive sub-bar hour (00:00–01:00 was 36,475; 01:00–04:00 was ≈0 three times; 04:00–05:00 is 0). Per the 12-hour streak rule, [BUY-30590](/BUY/issues/BUY-30590) remains blocked on sustained ≥150K/hr — the streak counter does NOT advance while the writer pipe is dark.
- **Auto-dispatcher repair (BUY-33694):** the crontab line `1 * * * * . /tmp/buy-33694-dispatcher.env && /usr/bin/node scripts/buy30392-hourly-throughput-snapshot.mjs --hours=24 >> logs/buy33694_dispatcher.log 2>&1` is missing the `cd` to the Oracle workspace and the script path itself is wrong (`/home/paperclip/scripts/...` does not exist). Until that cron is fixed, hourly dispatches will keep failing with `MODULE_NOT_FOUND` and Oracle's hourly heartbeat will need to perform the check manually as in this fire. (Filed as a separate `in_progress` follow-up under BUY-33694 — not this issue's scope.)
