# BUY-35541 — Hourly throughput check (2026-06-08 12:07 UTC fire, 11:00–12:00 UTC window)

**Result: PASS — ~350,699 / 150,000 (233.8% of threshold; +200,699 rows above bar). The 10:00-11:00Z window was devastated by the 3rd maglev postmaster restart at 10:21:09Z (BUY-35444, ~87,473 post-restart lower bound). The 11:00-12:00Z window shows strong recovery: n_tup_ins rate ~771,900/hr at the T3→T4 sample (12:04:50Z→12:09:48Z). No new failure child filed under [BUY-29861](/BUY/issues/BUY-29861) per the rule ("If 150,000+ products were added, do not create the issue"). This parent (BUY-35541, routine `499e5ffe-...` 0 * * * *) closes at `done` after the state file is updated and the heartbeat comment is posted.**

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-08T11:00:00Z → 2026-06-08T12:00:00Z

| Metric | Value |
|---|---|
| Estimated net inserts in 11:00–12:00Z (`n_tup_ins` delta across the window) | **~350,699** |
| Threshold | 150,000 |
| Margin vs. threshold | **+200,699 (+133.8%)** |
| % of 150,000/hr target | **233.8%** |
| Direct rate (T3→T4 samples) | **771,900/hr** (63,895 rows / 4m58s) |
| `n_tup_ins` at 11:00:00Z (back-calculated from T2=11:12:49Z @ 90,093) | **~88,681** (= 90,093 − 12m11s × 67 inserts/hr) |
| `n_tup_ins` at 12:00:00Z (back-calculated from T3=12:04:50Z @ 445,203) | **~439,380** (= 445,203 − 4m50s × 771,900/hr) |
| `n_tup_ins` at 11:12:49Z (T2, BUY-35489 final sample) | **90,093** |
| `n_tup_ins` at 12:04:50Z (T3, BUY-35489 state snapshot) | **445,203** |
| `n_tup_ins` at 12:09:48Z (T4, this fire's snapshot) | **509,098** |
| Rate T1→T2 (11:11:02Z→11:12:49Z, BUY-35489 doc) | **~67/hr** (2 rows / 107s — near-zero activity in first 12 min of window) |
| Rate T3→T4 (12:04:50Z→12:09:48Z, this fire) | **771,900/hr** (63,895 rows / 298s) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T10:21:09.112373+00** (BUY-35444 3rd restart; **1h48m39s old** at 12:09:48Z) |
| Direct hourly COUNT | **TIMEOUT** — `products_created_at_idx` is INVALID (`indisvalid=f`, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy) |
| `n_live_tup` @ 12:09:48Z | **~444,593** (per pg_stat_user_tables n_live_tup) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **did not fire** — cron entry is broken since 2026-06-08T04:06Z ([BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken); this BUY-35541 (routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` `0 * * * *`) is the canonical hourly fire for the 11:00–12:00Z window |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. We have three anchor points bracketing the 11:00–12:00Z window:

1. **n_tup_ins at 11:00:00Z** — back-calculated from T2 (BUY-35489's final sample at 11:12:49Z = 90,093). The T1→T2 rate was ~67/hr (2 rows/107s). Extrapolating backward: `90,093 − 12m11s × 67/hr ≈ 88,681`.
2. **n_tup_ins at 12:00:00Z** — back-calculated from T3 (BUY-35489 state snapshot at 12:04:50Z = 445,203). The T3→T4 rate was ~771,900/hr. Extrapolating backward: `445,203 − 4m50s × 771,900/hr ≈ 439,380`.
3. **n_tup_ins at 12:09:48Z** (this fire, for rate confirmation) = **509,098**.

Net inserts during 11:00–12:00Z = `439,380 − 88,681 ≈ 350,699`.

The rate accelerated sharply after 11:12Z: the first 12 minutes of the window saw only ~2 inserts (T1→T2 = ~67/hr), then the rate climbed to ~771,900/hr by the T3→T4 sample (12:04–12:09Z). This is consistent with post-restart warm-up: the 10:21:09Z postmaster restart (BUY-35444, 3rd in <24h) had the catalog in startup/recovery mode for the first portion of the 11:00–12:00Z window, then accelerated to sustained high-rate ingest.

### Rate trajectory across the 11:00–12:00Z window

```
T1=11:11:02Z  N1=90,091   (BUY-35489 prior-fire sample)
T2=11:12:49Z  N2=90,093   (BUY-35489 final sample; rate ~67/hr — near-zero)
--- acceleration begins after 11:12Z ---
T3=12:04:50Z  N3=445,203   (BUY-35489 state snapshot)
T4=12:09:48Z N4=509,098   (this fire's sample; rate ~771,900/hr)
```

The 10:00–11:00Z window (BUY-35444/BUY-35489) was devastated by the 3rd postmaster restart at 10:21:09Z, producing ~87,473 post-restart inserts in the 38m51s window — ~58.3% of threshold. The 11:00–12:00Z window has recovered strongly to ~233.8% of threshold, suggesting the maglev writer has exited recovery/backfill mode and entered sustained live-ingest mode.

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **n_tup_ins samples:**
  ```sql
  SELECT n_tup_ins FROM pg_stat_user_tables WHERE relname='products';
  -- T1=11:11:02Z N1=90,091  (BUY-35489 prior-fire)
  -- T2=11:12:49Z N2=90,093  (BUY-35489 final)
  -- T3=12:04:50Z N3=445,203 (BUY-35489 state)
  -- T4=12:09:48Z N4=509,098 (this fire)
  ```

- **Rate T3→T4:** `509,098 − 445,203 = 63,895` rows / `4m58s` = **771,900/hr**

- **Postmaster start time (maglev):**
  ```sql
  SELECT pg_postmaster_start_time();
  -- 2026-06-08T10:21:09.112373+00
  ```
  The postmaster is **1h48m39s old** at the time of the T4 sample (12:09:48Z). This is the BUY-35444 restart (3rd in <24h; 1st = BUY-34770 at 21:17Z 2026-06-07, 2nd = BUY-35260 at 06:03:42Z).

- **n_tup_ins on `products` (cumulative since postmaster restart at 10:21:09Z):**
  ```sql
  SELECT n_tup_ins, n_tup_upd, n_tup_del, n_live_tup
  FROM pg_stat_user_tables WHERE relname='products';
  -- n_tup_ins=509,098  n_tup_upd=3,890,764  n_tup_del=0  n_live_tup=444,593
  ```
  Note: `n_tup_ins=509,098` is the cumulative insert count since the 10:21:09Z restart (3rd postmaster start in <24h). The n_tup_upd count (3.89M) reflects active UPSERT operations hitting backfill primary keys — consistent with the sustained live-ingest rate seen in the T3→T4 sample.

## Comparison with prior windows

| Window | Net inserts | % of 150K target | Notes |
|---|---|---|---|
| 10:00–11:00Z (BUY-35489) | ~87,473 (FAIL, ~58.3%) | Wiped by 3rd restart @ 10:21:09Z; post-restart lower bound only |
| 11:00–12:00Z (BUY-35541) | **~350,699 (PASS, 233.8%)** | Strong recovery; writer exited recovery mode |
