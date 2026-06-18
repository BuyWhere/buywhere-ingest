# BUY-35625 — Hourly throughput check (2026-06-08 14:04 UTC fire, 13:00–14:00 UTC window)

**Result: PASS — ~1,170,360 / 150,000 (780.2% of threshold; +1,020,360 rows above bar). Sustained recovery from the BUY-35444 3rd maglev postmaster restart (10:21:09Z) continues at elevated steady-state — the writer fleet more than doubled the prior 12:00–13:00Z rate of 298K/hr ([BUY-35582](/BUY/issues/BUY-35582)) to 1.17M/hr in 13:00–14:00Z, the strongest hour since before the 3rd restart. No new failure child filed under [BUY-29861](/BUY/issues/BUY-29861) per the rule ("If 150,000+ products were added, do not create the issue"). This parent (BUY-35625, routine wake) closes at `done` after the state file is updated and the heartbeat comment is posted.**

## Threshold (from [BUY-29861](/BUY/issues/BUY-29861))

- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour for this fire: 2026-06-08T13:00:00Z → 2026-06-08T14:00:00Z

| Metric | Value |
|---|---|
| Net inserts in 13:00–14:00Z (`n_tup_ins` delta, dispatcher) | **~1,170,360** |
| Threshold | 150,000 |
| Margin vs. threshold | **+1,020,360 (+680.2%)** |
| % of 150,000/hr target | **780.2%** |
| `n_tup_ins` at 14:04:44Z (T6, this fire's sample) | **1,944,290** |
| `n_tup_ins` at 13:05:18Z (T5, BUY-35582 sample) | **785,029** |
| `n_tup_ins` at 12:09:48Z (T4, BUY-35541 sample) | **509,098** |
| Rate T5→T6 (13:05:18Z→14:04:44Z, 3,566s) | **1,170,360/hr** (1,159,261 rows / 59m26s) |
| Rate T4→T5 (12:09:48Z→13:05:18Z, BUY-35582 doc) | **298,277/hr** (275,931 rows / 55m30s) |
| `pg_postmaster_start_time` (maglev) | **2026-06-08T10:21:09.112373+00** (BUY-35444 3rd restart; **3h44m old** at 14:06:01Z) |
| Direct hourly COUNT | **TIMEOUT** — `products_created_at_idx` is INVALID (`indisvalid=f`, per [BUY-32878](/BUY/issues/BUY-32878) no-DDL-on-maglev policy) |
| `n_live_tup` @ 14:04:44Z | **~52,198,046** (per pg_stat_user_tables n_live_tup) |
| Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) | **did not fire** — cron entry is broken since 2026-06-08T04:06Z ([BUY-33694](/BUY/issues/BUY-33694) dispatcher cron broken); this BUY-35625 (routine hourly fire) is the canonical hourly check for the 13:00–14:00Z window |

## Why the math works

The criterion in [BUY-29861](/BUY/issues/BUY-29861) is **net products added** during the hour. The dispatcher's n_tup_ins delta path is the canonical signal under maglev contention (per [BUY-33694](/BUY/issues/BUY-33694) memory). Anchor points:

1. **`n_tup_ins` at 13:05:18Z (T5, BUY-35582) = 785,029** — last reading at end of the prior hour's fire.
2. **`n_tup_ins` at 14:04:44Z (T6, this fire) = 1,944,290** — sampled at fire time.
3. **Delta = 1,944,290 − 785,029 = 1,159,261 rows / 3,566s = 325.04 rows/sec = 1,170,360/hr.**

This is the **dispatcher per-hour rate** — it measures the actual elapsed time between fires, giving the per-hour rate at the current sample point. The `n_tup_ins` cumulative counter reset to 0 at the 10:21:09Z postmaster restart (BUY-35444, 3rd in <24h), and has been monotonically increasing since. The 13:00-14:00Z window strongly clears the 150K bar — by 7.8×.

### Rate trajectory across the 13:00–14:00Z window

```
T4=12:09:48Z  N4=509,098   (BUY-35541 sample; rate 771,900/hr over T3→T4)
T5=13:05:18Z  N5=785,029   (BUY-35582 sample; rate 298,277/hr over T4→T5)
--- 13:00–14:00Z window starts here ---
T6=14:04:44Z  N6=1,944,290 (this fire, BUY-35625; rate 1,170,360/hr over T5→T6)
```

The 13:00–14:00Z rate (1,170,360/hr) is **3.9× higher** than the 12:00–13:00Z rate (298,277/hr) and is the strongest sustained rate observed since pre-BUY-35444 3rd-restart. The T5→T6 window covers the full 13:00–14:00 hour (sampling at 14:04:44 is 4m44s past the boundary; elapsed window 59m26s ≈ 1 hour), so this is a true per-hour rate rather than a brief burst.

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

