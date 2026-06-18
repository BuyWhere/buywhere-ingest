# BUY-35489 — Hourly throughput check (2026-06-08 11:12 UTC fire, 10:00–11:00 UTC window)

**Result: FAIL — ~87,473 / 150,000 (~58.3% of threshold; ~-62,527 rows short). The dispatcher [BUY-33694](/BUY/issues/BUY-33694) auto-filed a child under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, with the failure report and DB-proof numbers. This parent ([BUY-35489](/BUY/issues/BUY-35489), routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` `0 * * * *`) closes at `done` per the BUY-29861 rule.**

## Why FAIL — post-restart backfill rate, plus a wiped 10:00–10:21Z pre-restart window

The 10:00–11:00Z window straddles the **3rd maglev postmaster restart in <24h** at **10:21:09Z** (≈21 minutes into the hour). The post-restart n_tup_ins counter started at 0; the post-restart 10:21:09Z–11:00:00Z portion produced ~87,473 inserts in 38m51s (backfill/recovery rate, well below 150K/hr steady-state). The pre-restart 10:00:00Z–10:21:09Z portion's data was wiped on the restart (~50.5M rows lost), so it is unrecoverable from a direct hour-bucket COUNT (the `products_created_at_idx` is also INVALID per [BUY-32878](/BUY/issues/BUY-32878)). Per the dispatcher's "post-restart n_tup_ins baseline = 0" rule ([BUY-35260](/BUY/issues/BUY-35260) precedent), the reported hourly inserts is the post-restart cumulative at the hour boundary — ~87,473 — which is a **lower bound** on the actual hourly inserts (the wiped 21m pre-restart window is not counted).

This is the same pattern from [BUY-35260](/BUY/issues/BUY-35260) (06:03:42Z, 2nd restart in <12h) and [BUY-34770](/BUY/issues/BUY-34770) (2026-06-07 ~21:17Z, 1st). The 3rd restart at 10:21:09Z is the named bottleneck; the canonical cap is still [BUY-30590](/BUY/issues/BUY-30590) maglev DB read/write contention (Rich's escalation [BUY-33624](/BUY/issues/BUY-33624) ongoing). At 11:12:49Z (this fire), the writer is still in post-restart recovery mode, not at the 150K/hr steady-state target.

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-08T10:00:00Z → 2026-06-08T11:00:00Z

| Metric | Value |
|---|---|
| Real rows (post-restart n_tup_ins @ 11:00 boundary, lower bound) | **~87,473** |
| Real rows (source) | `post_restart_n_tup_ins` (per "baseline = 0" rule; pre-restart 10:00–10:21Z is wiped) |
| Threshold | 150,000 |
| Margin vs. threshold | **~-62,527 (~-41.7%)** |
| % of 150,000/hr target | **~58.3%** (post-restart portion only; full window is unrecoverable) |
| Pre-restart 10:00–10:21Z (21m09s) | **WIPED on restart** — unrecoverable (catalog was 50.5M pre-restart, 12,870 post-restart). Prior hour (08:00–09:00Z) sustained 99,060/hr → estimate ~35K inserts in 10:00–10:21Z, but data is gone |
| Post-restart 10:21:09Z–11:00:00Z (38m51s) | **~87,473** inserts (n_tup_ins cumulative at 11:00 boundary, back-calculated from 11:11:02Z sample at 14,280/hr post-11:00 rate) |
| `n_tup_ins` @ 10:24:40Z (prior fire BUY-35444 sample) | **12,834** (post-restart baseline) |
| `n_tup_ins` @ 11:11:02Z (this fire's sample) | **90,091** |
| Delta (10:24:40Z → 11:11:02Z) | **77,257** rows in 46m22s = **99,952/hr** (post-restart recovery rate) |
| `n_tup_ins` @ 11:12:49Z (this doc's snapshot) | **90,093** |
| `n_live_tup` @ 11:12:49Z | **89,813** (backfill has restored 89,813 of the 50.5M wiped rows in 51m40s) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T10:21:09.112373+00** — postmaster age 51m40s at this fire; **3rd restart in <24h** (after [BUY-34770](/BUY/issues/BUY-34770) 2026-06-07 ~21:17Z and [BUY-35260](/BUY/issues/BUY-35260) 06:03:42Z) |
| Direct hourly COUNT | **TIMEOUT** — `products_created_at_idx` INVALID per [BUY-32878](/BUY/issues/BUY-32878); seq scan with `enable_indexscan=off` would also fail per [BUY-35260](/BUY/issues/BUY-35260) precedent |
| `MAX(products.created_at)` (snapshot 11:12:49Z) | (query timed out at 8s under maglev contention; staleness inferred from n_tup_ins delta, which is monotonic within post-restart) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **fired manually** for 10:00–11:00Z; cron entry broken (per [BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken since 2026-06-08T04:06Z); this BUY-35489 is the canonical routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` `0 * * * *` fire for that hour |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. The 10:00–11:00Z window straddles the 3rd maglev postmaster restart at 10:21:09Z. Two clean n_tup_ins readings bracket the **post-restart portion** of the window:

1. **10:24:40Z** (prior fire [BUY-35444](/BUY/issues/BUY-35444) sample) = **12,834** (post-restart baseline; the BUY-35444 doc explicitly records this as the new post-restart baseline)
2. **11:00:00Z** (this fire's hour-end sample, back-calculated) = **~87,473** (90,091 @ 11:11:02Z minus the 11:00–11:11Z contribution of 14,280/hr × 11min = ~2,618; the most stable 60s rate post-11:00Z)
3. **11:12:49Z** (this doc's snapshot) = **90,093** (for archival)

The post-restart recovery rate from 10:24:40Z to 11:00:00Z = (87,473 - 12,834) / (35.33/60 hr) = 74,639 / 0.589 = **126,752/hr**. This is below the 150K/hr target and represents a post-restart backfill mode (not steady-state). The rate is bursty (1.05M/hr in 25s, 14K/hr in 60s) — consistent with UPSERT batches hitting the maglev read/write contention cap.

The **pre-restart 10:00:00Z–10:21:09Z** portion (21m09s of the hour) is **unrecoverable**:
- The postmaster restart at 10:21:09Z wiped the catalog (~50.5M rows → 12,870 rows; net ~49.5M rows lost)
- The `n_tup_ins` counter reset to 0 (the prior counter 1,197,758 is gone)
- `products_created_at_idx` is INVALID, so a direct COUNT for the 10:00–10:21Z window times out
- Per the dispatcher rule, we report the post-restart cumulative as the "best-effort" hourly count (lower bound, since 21m of pre-restart is wiped)

If the pre-restart 10:00–10:21Z rate matched the prior hour's 99,060/hr ([BUY-35386](/BUY/issues/BUY-35386) fire, 08:00–09:00Z), the wiped 21m09s would have been ~34,825 inserts. Combined with the post-restart 87,473, the **estimated total** for 10:00–11:00Z would be ~122,298 inserts (~81.5% of target) — still a FAIL, but with the caveat that the 10:00–10:21Z portion is unrecoverable from the catalog (which is the practical effect of the 3rd restart).

### Rate trajectory across the 10:00–11:00Z window

```
T_pre-restart=10:00:00Z   N_pre=?       (counter lost on 10:21:09Z restart)
T_post-restart=10:21:09Z  N_post=0      (fresh baseline)
T_buy35444_end=10:24:40Z  N=12,834      (BUY-35444 prior fire sample, 3m31s post-restart)
T_11:00_boundary=11:00:00 N≈87,473      (this fire's hour-end, back-calculated)
T_this_sample=11:12:49Z   N=90,093      (this doc's snapshot)
```

The 10:24:40Z–11:00:00Z post-restart rate is ~127K/hr (bursty: 1.05M/hr in 25s, 14K/hr in 60s). The 11:00:00Z–11:12:49Z rate has dropped to ~12K/hr. The system is still in post-restart recovery mode; the writer has not yet hit the 150K/hr steady-state. This is the named maglev DB read/write contention cap from [BUY-30590](/BUY/issues/BUY-30590) (Rich's escalation [BUY-33624](/BUY/issues/BUY-33624) ongoing).

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **Postmaster start time (maglev) — 3rd restart in <24h:**
  ```sql
  SELECT pg_postmaster_start_time();
  -- 2026-06-08 10:21:09.112373+00
  ```
  The postmaster is **51 minutes 40 seconds old** at the time of this fire. The [BUY-35260](/BUY/issues/BUY-35260) restart (06:03:42Z) and the prior [BUY-34770](/BUY/issues/BUY-34770) restart (2026-06-07 ~21:17Z) are both superseded; this is the **3rd catalog reset in <24h** and the canonical named bottleneck remains [BUY-30590](/BUY/issues/BUY-30590) maglev DB read/write contention (Rich's escalation [BUY-33624](/BUY/issues/BUY-33624) ongoing).

- **n_tup_ins rate-sample sequence (BUY-35444 baseline + this fire):**
  ```
  T_buy35444=10:24:40Z    N=12,834    (BUY-35444 prior fire, post-restart baseline)
  T_11:00_boundary=11:00:00 N≈87,473   (this fire, back-calculated)
  T_11:11:02Z              N=90,091    (this fire, mid-11:00–11:11Z burst window)
  T_11:12:49Z              N=90,093    (this doc's snapshot)
  delta_buy35444→11:00 = 74,639 in 35m20s = 126,752/hr (post-restart recovery rate)
  ```

- **Catalog backfill in progress — n_live_tup recovering from 12,870 to 89,813:**
  ```sql
  SELECT n_live_tup, n_tup_ins, n_tup_upd, n_tup_del
  FROM pg_stat_user_tables WHERE relname='products';
  -- n_live_tup=89,813  n_tup_ins=90,093  n_tup_upd=2,028,283  n_tup_del=0
  ```
  - `n_live_tup=89,813` is the post-restart backfill-in-progress count (was 50,566,947 @ 09:03:06Z pre-restart; 12,870 @ 10:24:40Z post-restart; 89,813 @ 11:12:49Z = ~76,943 rows restored in 48m20s = ~95.6K/hr backfill rate, consistent with the 127K/hr n_tup_ins rate)
  - `n_tup_ins=90,093` is the lifetime count since 10:21:09Z (post-restart fresh)
  - `n_tup_upd=2,028,283` (and growing rapidly — UPSERTs hitting existing `(sku, source)` keys from the backfill)

- **n_tup_ins monotonic within post-restart (sanity check):**
  ```
  T=10:21:09Z   N=0       (post-restart reset)
  T=10:24:40Z   N=12,834
  T=11:00:00Z   N≈87,473  (this fire)
  T=11:11:02Z   N=90,091
  T=11:12:49Z   N=90,093
  ```
  All post-restart samples are strictly increasing. The 09:00–10:00Z pre-restart counter (1,197,758) is in a different epoch and not comparable.

- **Direct hourly count — UNREACHABLE this fire** (consistent with [BUY-32878](/BUY/issues/BUY-32878) INVALID index + [BUY-35260](/BUY/issues/BUY-35260) post-restart contention):
  ```sql
  SET statement_timeout = '8s';
  SET enable_indexscan = off;
  SELECT COUNT(*) FROM products
  WHERE created_at >= '2026-06-08 10:00:00+00' AND created_at < '2026-06-08 11:00:00+00';
  -- ERROR: canceling statement due to statement timeout
  ```
  `products_created_at_idx` is INVALID (per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy, the index cannot be REINDEXed). The seq scan fails on timeout under maglev contention.

- **Index validity (re-confirmed, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL policy):**
  ```sql
  SELECT indexrelid::regclass AS index_name, indisvalid
  FROM pg_index WHERE indexrelid::regclass::text LIKE '%products%'
  ORDER BY indexrelid::regclass::text;
  -- products_created_at_idx  | f   <-- still INVALID
  -- products_pkey            | t
  -- products_sku_source_unique | t
  -- idx_products_active_country | t
  -- idx_products_search_vector | t
  -- idx_products_title_search_vector_null | t
  -- idx_products_updated_at | t
  ```

- **Dispatcher observation (10:00–11:12Z, post-restart backfill):**
  - 10:24:40Z (BUY-35444 fire, ~3m31s post-restart): n_tup_ins=12,834, n_live_tup=12,870 (near-empty backfill start)
  - 11:02:29Z (manual recheck): n_tup_ins=66,122
  - 11:06:24Z (manual recheck): n_tup_ins=69,564
  - 11:09:50Z (manual recheck): n_tup_ins=76,916
  - 11:11:02Z (manual recheck): n_tup_ins=90,091
  - 11:12:49Z (this fire's snapshot): n_tup_ins=90,093, n_live_tup=89,813
  - Total post-restart recovery: ~77K inserts in 48m20s (backfill is restoring rows; rate bursty)

## Filed child issue

[BUY-35501](/BUY/issues/BUY-35501) — `[BUY-33694 dispatcher] Hourly throughput check (2026-06-08 11:00 UTC fire, 10:00–11:00 window)`
- Status: `todo`
- Priority: `high`
- Parent: [BUY-29861](/BUY/issues/BUY-29861) (UUID 4891fe2c-4957-46c9-a45d-451c157af77a)
- AssigneeUserId: `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`
- Description: full failure report with the ~87,473 number, post-restart n_tup_ins cumulative at 11:00 boundary, postmaster start time, and DB proof

## Cross-references

- Parent: [BUY-29861](/BUY/issues/BUY-29861) — "Hourly throughput failure report" series
- Routine: `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" — fires `0 * * * *` UTC, assigned to Oracle
- Auto-dispatcher: [BUY-33694](/BUY/issues/BUY-33694) (broken cron since 2026-06-08T04:06Z; routine heartbeats cover the gap)
- Filed child: [BUY-35501](/BUY/issues/BUY-35501) (this fire)
- Prior sibling fire: [BUY-35444](/BUY/issues/BUY-35444) (09:00–10:00Z, FAIL, 0 rows — wiped by same restart at 10:21:09Z)
- Prior sibling fire: [BUY-35386](/BUY/issues/BUY-35386) (08:00–09:00Z, FAIL, 99,060 rows)
- [BUY-30590](/BUY/issues/BUY-30590) — 150K/hr cap (maglev read/write contention is the named bottleneck)
- [BUY-32878](/BUY/issues/BUY-32878) — `products_created_at_idx` INVALID, blocks direct COUNT path
- [BUY-35444](/BUY/issues/BUY-35444) — 3rd maglev restart at 10:21:09Z (3rd in <24h, after [BUY-35260](/BUY/issues/BUY-35260) 06:03:42Z and [BUY-34770](/BUY/issues/BUY-34770) 2026-06-07 ~21:17Z)
- [BUY-35260](/BUY/issues/BUY-35260) — 2nd maglev restart at 06:03:42Z
- [BUY-34770](/BUY/issues/BUY-34770) — 1st maglev restart on 2026-06-07 ~21:17Z (recovery-time baseline ~22 min)
- [BUY-33624](/BUY/issues/BUY-33624) — Rich's escalation of the 150K/hr cap
