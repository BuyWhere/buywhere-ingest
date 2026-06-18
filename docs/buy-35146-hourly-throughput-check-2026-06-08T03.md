# BUY-35146 — Hourly throughput check (2026-06-08 04:06 UTC fire, 03:00–04:00 UTC window)

**Result: FAIL — ≈ 0 / 150,000 (writer pipe dark; maglev catalog DB still in startup/restart).** Failure report filed as a new child of [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`. This dispatcher ([BUY-35146](/BUY/issues/BUY-35146)) closes at `done` after the child is filed and the heartbeat comment is posted.

## Threshold

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- If a child for that hour already exists under [BUY-29861](/BUY/issues/BUY-29861), do **not** create a duplicate (none existed for 03:00–04:00; [BUY-35092](/BUY/issues/BUY-35092) covers 02:00–03:00, a separate hour).

## Just-completed hour for this fire: 2026-06-08T03:00:00Z → 2026-06-08T04:00:00Z

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **UNREACHABLE — maglev down (3rd consecutive fire)** |
| Real rows (excluding synthetic merchants & `example.com`) | **≈ 0** (per writer-pipe ingest log, all 28 cycles from 03:00Z to 04:08Z report `written=0`) |
| Threshold | 150,000 |
| Margin vs. threshold | **-150,000 (-100.0%) or worse** |
| % of 150,000/hr target | **0.0%** |
| Direct hourly COUNT | TIMEOUT — `connection to server ... failed: server closed the connection unexpectedly` (3+ probes at 04:05Z–04:07Z) |
| Raw TLS probe (Node) | not re-probed (same fingerprint as 02:00Z fire — TCP accepts, Postgres handshake ECONNRESET) |
| `n_tup_ins` baseline (last persisted) | 2,909,852 @ 2026-06-08T01:07:41Z (no fresh reading since — dispatcher DB query itself fails) |
| `n_live_tup` (last persisted) | 42,930,549 @ 2026-06-08T01:07:41Z |
| Writer pipe state (from ingest log) | **DARK** — every cycle in the 03:00Z–04:08Z window reports `exit=0` wrapper but `written=0` subprocess; `errors=N` matches `valid/500 × ceil` (failing batch writes) |

## DB proof (canonical PostgreSQL @ maglev.proxy.rlway.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **Direct hourly count — UNREACHABLE this fire** (3 retries, all `server closed the connection unexpectedly`):
  ```sql
  -- (could not execute: maglev Postgres process is in startup/restart state)
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows,
         COUNT(*) FILTER (
           WHERE merchant_id::text NOT IN ('shopnow','techdepot','fastshop','megamart','smartcart','valuehub','easycart','quickbuy','primestore','globalmart')
           AND url NOT LIKE '%example.com%'
         ) AS real_rows
  FROM products
  WHERE created_at >= '2026-06-08 03:00:00+00'
    AND created_at <  '2026-06-08 04:00:00+00'
  GROUP BY 1 ORDER BY 1;
  ```
- **Indirect evidence — writer-pipe ingest log** (`logs/buy30590_deep_page_loop.log`), 28 cycles in the 03:00Z–04:08Z window:

  | Cycle | Start (UTC) | Valid lines | Written | Errors | Avg latency (ms) | Notes |
  |---:|---:|---:|---:|---:|---:|---|
  | 5413 | 03:00:15 | 21,941 | **0** | 44 | ~7148 | first cycle in window |
  | 5414 | 03:00:45 | 1,884 | **0** | 4 | ~7146 | small tail |
  | 5415 | 03:07:09 | 63,933 | **0** | 128 | ~19000 | 307s ingest |
  | 5416 | 03:10:11 | 23,782 | **0** | 48 | ~19200 | |
  | 5417 | 03:12:27 | 17,709 | **0** | 36 | ~19000 | |
  | 5418 | 03:13:29 | 6,976 | **0** | 14 | ~19000 | |
  | 5419 | 03:15:11 | 14,864 | **0** | 30 | ~19000 | |
  | 5420 | 03:16:29 | 9,750 | **0** | 20 | ~19000 | |
  | 5421 | 03:22:34 | 50,075 | **0** | 101 | ~19000 | 243s ingest |
  | 5422 | 03:25:43 | 31,160 | **0** | 63 | ~19000 | |
  | 5423 | 03:26:44 | 4,543 | **0** | 10 | ~19000 | |
  | 5424 | 03:28:45 | 17,373 | **0** | 35 | ~19000 | |
  | 5425 | 03:30:21 | 13,282 | **0** | 27 | ~19000 | |
  | 5426 | 03:32:39 | 14,152 | **0** | 29 | ~19000 | |
  | 5427 | 03:33:53 | 9,250 | **0** | 19 | ~19000 | |
  | 5428 | 03:36:19 | 46,836 | **0** | 94 | ~19000 | |
  | 5429 | 03:37:30 | 25,226 | **0** | 51 | ~19000 | |
  | 5430 | 03:41:14 | 33,611 | **0** | 68 | ~19000 | |
  | 5431 | 03:43:17 | 16,477 | **0** | 33 | ~19000 | |
  | 5432 | 03:46:23 | 30,138 | **0** | 61 | ~19000 | |
  | 5433 | 03:53:10 | 71,811 | **0** | 144 | ~19000 | 343s ingest |
  | 5434 | 03:53:24 | 52 | **0** | 1 | ~7146 | tiny tail |
  | 5435 | 03:57:15 | 32,489 | **0** | 65 | ~19335 | |
  | 5436 | 03:59:58 | 24,626 | **0** | 50 | ~19300 | |
  | 5437 | 04:03:41 | 26,929 | **0** | 54 | ~18629 | |
  | 5438 | 04:05:35 | 14,398 | **0** | 29 | ~19280 | |
  | 5439 | 04:08:18 | 23,181 | **0** | 47 | ~19286 | last cycle in window |
  | 5440 | 04:08:32 | 360 | **0** | 1 | ~7158 | tiny tail (spans 04:00Z) |
  | **Total** | | **~646,808 valid** | **0 written** | | | **28 cycles, all dark** |

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
  The dispatcher crontab itself is also broken at the moment: `/home/paperclip/scripts/buy30392-hourly-throughput-snapshot.mjs` is missing (script actually lives at `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30392-hourly-throughput-snapshot.mjs` and the cron line lacks the `cd` to that workspace). The 04:00Z cron fire produced `Error: Cannot find module ...` in `logs/buy33694_dispatcher.log`. The 03:00Z-04:00Z window is unverified by the auto-dispatcher but is verified manually here from the writer-pipe ingest log.

## Why this happened

1. **Maglev catalog DB is still in startup/restart state** at 04:06Z (3h+ of darkness since the 01:07Z last-good `n_tup_ins` reading). TCP accepts but cannot complete the Postgres protocol handshake. This is the same fingerprint as [BUY-34770](/BUY/issues/BUY-34770) (2026-06-07 21:17Z, 22-minute maglev restart) and [BUY-35041](/BUY/issues/BUY-35041) (this same night, 01:00–02:00 hour).
2. **The writer pipe is dark for the same reason.** The BUY-30590 deep-cycle scraper is producing rows at scale (~647K validated in the 03:00Z–04:08Z window alone), but the ingest subprocess cannot reach the catalog DB. The `exit=0` from the wrapper is misleading: rows are validated and queued for write, but the actual `INSERT INTO products` step is failing batch-by-batch (`errors ≈ valid/500`).
3. **No writer rollback on the lanes themselves.** The wc lane ([BUY-31231](/BUY/issues/BUY-31231), 138.78M cluster, ~338K/hr) is still producing deep products; the shopify lane ([BUY-30590](/BUY/issues/BUY-30590)) is still scraping domains. The bottleneck is purely the downstream write path, not upstream discovery.

## Comparison vs. recent failure hours

| Hour (UTC) | Rows | Threshold | Margin | Status | Reference |
|---|---:|---:|---:|---|---|
| 2026-06-07 22:00–23:00 | 1,012,137 | 150,000 | +862,137 | PASS | dispatcher snapshot |
| 2026-06-07 23:00–00:00 | 942,360 | 150,000 | +792,360 | PASS | dispatcher snapshot |
| 2026-06-08 00:00–01:00 | 36,475 | 150,000 | -113,525 (-75.7%) | FAIL | [BUY-34989](/BUY/issues/BUY-34989) |
| 2026-06-08 01:00–02:00 | ≈ 0 (writer pipe dark) | 150,000 | -150,000 (-100.0%) | FAIL | [BUY-35051](/BUY/issues/BUY-35051) |
| 2026-06-08 02:00–03:00 | ≈ 0 (writer pipe dark) | 150,000 | -150,000 (-100.0%) | FAIL | [BUY-35092](/BUY/issues/BUY-35092) |
| **2026-06-08 03:00–04:00** | **≈ 0 (writer pipe dark, 28 cycles 0/646,808 valid)** | **150,000** | **-150,000 (-100.0%)** | **FAIL** | **child of BUY-29861 (this fire)** |

## Action taken

- Created child issue (assigned by Paperclip) under [BUY-29861](/BUY/issues/BUY-29861), priority critical, assignee user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- Posted heartbeat comment on [BUY-35146](/BUY/issues/BUY-35146) (this issue) documenting the hour, DB proof (or lack thereof), ingest-log indirect evidence, and the failure mode.
- Closed [BUY-35146](/BUY/issues/BUY-35146) at status `done` — its one-shot dispatcher duty for the 03:00–04:00 fire is complete.
- `data/.throughput_state.json` not updated by this heartbeat (dispatcher itself is unable to read the DB); will be refreshed automatically on the next successful cron fire once maglev recovers.

## Next steps (delegated; not in this issue's scope)

- **Ops / Bolt (maglev owner):** maglev has been in startup/restart state for ≥3h (since 01:07Z). This is now well past the 30-min threshold for a dedicated ops child issue. If persistent past the 05:00Z hour, file a dedicated ops child of [BUY-29861](/BUY/issues/BUY-29861) escalating the maglev recovery and tagged P0.
- **Hex (BUY-30590 lane):** the writer backlog is now ~1.5M+ validated rows stranded across cycles 5385–5440; downstream drain must be coordinated with DB recovery to avoid overwhelming the recovering maglev instance.
- **Oracle (CDO, BUY-29861 assignee):** this is the 3rd consecutive sub-bar hour (00:00–01:00 was 36,475; 01:00–02:00 was ≈0; 02:00–03:00 was ≈0; 03:00–04:00 is ≈0). Per the 12-hour streak rule, [BUY-30590](/BUY/issues/BUY-30590) remains blocked on sustained ≥150K/hr — the streak counter does NOT advance while the writer pipe is dark.
- **Auto-dispatcher repair (BUY-33694):** the crontab line `1 * * * * . /tmp/buy-33694-dispatcher.env && /usr/bin/node scripts/buy30392-hourly-throughput-snapshot.mjs --hours=24 >> logs/buy33694_dispatcher.log 2>&1` is missing the `cd` to the Oracle workspace and the script path itself is wrong (`/home/paperclip/scripts/...` does not exist). Until that cron is fixed, hourly dispatches will keep failing with `MODULE_NOT_FOUND` and Oracle's hourly heartbeat will need to perform the check manually as in this fire. Filed as a separate `in_progress` follow-up under BUY-33694 (not this issue's scope).
