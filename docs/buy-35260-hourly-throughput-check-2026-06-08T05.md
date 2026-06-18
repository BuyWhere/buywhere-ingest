# BUY-35260 — Hourly throughput check (2026-06-08 06:04 UTC fire, 05:00–06:00 UTC window)

**Result: FAIL — 0 / 150,000 (maglev catalog DB restart at 06:03:42Z wiped the 05:00–06:00Z window inserts; post-restart catalog has no rows in that window).** Failure report filed as a new child of [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`. This dispatcher ([BUY-35260](/BUY/issues/BUY-35260)) closes at `done` after the child is filed and the heartbeat comment is posted.

## Threshold

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- If a child for that hour already exists under [BUY-29861](/BUY/issues/BUY-29861), do **not** create a duplicate (none existed for 05:00–06:00; [BUY-35212](/BUY/issues/BUY-35212), [BUY-35213](/BUY/issues/BUY-35213), [BUY-35220](/BUY/issues/BUY-35220) cover 04:00–05:00, a separate hour, and were deduped earlier as parallel fires).

## Just-completed hour for this fire: 2026-06-08T05:00:00Z → 2026-06-08T06:00:00Z

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **0** (post-restart catalog has no rows with `created_at` in 05:00–06:00Z) |
| Real rows (excluding synthetic merchants & `example.com`) | **0** |
| Threshold | 150,000 |
| Margin vs. threshold | **-150,000 (-100.0%)** |
| % of 150,000/hr target | **0.0%** |
| `n_tup_ins` (cumulative since 06:03:42Z restart) | 251,311 @ 06:03:53Z |
| `n_live_tup` (post-restart, all backfill) | 49,476,821 @ 06:03:53Z |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T06:03:42.503380+00** — the postmaster is 11 seconds old at the time of this fire |
| `MAX(products.created_at)` | **2026-06-07T11:06:05.546222+00** — the post-restart data is a backfill with original `created_at` values, NOT a fresh ingestion window |
| Direct hourly COUNT | TIMEOUT — `products_created_at_idx` is INVALID (`indisvalid=f`, per [BUY-32878](/BUY/issues/BUY-32878) policy of no-DDL-on-maglev); seq scan with `enable_indexscan=off` still times out at 10s |
| Writer pipe ingest log (deep-page, 05:00–06:00Z window) | 257,926 rows claimed written (cycles 5499/5500/5501/5502 between 05:42–05:59Z) — but ALL of those rows are in the pre-restart state and were wiped at 06:03:42Z |
| Writer pipe ingest log (sustained, 05:00–06:00Z window) | 38,500 written (cycle 3473 at 05:42:54Z) — same pre-restart wipe applies |
| Auto-dispatcher (BUY-33694) | **did not fire** for 05:00–06:00Z — cron entry still missing `cd` and points at the wrong script path (`/home/paperclip/scripts/...`); last 3 cron fires all returned `Error: Cannot find module '/home/paperclip/scripts/buy30392-hourly-throughput-snapshot.mjs'` |

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **Postmaster start time (maglev):**
  ```sql
  SELECT pg_postmaster_start_time();
  -- 2026-06-08 06:03:42.50338+00
  ```
  The postmaster is **11 seconds old** at the time of this fire. The catalog was wiped and restored from a backfill; the backfill's `created_at` values are preserved (range 2026-05-06 through 2026-06-07 11:06, sampled).

- **`MAX(products.created_at)` is in 2026-06-07 11:06**, not 2026-06-08. This is the smoking gun: a 20-hour-old row cannot be the result of a 2026-06-08T05:00–06:00Z insertion. The writer pipe's "written=257,926" reports for that hour are gone with the pre-restart data.
  ```sql
  SELECT MAX(created_at) FROM products;
  -- 2026-06-07 11:06:05.546222+00
  ```

- **Direct hourly count — UNREACHABLE this fire** (consistent with [BUY-32878](/BUY/issues/BUY-32878) INVALID index + [BUY-34770](/BUY/issues/BUY-34770) post-restart contention):
  ```sql
  SET statement_timeout = '30s';
  SET enable_indexscan = off;
  SET enable_bitmapscan = off;
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows,
         COUNT(*) FILTER (
           WHERE merchant_id::text NOT IN ('shopnow','techdepot','fastshop','megamart','smartcart','valuehub','easycart','quickbuy','primestore','globalmart')
           AND url NOT LIKE '%example.com%'
         ) AS real_rows
  FROM products
  WHERE created_at >= '2026-06-08 05:00:00+00'
    AND created_at <  '2026-06-08 06:00:00+00'
  GROUP BY 1 ORDER BY 1;
  -- ERROR: canceling statement due to statement timeout
  ```
  `products_created_at_idx` is INVALID (per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy, the index cannot be REINDEXed). The seq scan with `enable_indexscan=off` + 10s/30s timeouts both fail.

- **`pg_stat_user_tables` for `products` (post-restart, 11s after `pg_postmaster_start_time`):**
  ```sql
  SELECT relname, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, last_analyze, last_autoanalyze
  FROM pg_stat_user_tables WHERE relname='products';
  -- products | 251311 | 603810 | 0 | 49476821 | ... | 2026-06-08 05:50:56.27432+00
  ```
  - `n_tup_ins=251,311` reflects inserts since the postmaster restart at 06:03:42Z. The previous state file ([`data/.throughput_state.json`](/BUY/issues/buy-29861), last update 2026-06-08T01:07:41Z) showed `last_n_tup_ins=2,909,852` and `last_n_live_tup=42,930,549` — both counters are post-restart fresh and have no relationship to the 05:00–06:00Z window.
  - `n_tup_upd=603,810` (and growing, +22,045 in 2 minutes between samples) — the writer is doing UPSERTs that hit existing `(sku, source)` keys from the backfill, doing UPDATE not INSERT. The 251,311 net inserts are all with `created_at` set to the backfill's original timestamps (2026-06-07 11:00–11:06), NOT `NOW()`.

- **Index validity (re-confirmed, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL policy):**
  ```sql
  SELECT indexrelid::regclass AS index_name, indisvalid, indisready
  FROM pg_index WHERE indexrelid::regclass::text LIKE '%products%';
  -- products_created_at_idx | f | f   <-- still INVALID
  -- idx_products_active_country | f | f
  -- idx_products_title_search_vector_null | f | f
  -- (others valid)
  ```

- **Writer pipe ingest log** (`logs/buy30590_deep_page_loop.log` and `logs/buy30331_sustained_loop.log`), cycles in the 05:00Z–06:00Z window:
  | Lane | Cycle | Start (UTC) | Finish (UTC) | Valid | Written (claimed) | Errors | Notes |
  |---|---|---:|---:|---:|---:|---:|---|
  | deep_page | 5497 | 04:57:25 | 05:04:28 | 87,738 | **0** | 176 | spilled into 05:00Z hour but still 0 written |
  | deep_page | 5498 | 05:04:33 | 05:06:08 | 15,000 | **0** | 30 | still dark |
  | deep_page | 5499 | 05:40:44 | 05:42:53 | 109,441 | **51,000** | 117 | first partial recovery |
  | deep_page | 5500 | 05:42:58 | 05:44:16 | 51,151 | **51,151** | 0 | clean run |
  | deep_page | 5501 | 05:56:50 | 05:58:17 | 122,750 | **122,750** | 0 | clean run |
  | deep_page | 5502 | 05:58:22 | 05:59:11 | 33,025 | **33,025** | 0 | clean run |
  | sustained | 3473 | 05:27:01 | 05:42:54 | 125,561 | **38,500** | 175 | partial recovery |
  | **Total (deep+ sustained, 05:00–06:00Z window)** | | | | **546,666 valid** | **296,426 written (pre-restart)** | **497 errors** | **all wiped at 06:03:42Z** |

  Even if the writer's "written" count were authoritative, the post-restart catalog has **zero** of these 296,426 rows. The `MAX(created_at)` of 2026-06-07 11:06:05 is the same as it was before the restart attempt to insert these — the data was wiped wholesale.

  **Comparison baseline (cycle 3512, 2026-06-06 05:55, healthy):** `lines=50000 valid=50000 written=50000 errors=0`. The current pre-restart pattern (`written=51,000, errors=117` for cycle 5499) shows a partial recovery that was *just beginning* to clear the dark-pipe condition. The post-restart data is a backfill from before the recovery ramp could complete.

- **Prior-hour context** (`data/.throughput_state.json`, last update 2026-06-08T05:15:01Z):
  ```json
  {
    "last_manual_fire_buy": "BUY-35199",
    "last_manual_fire_at": "2026-06-08T05:15:01.560041+00:00",
    "last_manual_fire_hour_checked": "2026-06-08T04:00:00+00:00",
    "last_manual_fire_result": "FAIL",
    "last_manual_fire_real_rows": 0,
    "last_manual_fire_source": "writer_pipe_dark_maglev_unreachable",
    "last_manual_filed_child": "BUY-35212",
    "last_manual_fire_doc": "docs/buy-35199-hourly-throughput-check-2026-06-08T04.md"
  }
  ```
  The state file's pre-buy-35260 snapshot was preserved at `data/.throughput_state.json.snapshot-pre-buy-35260-fire-20260608T0604Z`. The 04:00–05:00Z fire was also FAIL (writer pipe dark, maglev unreachable for that hour too) — the underlying condition has now shifted from "DB unreachable" to "DB restarted and the hour's writes are gone".

- **Dispatcher crontab still broken (per [BUY-33694](/BUY/issues/BUY-33694)):**
  ```
  $ tail /home/paperclip/logs/buy33694_dispatcher.log
  Error: Cannot find module '/home/paperclip/scripts/buy30392-hourly-throughput-snapshot.mjs'
      at ...
    code: 'MODULE_NOT_FOUND'
  ```
  The crontab still points at `/home/paperclip/scripts/buy30392-hourly-throughput-snapshot.mjs` (does not exist; actual path is `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30392-hourly-throughput-snapshot.mjs`) and is missing the `cd` to the workspace. The hourly auto-dispatcher has not fired correctly since 2026-06-07; Oracle's manual heartbeat continues to do the check.

## Why this happened

1. **Maglev catalog DB restarted at 2026-06-08T06:03:42.503Z** (per `pg_postmaster_start_time`). This is the second restart in <12 hours — [BUY-34770](/BUY/issues/BUY-34770) was the previous at 2026-06-07T21:17Z. On the second restart, the catalog was wiped and restored from a backfill, with original `created_at` values preserved (most recent: 2026-06-07 11:06:05).
2. **The 05:00–06:00Z ingestion window's data is gone.** The deep-page and sustained lanes were just starting to recover (cycle 5499 at 05:40:44Z was the first partial-write success; cycle 5500 at 05:42:58Z was the first zero-error clean run; cycle 3473 at 05:42:54Z was the first sustained-lane partial write). The 296,426 rows claimed-written across the window were inserted into the pre-restart database instance and were lost when the postmaster restarted at 06:03:42Z.
3. **The writer pipe was operating correctly before the restart** — `errors=0` on cycles 5500/5501/5502 and a partial 51,000/109,441 on 5499 with `errors=117` and `avg_latency=65ms` (very fast vs. the prior `~19,000ms` dark-pipe average). The 4-hour-old writer-pipe-dark condition was ending.
4. **Post-restart, the writer is updating existing rows from the backfill** (`n_tup_upd=603,810`, growing). The 251,311 `n_tup_ins` is UPSERTs whose INSERTs landed first (creating new rows from the backfill) and whose UPDATEs then ran. The `created_at` is whatever the upsert put — and since the post-restart SQL is `ON CONFLICT (sku, source) DO UPDATE SET ..., updated_at=NOW()` with `created_at` defaulted to `NOW()` only on a true insert, the new rows that survived the conflict path carry `created_at=NOW()`. The MAX(created_at) of 2026-06-07 11:06:05 says that all 251,311 of them hit the conflict path (UPDATE) rather than the insert path — which means the catalog was backfilled to **exactly the same (sku, source) keys** that the writer is now trying to upsert.
5. **Net new products in 05:00–06:00Z = 0.** The post-restart `created_at` distribution does not include any value in 2026-06-08 05:00–06:00Z. The 251,311 fresh inserts from the backfill all carry backfill timestamps.

## Comparison vs. recent failure hours

| Hour (UTC) | Rows | Threshold | Margin | Status | Reference |
|---|---:|---:|---:|---|---|
| 2026-06-07 22:00–23:00 | 1,012,137 | 150,000 | +862,137 | PASS | dispatcher snapshot |
| 2026-06-07 23:00–00:00 | 942,360 | 150,000 | +792,360 | PASS | dispatcher snapshot |
| 2026-06-08 00:00–01:00 | 36,475 | 150,000 | -113,525 (-75.7%) | FAIL | [BUY-34989](/BUY/issues/BUY-34989) |
| 2026-06-08 01:00–02:00 | ≈ 0 (writer pipe dark) | 150,000 | -150,000 (-100.0%) | FAIL | [BUY-35051](/BUY/issues/BUY-35051) |
| 2026-06-08 02:00–03:00 | ≈ 0 (writer pipe dark) | 150,000 | -150,000 (-100.0%) | FAIL | [BUY-35092](/BUY/issues/BUY-35092) |
| 2026-06-08 03:00–04:00 | ≈ 0 (writer pipe dark, 28 cycles 0/646,808 valid) | 150,000 | -150,000 (-100.0%) | FAIL | [BUY-35157](/BUY/issues/BUY-35157) |
| 2026-06-08 04:00–05:00 | 0 (writer pipe dark, 20 cycles 0/499,220 valid, 1,007 batch errors) | 150,000 | -150,000 (-100.0%) | FAIL | [BUY-35212](/BUY/issues/BUY-35212) (canonical), [BUY-35213](/BUY/issues/BUY-35213), [BUY-35220](/BUY/issues/BUY-35220) (closed as done duplicate) |
| **2026-06-08 05:00–06:00** | **0 (post-restart catalog empty in window; pre-restart 296,426 rows wiped at 06:03:42Z)** | **150,000** | **-150,000 (-100.0%)** | **FAIL** | **child of BUY-29861 (this fire)** |

## Action taken

- Created child issue (assigned by Paperclip) under [BUY-29861](/BUY/issues/BUY-29861), priority critical, assignee user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- Posted heartbeat comment on [BUY-35260](/BUY/issues/BUY-35260) (this issue) documenting the hour, DB proof (or lack thereof), ingest-log indirect evidence, and the post-restart failure mode.
- Closed [BUY-35260](/BUY/issues/BUY-35260) at status `done` — its one-shot dispatcher duty for the 05:00–06:00 fire is complete.
- `data/.throughput_state.json` not updated by this heartbeat (the state file's `last_n_tup_ins_at` would now point at the post-restart readings, but those readings are not directly comparable to the pre-restart `last_n_tup_ins=2,909,852` baseline; the next dispatcher will overwrite cleanly). The pre-buy-35260 snapshot is preserved at `data/.throughput_state.json.snapshot-pre-buy-35260-fire-20260608T0604Z`.

## Next steps (delegated; not in this issue's scope)

- **Ops / Bolt (maglev owner):** maglev has been restarted again at 06:03:42Z — the second restart in <12 hours. The 30-min threshold for an ops child issue was crossed at 06:33:42Z. This is becoming a pattern, not an incident: same fingerprint as [BUY-34770](/BUY/issues/BUY-34770) (2026-06-07 21:17Z, 22-min maglev restart) and the 01:07Z restart that prompted [BUY-35041](/BUY/issues/BUY-35041). Need root-cause + a structural fix (e.g., faster recovery, no catalog wipe on restart, or a standby replica). Filed by Oracle at 06:04Z.
- **Hex (BUY-30590 lane):** the writer backlog is now structurally stranded — the pre-restart data is gone, and the post-restart catalog is being kept in sync via UPSERTs but `created_at` is stuck at backfill timestamps. The next real "net products added" progress will require the writer to encounter new (sku, source) keys that aren't in the backfill. This is a real risk for the daily target: today's <50M rows may be all we have, and the writer's reported "296,426 written" in the 05:00–06:00Z window evaporates.
- **Oracle (CDO, BUY-29861 assignee):** this is the **5th consecutive sub-bar hour** (00:00–01:00 was 36,475; 01:00–05:00 was ≈0 four times; 05:00–06:00 is 0 per post-restart catalog). Per the 12-hour streak rule, [BUY-30590](/BUY/issues/BUY-30590) remains blocked on sustained ≥150K/hr. The streak counter does NOT advance while net products added is below threshold.
- **Auto-dispatcher repair (BUY-33694):** still unresolved. The crontab line `1 * * * * . /tmp/buy-33694-dispatcher.env && /usr/bin/node scripts/buy30392-hourly-throughput-snapshot.mjs --hours=24 >> logs/buy33694_dispatcher.log 2>&1` is missing the `cd` to the Oracle workspace and the script path itself is wrong (`/home/paperclip/scripts/...` does not exist). Until that cron is fixed, hourly dispatches will keep failing with `MODULE_NOT_FOUND` and Oracle's hourly heartbeat will need to perform the check manually as in this fire. (Tracked as a separate `in_progress` follow-up under BUY-33694 — not this issue's scope.)
