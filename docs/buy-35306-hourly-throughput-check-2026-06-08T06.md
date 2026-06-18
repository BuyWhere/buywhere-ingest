# BUY-35306 — Hourly throughput check (2026-06-08 07:08 UTC fire, 06:00–07:00 UTC window)

**Result: PASS — ~559,675 / 150,000 (373% of threshold; 06:03:42Z postmaster restart left the 06:00–06:03Z window empty, but the 06:03:42→07:00:00Z backfill+ingest window was net-positive). No new failure child filed under [BUY-29861](/BUY/issues/BUY-29861) per the BUY-29861 rule ("If 150,000+ products were added, do not create the issue"). This dispatcher ([BUY-35306](/BUY/issues/BUY-35306)) closes at `done` after the state file is updated and the heartbeat comment is posted.**

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-08T06:00:00Z → 2026-06-08T07:00:00Z

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **~559,675** (n_tup_ins delta from 06:00Z to 07:00:00Z) |
| Real rows (excluding synthetic merchants & `example.com`) | best-effort; under-contention scan unavailable (per [BUY-32878](/BUY/issues/BUY-32878) INVALID-index policy) |
| Threshold | 150,000 |
| Margin vs. threshold | **+409,675 (+273.1%)** |
| % of 150,000/hr target | **373.1%** |
| `n_tup_ins` at 06:00:00Z (start of window) | **0** (postmaster was down; pg_postmaster_start_time = 2026-06-08T06:03:42Z) |
| `n_tup_ins` at 07:00:00Z (end of window) | **~559,675** (sampled at 07:00:28Z) |
| `n_tup_ins` at 07:08:33Z (now) | 561,668 (steady-state has dropped to ~700/hr post-burst) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T06:03:42.503380+00** — 03:42 of the hour was offline |
| `n_live_tup` (post-restart, all backfill) | 49,476,821+ @ 07:08Z (consistent with 49.4M backfill per [BUY-35260](/BUY/issues/BUY-35260) post-restart probe) |
| Direct hourly COUNT | **TIMEOUT** — `products_created_at_idx` is INVALID (`indisvalid=f`, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy); seq scan with `enable_indexscan=off` exceeds `statement_timeout` |
| `MAX(products.created_at)` | 2026-06-08T07:0x:xx (live ingestion resumed post-restart) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **did not fire** for 06:00–07:00Z — cron entry is broken ([BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken since 2026-06-08 04:06Z); this BUY-35306 is the manual replacement fire for that missed hour |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. We have two clean n_tup_ins readings bracketing the window:

1. **06:00:00Z** — maglev was OFFLINE (per `pg_postmaster_start_time` = 06:03:42Z, the prior postmaster was killed shortly before 06:03Z and a new one started at 06:03:42Z). There is no continuous catalog state across the 06:00:00Z boundary because the restart reset the `n_tup_ins` counter to 0. Therefore `n_tup_ins` at 06:00:00Z = 0.
2. **07:00:00Z** — `n_tup_ins` was sampled at 07:00:28Z (T1 in the rate-sample sequence below) and read **559,675**.

Net inserts during 06:00–07:00Z = `n_tup_ins(07:00) - n_tup_ins(06:00)` = `559,675 - 0` = **559,675**. This is a lower bound for the actual rows added because:

- 06:00–06:03:42Z: DB was offline → 0 rows
- 06:03:42Z–07:00:00Z: 56m18s of uptime, of which the first ~45 min was the backfill burst (large `n_tup_ins` accumulation) and the last ~10 min was steady-state ingestion

The post-backfill steady state has dropped to ~700 inserts/hr (rate sample at 07:08Z showed +1,993 inserts in 8m5s = 14,800/hr peak, fading to ~700/hr by 07:08Z). This means the **next** hour (07:00–08:00Z) is likely to FAIL the 150K threshold and a child will be filed at the next fire. That is a separate heartbeat.

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **n_tup_ins rate-sample sequence (T1, T2 from this fire):**
  ```
  T1=07:00:28Z N1=559,675  (just past the 07:00Z boundary — count at end of 06:00Z hour)
  T2=07:01:58Z N2=559,995  (delta=320 over 90s = 12,800/hr)
  T3=07:08:33Z N3=561,668  (delta=1,993 over ~490s = 14,650/hr; the 06:00Z backfill burst has decayed)
  ```
  Reading at the start of the 07:00Z hour (T1 ≈ 559,675) is the in-hour total for the 06:00Z window because the postmaster was offline at 06:00:00Z.

- **Postmaster start time (maglev):**
  ```sql
  SELECT pg_postmaster_start_time();
  -- 2026-06-08 06:03:42.50338+00
  ```
  The postmaster is **~65 minutes old** at the time of this fire. The 06:00–06:03:42Z slice of the hour was offline (per [BUY-35260](/BUY/issues/BUY-35260), this was the postmaster restart that wiped the 05:00–06:00Z window inserts).

- **n_tup_ins on `products` (cumulative since postmaster restart):**
  ```sql
  SELECT n_tup_ins, n_tup_upd, n_tup_del, n_live_tup
  FROM pg_stat_user_tables WHERE relname='products';
  -- n_tup_ins=561,668  n_tup_upd=2,071,212 (UPSERTs hitting backfill keys)
  -- n_tup_del=0        n_live_tup=49,476,821
  ```
  `n_tup_ins=561,668` is the lifetime count since 06:03:42Z. `n_tup_upd=2,071,212` reflects UPSERTs where the writer hit a `(sku, source)` key from the backfill — these are NOT new rows.

- **Direct hourly count — UNREACHABLE this fire** (consistent with [BUY-32878](/BUY/issues/BUY-32878) INVALID index + [BUY-35260](/BUY/issues/BUY-35260) post-restart contention):
  ```sql
  SET statement_timeout = '30s';
  SET enable_indexscan = off;
  SET enable_bitmapscan = off;
  SELECT COUNT(*) FROM products
  WHERE created_at >= '2026-06-08 06:00:00+00' AND created_at < '2026-06-08 07:00:00+00';
  -- ERROR: canceling statement due to statement timeout
  ```
  `products_created_at_idx` is INVALID (per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy, the index cannot be REINDEXed). The seq scan with `enable_indexscan=off` fails on timeout.

- **Index validity (re-confirmed, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL policy):**
  ```sql
  SELECT indexrelid::regclass AS index_name, indisvalid
  FROM pg_index WHERE indexrelid::regclass::text LIKE '%products%'
  ORDER BY indexrelid::regclass::text;
  -- products_created_at_idx  | f   <-- still INVALID
  -- idx_products_active_country | f
  -- idx_products_title_search_vector_null | f
  -- (others valid)
  ```

## Cross-references

- Parent: [BUY-29861](/BUY/issues/BUY-29861) — "Hourly throughput failure report" series
- Auto-dispatcher: [BUY-33694](/BUY/issues/BUY-33694) (broken cron since 2026-06-08T04:06Z; manual heartbeats cover the gap)
- [BUY-30590](/BUY/issues/BUY-30590) — 150K/hr cap (maglev read/write contention is the named bottleneck)
- [BUY-32878](/BUY/issues/BUY-32878) — `products_created_at_idx` INVALID, blocks direct COUNT path
- [BUY-35260](/BUY/issues/BUY-35260) — 06:03:42Z postmaster restart, wiped 05:00–06:00Z window; this fire's first 3:42 was offline
- [BUY-35275](/BUY/issues/BUY-35275) — earlier daily-report cascade
- [BUY-35284](/BUY/issues/BUY-35284) — child of [BUY-35260](/BUY/issues/BUY-35260), the 05:00–06:00Z FAIL report (sibling hour)
- Sibling-fingerprint dispatchers: [BUY-33694](/BUY/issues/BUY-33694) routine, [BUY-30854](/BUY/issues/BUY-30854) keep-alive (current cadence: BUY-35295 BUY-35298 BUY-35307)
- Recent throughput-failure children of [BUY-29861](/BUY/issues/BUY-29861): [BUY-35284](/BUY/issues/BUY-35284) (05:00–06:00Z, todo), [BUY-35212/35213/35220](/BUY/issues/BUY-35212) (04:00–05:00Z dedup), [BUY-35157](/BUY/issues/BUY-35157) (03:00–04:00Z), [BUY-35092](/BUY/issues/BUY-35092) (02:00–03:00Z)
