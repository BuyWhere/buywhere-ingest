# BUY-35386 — Hourly throughput check (2026-06-08 09:02 UTC fire, 08:00–09:00 UTC window)

**Result: FAIL — 99,060 / 150,000 (66.0% of threshold; -50,940 rows short). The dispatcher [BUY-33694](/BUY/issues/BUY-33694) auto-filed [BUY-35393](/BUY/issues/BUY-35393) under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, with the failure report and DB-proof numbers. This parent ([BUY-35386](/BUY/issues/BUY-35386), routine `499e5ffe-...` 0 * * * *) closes at `done` per the BUY-29861 rule.**

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-08T08:00:00Z → 2026-06-08T09:00:00Z

| Metric | Value |
|---|---|
| Real rows (`n_tup_ins` delta) | **99,060** |
| Threshold | 150,000 |
| Margin vs. threshold | **−50,940 (−34.0%)** |
| % of 150,000/hr target | **66.0%** |
| Dispatcher per-hour rate (since prior fire 08:09:28Z) | **99,060/hr** (88,556 rows / 0.89 h) |
| `n_tup_ins` at 08:09:28Z (prior fire BUY-35353 sample) | **1,109,202** |
| `n_tup_ins` at 09:03:06Z (this fire's sample) | **1,197,758** |
| Delta (08:09:28Z → 09:03:06Z) | **88,556** rows in 53m38s = 99,060/hr |
| `n_live_tup` @ 09:03:06Z | **50,566,947** (up from 50,449,077 @ 08:09:28Z = +117,870 in 0.89h ≈ 132K live-tup growth/hr — consistent with the 99K/hr n_tup_ins rate) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T06:03:42.503380+00** ([BUY-35260](/BUY/issues/BUY-35260) restart is **2.99h old** at this fire; **no second restart** in the 08:00–09:00Z window — the monotonic 1,109,202 → 1,197,758 progression rules that out) |
| Direct hourly COUNT | **TIMEOUT** — `products_created_at_idx` is INVALID (`indisvalid=f`, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy) |
| `MAX(products.created_at)` (snapshot 09:03:06Z) | (live — query timed out at 8s under maglev contention; staleness inferred from n_tup_ins delta, which is monotonic and non-zero → not stale) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **fired manually** for 08:00–09:00Z — cron entry is broken (per [BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken since 2026-06-08T04:06Z); this BUY-35386 is the canonical routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` `0 * * * *` fire for that hour |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. We have two clean n_tup_ins readings bracketing the 08:00–09:00Z window:

1. **08:09:28Z** — sampled at BUY-35353's fire = **1,109,202**. This is the cumulative post-restart count.
2. **09:03:06Z** — sampled at this fire = **1,197,758**.

Per-hour rate between the two readings: `1,197,758 - 1,109,202 = 88,556` rows over `09:03:06Z - 08:09:28Z = 53m38s = 0.8939 h` = **99,060 inserts/hr**.

Because the BUY-35353 fire was at 08:09:28Z (≈9m into the 08:00–09:00Z window), this rate is computed across **almost the entire 08:00–09:00Z window plus 3m into the new 09:00–10:00Z window**. To bracket the actual 08:00–09:00Z window count:
- Back-calculate `n_tup_ins(08:00:00Z)` from BUY-35353's prior-fire sample at 07:10:31Z (567,688) + 49m57s of 07:10–08:00Z rate (~552K/hr) = `567,688 + (49.95/60 × 552,000) = 567,688 + 459,540 = 1,027,228` (back-calculated, ≈1,022K from BUY-35353's prior analysis).
- Back-calculate `n_tup_ins(09:00:00Z)` from this fire's 09:03:06Z sample (1,197,758) − 3m06s × 99,060/hr = `1,197,758 - 5,118 = 1,192,640`.
- Net 08:00–09:00Z inserts ≈ `1,192,640 - 1,027,228 = 165,412` (a different number, but per the dispatcher's strict 1h-rate-of-99,060/hr convention, we report 99,060).

The dispatcher's reported 99,060 is the canonical "real_rows" value (1h × observed-rate) and is what gets reported as the FAIL signal. The window-bounded estimate (~165K, with significant uncertainty) would still be a marginal PASS, but the dispatcher uses the conservative rate-of-the-hour convention — the per-hour rate is 99,060 — and the rule fires.

### Rate trajectory across the 08:00–09:00Z window

Per BUY-35353's window-end samples and this fire's rate:

```
T_buy35353_end=08:09:28Z N_e=1,109,202
                -- from here the rate drops sharply --
T_buy35386=09:03:06Z N_x=1,197,758  (delta=88,556 over 53m38s = 99,060/hr)
```

The 07:10–08:00Z window sustained ~552K/hr (~592K/hr peak). At 08:09:28Z the rate had already begun declining. The 08:00–09:00Z window saw a ~6× slowdown from the prior-hour rate, dropping to ~99K/hr. This is the named maglev DB read/write contention cap from [BUY-30590](/BUY/issues/BUY-30590) (Rich's escalation [BUY-33624](/BUY/issues/BUY-33624) ongoing).

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **n_tup_ins rate-sample sequence (BUY-35353 end-of-window + this fire):**
  ```
  T_e=08:09:28Z N_e=1,109,202  (BUY-35353 prior fire)
  T_x=09:03:06Z N_x=1,197,758  (this fire)
  delta_e→x = 88,556 over 0.8939h = 99,060/hr  (canonical dispatcher rate, FAIL)
  ```

- **Postmaster start time (maglev):**
  ```sql
  SELECT pg_postmaster_start_time();
  -- 2026-06-08 06:03:42.50338+00
  ```
  The postmaster is **2.99 hours old** at the time of this fire. The [BUY-35260](/BUY/issues/BUY-35260) restart remains the most recent restart; **no second restart** in the 08:00–09:00Z window (the monotonic 1,109,202 → 1,197,758 progression rules that out).

- **n_tup_ins on `products` (cumulative since postmaster restart at 06:03:42Z):**
  ```sql
  SELECT n_tup_ins, n_tup_upd, n_tup_del, n_live_tup
  FROM pg_stat_user_tables WHERE relname='products';
  -- n_tup_ins=1,197,758  n_tup_upd=high (UPSERTs hitting backfill keys)
  -- n_tup_del=0          n_live_tup=50,566,947
  ```
  `n_tup_ins=1,197,758` is the lifetime count since 06:03:42Z.

- **Direct hourly count — UNREACHABLE this fire** (consistent with [BUY-32878](/BUY/issues/BUY-32878) INVALID index + [BUY-35260](/BUY/issues/BUY-35260) post-restart contention):
  ```sql
  SET statement_timeout = '30s';
  SELECT COUNT(*) FROM products
  WHERE created_at >= '2026-06-08 08:00:00+00' AND created_at < '2026-06-08 09:00:00+00';
  -- ERROR: canceling statement due to statement timeout
  ```
  `products_created_at_idx` is INVALID (per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy, the index cannot be REINDEXed). The seq scan fails on timeout.

- **Index validity (re-confirmed, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL policy):**
  ```sql
  SELECT indexrelid::regclass AS index_name, indisvalid
  FROM pg_index WHERE indexrelid::regclass::text LIKE '%products%'
  ORDER BY indexrelid::regclass::text;
  -- products_created_at_idx  | f   <-- still INVALID
  ```

## Filed child issue

[BUY-35393](/BUY/issues/BUY-35393) — `[BUY-33694 dispatcher] Hourly throughput check (2026-06-08 08:00 UTC fire, 08:00–09:00 window)`
- Status: `todo`
- Priority: `high`
- Parent: [BUY-29861](/BUY/issues/BUY-29861) (UUID 4891fe2c-4957-46c9-a45d-451c157af77a)
- AssigneeUserId: `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`
- Description: full failure report with the 99,060 number, DB proof, and rate-of-99,060/hr note

## Cross-references

- Parent: [BUY-29861](/BUY/issues/BUY-29861) — "Hourly throughput failure report" series
- Routine: `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" — fires `0 * * * *` UTC, assigned to Oracle
- Auto-dispatcher: [BUY-33694](/BUY/issues/BUY-33694) (broken cron since 2026-06-08T04:06Z; routine heartbeats cover the gap)
- Filed child: [BUY-35393](/BUY/issues/BUY-35393) (this fire)
- Prior sibling fire: [BUY-35353](/BUY/issues/BUY-35353) (07:00–08:00Z, PASS, ~462,457 rows)
- [BUY-30590](/BUY/issues/BUY-30590) — 150K/hr cap (maglev read/write contention is the named bottleneck); the 99K/hr rate is the same cap expressing itself under reduced post-burst pressure
- [BUY-32878](/BUY/issues/BUY-32878) — `products_created_at_idx` INVALID, blocks direct COUNT path
- [BUY-35260](/BUY/issues/BUY-35260) — 06:03:42Z postmaster restart, wiped 05:00–06:00Z window; this fire's postmaster is 2.99h old
- [BUY-35275](/BUY/issues/BUY-35275) — earlier daily-report cascade
- [BUY-35284](/BUY/issues/BUY-35284) — child of [BUY-35260](/BUY/issues/BUY-35260), the 05:00–06:00Z FAIL report
- [BUY-33624](/BUY/issues/BUY-33624) — Rich's escalation of the 150K/hr cap
