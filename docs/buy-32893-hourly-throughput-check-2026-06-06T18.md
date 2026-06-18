# BUY-32893 — Hourly throughput check (2026-06-06 18:00–19:00 UTC)

**Result: FAIL — failure-report child issue created under [BUY-29861](/BUY/issues/BUY-29861).**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T18:00:00+00:00 -> 2026-06-06T19:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **2,745** |
| Threshold | 150,000 |
| Margin vs. threshold | **-147,255 (-98.2%)** |
| % of 150,000/hr target | **1.8%** |
| First row in window | 2026-06-06 18:00:21.873660+00 |
| Last row in window | 2026-06-06 18:46:40.612465+00 |
| Source mix (all rows) | `chewy_us` 100% (2,745 / 2,745) |
| Partition mix (all rows) | `products_us` 100% (2,745 / 2,745) |
| Distinct source labels in window | 1 (`chewy_us`) |
| Per-minute: buckets with rows | 42 / 60 |
| Per-minute: peak rows/min | 325 |
| Per-minute: average rows/min | 65.4 |
| Rows before hour (`created_at < 18:00 UTC`) | 4,189,599 |
| Rows after hour (`created_at < 19:00 UTC`) | 4,192,344 |
| Delta (after - before) | **2,745** (matches window count) |
| Total rows in `products` | 4,196,663 |
| `is_synthetic = true` rows in window | 0 |
| `is_active = false` rows inserted in window | 0 |

## DB proof (canonical PostgreSQL @ roundhouse.proxy.rlwy.net:27479/railway)

Connection string source: harness env `DATABASE_URL` (workspace primary DB used by the harness for catalog ingest writes). Workspace historical reports reference `data/.catalog_db_url` (maglev.proxy.rlwy.net:31310) — that host was unresponsive on read for this run (writer contention; multiple long-running `INSERT INTO products` and `SELECT count(DISTINCT p.url)` queries observed in `pg_stat_activity` from the maglev end), so the roundhouse replica was used. The two DBs are in the same product family; roundhouse is the writer's primary, maglev is a downstream read replica used by earlier reports.

- Direct count (executed 2026-06-06 20:12 UTC):
  ```sql
  SELECT COUNT(*) FROM products
  WHERE created_at >= '2026-06-06 18:00:00+00'
    AND created_at <  '2026-06-06 19:00:00+00';
  -- → 2745
  ```
- Source breakdown:
  ```sql
  SELECT source, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 18:00:00+00' AND created_at < '2026-06-06 19:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- chewy_us | 2745
  ```
- Partition breakdown:
  ```sql
  SELECT tableoid::regclass AS partition, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 18:00:00+00' AND created_at < '2026-06-06 19:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- products_us | 2745
  ```
- Writer status: writer is alive and continues to land rows in the next (19:00) hour — at 20:12 UTC the 19:00 hour holds 3,991 rows (also `chewy_us`, `products_us`). No `INGESTION_HOLD`. Failure is **not** a writer/plumbing outage.
- Last 24h credited adds: 29,740 vs 3,600,000 required (0.83% of target).

## Per-minute breakdown of the failing hour (2026-06-06 18:00–19:00 UTC)

Writer was active 42 / 60 minutes. First row landed at 18:00:21, last at 18:46:40. From 18:47 UTC through 19:00 UTC the chewy_us channel produced **zero** rows in this window — the writer was idle for the back half of the hour. Peak per-minute volume: 325 rows. Per-minute average: ~65.4 rows. Even sustained for 60 minutes at peak, the chewy_us lane would top out near ~19,500 rows/hr — still an order of magnitude short of 150,000.

## Recent hourly buckets (UTC), derived this run

| Hour (UTC)        | Rows     | >=150k? | Notes |
|-------------------|---------:|:-------:|---|
| 2026-06-06 19:00 (in flight, ~72 min in) | 3,991 | (on pace: FAIL) | chewy_us only |
| **2026-06-06 18:00** |   **2,745**  | **NO** | **this doc** |
| 2026-06-06 17:00  |   5,305  | NO | chewy_us 4,825 + sitemap 480 |
| 2026-06-06 16:00  |   4,927  | NO | chewy_us only — [BUY-32933](/BUY/issues/BUY-32933) |
| 2026-06-06 15:00  |   4,593  | NO | chewy_us only |
| 2026-06-06 14:00  |   2,126  | NO | chewy_us only |
| 2026-06-06 13:00  |   6,812  | NO | chewy_us only |

**The 13:00–19:00 UTC stretch on 2026-06-06 is now seven consecutive failed closed-or-in-flight hours**, every hour delivered by a single channel (`chewy_us` plus a 480-row `sitemap` blip at 17:00). The in-flight 19:00 hour is on the same single-channel, sub-5k-per-hour trajectory.

## Why the 18:00–19:00 hour was a FAIL

- **No infrastructure cap observed.** DB writes succeed; no `INGESTION_HOLD`; the writer is alive and continues to land `chewy_us` rows in the 19:00 hour.
- **Only one channel delivered rows in the window.** `chewy_us` contributed 2,745 / 2,745 = 100% of the rows. All other ingest lanes (Shopify US/SG discovery, WooCommerce, brand-direct, zalora, hunter/scout sublanes) did not produce any row in the 18:00–19:00 window.
- **The chewy_us channel went idle in the back half of the hour.** First row at 18:00:21, last row at 18:46:40 — 13 minutes 20 seconds of zero production between 18:47 and 19:00. This is the lowest-volume closed hour in the 7-hour low-throughput stretch.
- **Source-mix concentration is the gap.** 100% chewy_us fails the 60/20/20 (Shopify / brand-direct / WooCommerce) target on the unblocker thread under [BUY-30590](/BUY/issues/BUY-30590). The non-chewy / non-Shopify lanes must come back online at hour-level volume before the 150k/hr bar is reachable from a single channel's product.
- **No new ingest burst landed in the window.** The previous fire [BUY-32933](/BUY/issues/BUY-32933) (16:00–17:00) reported 4,927 rows. The 17:00 hour lifted slightly to 5,305 with a 480-row `sitemap` blip. The 18:00–19:00 hour dropped back to 2,745 with no blip at all.

## Action taken
- **Failure-report child issue created** under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, priority `critical`, status `todo`. Linked from the BUY-32893 closing comment.
- BUY-32893 closed `done` with this DB-proof record.

## Routine

- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 20:00 UTC will measure 19:00–20:00.
- Prior unprocessed routine issues: [BUY-32986](/BUY/issues/BUY-32986) (18:00 fire, 17:00–18:00 hour) and [BUY-33056](/BUY/issues/BUY-33056) (19:00 fire, 18:00–19:00 hour). The 19:00 fire was created at 19:23:08Z and is the same window this issue covers; the harness instead woke this stale 17:00 issue at 20:12Z, so the 19:00 fire will be re-fired by the cron at 20:00 UTC and that worker should not duplicate the report for the 18:00–19:00 hour (this report already covers it).

## Parent

- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
