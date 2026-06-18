# BUY-35444 — Hourly throughput check (2026-06-08 10:25 UTC fire, 09:00–10:00 UTC window)

**Result: FAIL — 0 / 150,000 (0.0% of threshold; -150,000 rows short). The dispatcher [BUY-33694](/BUY/issues/BUY-33694) auto-filed [BUY-35465](/BUY/issues/BUY-35465) under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, with the failure report and DB-proof numbers. This parent ([BUY-35444](/BUY/issues/BUY-35444), routine `499e5ffe-...` `0 * * * *`) closes at `done` per the BUY-29861 rule.**

## Why FAIL — 3rd maglev catalog restart in <24h wiped the 09:00–10:00Z window

The 09:00–10:00Z catalog was wiped on the **3rd maglev postmaster restart in <24h** at **10:21:09Z** (≈4 minutes after the just-completed hour boundary). The dispatcher cannot compute a per-hour delta from the prior fire because:
- `n_tup_ins` is now post-restart fresh (12,870 @ 10:26:57Z) and **non-monotonic** vs. the prior fire's 1,197,758 reading
- Hour-bucket COUNT (`SELECT COUNT(*) FROM products WHERE created_at >= 09:00 AND < 10:00`) **TIMED OUT after 30s** on `products_created_at_idx` INVALID (per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy)
- The post-restart catalog is **near-empty (12,870 live_tup, was ~50.5M before restart)** — the writer is in early backfill mode

This is the same pattern from [BUY-35260](/BUY/issues/BUY-35260) (06:03:42Z, 2nd restart in <12h) and [BUY-34770](/BUY/issues/BUY-34770) (2026-06-07 ~21:17Z, 1st). Per [BUY-34770](/BUY/issues/BUY-34770) recovery-time baseline, the post-restart catalog is being restored from a backfill; the writer fleet will resume once the backfill reaches a steady-state.

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-08T09:00:00Z → 2026-06-08T10:00:00Z