Connection string source: `data/.catalog_db_url` (maglev). Per `feedback-catalog-db-url-shell-trap`, the URL is assigned into a quoted shell variable before use. NOT the harness `DATABASE_URL` (which is roundhouse — wrong catalog).

- **n_tup_ins samples (PRIMARY signal — works under maglev contention):**
  ```sql
  SELECT n_tup_ins FROM pg_stat_user_tables WHERE relname='products';
  -- T4=12:09:48Z N4=509,098 (BUY-35541)
  -- T5=13:05:18Z N5=785,029 (BUY-35582)
  -- T6=14:04:44Z N6=1,944,290 (this fire, BUY-35625)
  ```
- **Rate T5→T6:** `1,944,290 − 785,029 = 1,159,261` rows / `3,566s` (59m26s) = **1,170,360/hr**

- **Postmaster start time (maglev):**
  ```sql
  SELECT pg_postmaster_start_time();
  -- 2026-06-08T10:21:09.112373+00
  ```
  The postmaster is **3h44m old** at the time of the T6 sample (14:04:44Z). This is the BUY-35444 restart (3rd in <24h; 1st = BUY-34770 at 21:17Z 2026-06-07, 2nd = BUY-35260 at 06:03:42Z).

- **n_tup_ins on `products` (cumulative since postmaster restart at 10:21:09Z):**
  ```sql
  SELECT n_tup_ins, n_tup_upd, n_tup_del, n_live_tup
  FROM pg_stat_user_tables WHERE relname='products';
  -- n_tup_ins=1,944,290  n_tup_upd=?  n_tup_del=0  n_live_tup=52,198,046
  ```
  Note: `n_tup_ins=1,944,290` is the cumulative insert count since the 10:21:09Z restart (3h44m ago). At 1,170,360/hr observed rate, this represents 1h39m of sustained ingest; the remaining ~2h05m of post-restart time was spent in earlier steady-state ramp-up from 0.

- **Hour-bucket COUNT (SECONDARY — best-effort, may time out):**
  ```sql
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-08T13:00:00+00:00'
    AND created_at <  '2026-06-08T14:00:00+00:00'
  GROUP BY 1 ORDER BY 1;
  -- QueryCanceled after 30s (products_created_at_idx INVALID per BUY-32878)
  ```

## Comparison with prior windows

| Window | Net inserts | % of 150K target | Notes |
|---|---|---|---|
| 09:00–10:00Z (BUY-35386) | ~501,000 (PASS, 334%) | Healthy pre-3rd-restart |
| 10:00–11:00Z (BUY-35444/BUY-35489) | ~87,473 (FAIL, 58.3%) | Wiped by 3rd restart @ 10:21:09Z; post-restart lower bound only |
| 11:00–12:00Z (BUY-35541) | ~350,699 (PASS, 233.8%) | Strong recovery; writer exited recovery mode |
| 12:00–13:00Z (BUY-35582) | ~298,277 (PASS, 198.9%) | Sustained steady-state; 2× target |
| 13:00–14:00Z (BUY-35625) | **~1,170,360 (PASS, 780.2%)** | **Strongest hour since pre-3rd-restart; 7.8× target** |

## State file

`data/.throughput_state.json` was snapshotted to `data/.throughput_state.json.snapshot-pre-buy-35625-fire-20260608T140445Z` (per `feedback_dispatcher_dry_run_writes_state.md`) before the live re-fire, then updated by the live dispatcher run:

```json
{
  "last_n_tup_ins": 1944290,
  "last_n_tup_ins_at": "2026-06-08T14:04:44.161962+00:00",
  "last_hour_checked": "2026-06-08T13:00:00+00:00",
  "last_check_result": "PASS",
  "last_check_real_rows": 1170360,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 52198046,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway",
  "last_fire_buy": "BUY-35625",
  "last_fire_note": "PASS ~1,170,360 rows (780.2% of 150K). Strongest hour since pre-3rd-restart. Sustained recovery from BUY-35444. No failure child filed.",
  "last_fire_doc": "docs/buy-35625-hourly-throughput-check-2026-06-08T13.md"
}
```

(Note: `last_fire_buy` and `last_fire_doc` are updated as part of this fire's close, per the convention noted in the BUY-35582 doc.)

## Disposition

**done** — BUY-35625 closes at 14:08Z after state file update + this doc + heartbeat comment on the parent. No failure child filed under BUY-29861 (13:00–14:00Z window PASSed at 780.2% of 150K target).