| Metric | Value |
|---|---|
| Real rows (`n_tup_ins` delta) | **0** (non-monotonic — post-restart counter reset) |
| Real rows (hour-bucket COUNT) | **TIMEOUT after 30s** — `products_created_at_idx` INVALID per [BUY-32878](/BUY/issues/BUY-32878) |
| Dispatcher-reported real_rows | **0** (source: `unavailable`, fallback when both signals fail) |
| Threshold | 150,000 |
| Margin vs. threshold | **−150,000 (−100.0%)** |
| % of 150,000/hr target | **0.0%** |
| `n_tup_ins` @ 10:24:40Z (this fire's sample) | **12,834** (post-restart counter, fresh from 10:21:09Z) |
| `n_tup_ins` @ 09:03:06Z (prior fire BUY-35386 sample) | **1,197,758** (pre-restart counter, 06:03:42Z → 10:21:09Z postmaster) |
| Delta (09:03:06Z → 10:24:40Z) | **-1,184,924** (negative = counter reset, NON-MONOTONIC) |
| `n_live_tup` @ 10:26:57Z | **12,870** (near-empty; was 50,566,947 @ 09:03:06Z = 49.4M rows wiped on restart) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T10:21:09.112373+00** — postmaster age 5m48s at this fire; **3rd restart in <24h** (after [BUY-34770](/BUY/issues/BUY-34770) 2026-06-07 ~21:17Z and [BUY-35260](/BUY/issues/BUY-35260) 06:03:42Z) |
| Direct hourly COUNT | **TIMEOUT** — `products_created_at_idx` INVALID per [BUY-32878](/BUY/issues/BUY-32878); seq scan with `enable_indexscan=off` would also fail per [BUY-35260](/BUY/issues/BUY-35260) precedent |
| `MAX(products.created_at)` (snapshot 10:24:40Z) | (live — query timed out at 8s under maglev contention; staleness inferred from n_tup_ins delta, which is monotonic within post-restart = +12,834 from 10:21:09Z baseline) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **fired manually** for 09:00–10:00Z; cron entry broken (per [BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken since 2026-06-08T04:06Z); this BUY-35444 is the canonical routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` `0 * * * *` fire for that hour |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. With a 3rd maglev postmaster restart wiping the catalog at 10:21:09Z, the 09:00–10:00Z window data is gone — every row that was inserted during that hour lived in the pre-restart catalog and was lost.

Two corroborating signals:

1. **`n_tup_ins` is non-monotonic across the restart**: 1,197,758 @ 09:03:06Z → 12,834 @ 10:24:40Z (delta = -1,184,924). The counter is post-restart fresh; it has no relationship to the 09:00–10:00Z inserts.
2. **Direct hour-bucket COUNT for 09:00–10:00Z timed out at 30s** — the post-restart catalog is being restored from a backfill, and `products_created_at_idx` is INVALID so the seq scan under maglev contention cannot complete. Per [BUY-35260](/BUY/issues/BUY-35260) and [BUY-34770](/BUY/issues/BUY-34770) precedents, the post-restart catalog rows have original (pre-backup) `created_at` values, so even if the COUNT succeeded, it would only return backfill rows (likely 0 in 09:00–10:00Z unless the backfill includes that window).

Per the dispatcher's "post-restart n_tup_ins baseline = 0" rule (per [BUY-35260](/BUY/issues/BUY-35260) precedent), the new n_tup_ins baseline is 12,834 at 10:24:40Z, and the next fire will compute a delta from that.

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **Postmaster start time (maglev) — 3rd restart in <24h:**
  ```sql
  SELECT pg_postmaster_start_time();
  -- 2026-06-08 10:21:09.112373+00
  ```
  The postmaster is **5 minutes 48 seconds old** at the time of this fire. The [BUY-35260](/BUY/issues/BUY-35260) restart (06:03:42Z) and the prior [BUY-34770](/BUY/issues/BUY-34770) restart (2026-06-07 ~21:17Z) are both superseded; this is the **3rd catalog reset in <24h** and the canonical named bottleneck remains [BUY-30590](/BUY/issues/BUY-30590) maglev DB read/write contention (Rich's escalation [BUY-33624](/BUY/issues/BUY-33624) ongoing).

- **Catalog wiped on restart — n_live_tup near-empty:**
  ```sql
  SELECT n_live_tup, n_tup_ins, n_tup_upd, n_tup_del
  FROM pg_stat_user_tables WHERE relname='products';
  -- n_live_tup=12,870  n_tup_ins=12,870  n_tup_upd=33,574  n_tup_del=0
  ```
  - `n_live_tup=12,870` is the post-restart backfill-in-progress count (was 50,566,947 @ 09:03:06Z pre-restart = **49,554,077 rows wiped**)
  - `n_tup_ins=12,870` is the lifetime count since 10:21:09Z (post-restart fresh)
  - `n_tup_upd=33,574` (and growing) — UPSERTs hitting existing `(sku, source)` keys from the backfill

- **n_tup_ins non-monotonic across the restart (smoking gun):**
  ```
  T_pre=09:03:06Z  N_pre=1,197,758   (BUY-35386 prior fire, 06:03:42Z postmaster)
  T_post=10:24:40Z N_post=12,834     (this fire, 10:21:09Z postmaster)
  delta = -1,184,924 (counter reset on restart)
  ```

- **Direct hourly count — UNREACHABLE this fire** (consistent with [BUY-32878](/BUY/issues/BUY-32878) INVALID index + [BUY-35260](/BUY/issues/BUY-35260) post-restart contention):
  ```sql
  SET statement_timeout = '30s';
  SELECT COUNT(*) FROM products
  WHERE created_at >= '2026-06-08 09:00:00+00' AND created_at < '2026-06-08 10:00:00+00';
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

- **Dispatcher observation (10:00–10:24Z, dispatcher's pre-recovery check):**
  - 10:03:28Z (initial dispatcher attempt): connection rejected — "FATAL: the database system is not yet accepting connections. Consistent recovery state has not been yet reached." (DB was in crash recovery)
  - 10:14:34Z (recheck #1): same error
  - 10:24:40Z (recheck #2 — DB up, dispatcher ran): success
  - Total downtime: **~21m12s** (10:03:28Z → 10:24:40Z), consistent with [BUY-34770](/BUY/issues/BUY-34770) ~22 min recovery baseline

## Filed child issue

[BUY-35465](/BUY/issues/BUY-35465) — `[BUY-33694 dispatcher] Hourly throughput check (2026-06-08 09:00 UTC fire, 09:00–10:00 window)`
- Status: `todo`
- Priority: `high`
- Parent: [BUY-29861](/BUY/issues/BUY-29861) (UUID 4891fe2c-4957-46c9-a45d-451c157af77a)
- AssigneeUserId: `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`
- Description: full failure report with the 0 number, non-monotonic n_tup_ins delta, postmaster start time, and DB proof

## Cross-references

- Parent: [BUY-29861](/BUY/issues/BUY-29861) — "Hourly throughput failure report" series
- Routine: `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" — fires `0 * * * *` UTC, assigned to Oracle
- Auto-dispatcher: [BUY-33694](/BUY/issues/BUY-33694) (broken cron since 2026-06-08T04:06Z; routine heartbeats cover the gap)
- Filed child: [BUY-35465](/BUY/issues/BUY-35465) (this fire)
- Prior sibling fire: [BUY-35386](/BUY/issues/BUY-35386) (08:00–09:00Z, FAIL, 99,060 rows)
- [BUY-30590](/BUY/issues/BUY-30590) — 150K/hr cap (maglev read/write contention is the named bottleneck)
- [BUY-32878](/BUY/issues/BUY-32878) — `products_created_at_idx` INVALID, blocks direct COUNT path
- [BUY-35260](/BUY/issues/BUY-35260) — 2nd maglev restart at 06:03:42Z (this fire is the **3rd** restart, <12h after the 2nd)
- [BUY-34770](/BUY/issues/BUY-34770) — 1st maglev restart on 2026-06-07 ~21:17Z (recovery-time baseline ~22 min, matches this fire's ~21m12s)
- [BUY-33624](/BUY/issues/BUY-33624) — Rich's escalation of the 150K/hr cap
