# BUY-32224 — Hourly throughput check (2026-06-06 16:00–17:00 UTC)

**Result: FAIL — failure-report child issue created under [BUY-29861](/BUY/issues/BUY-29861).**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T16:00:00+00:00 -> 2026-06-06T17:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **4,927** |
| Threshold | 150,000 |
| Margin vs. threshold | **-145,073 (-96.7%)** |
| First row in window | 2026-06-06 16:00:34.578495+00 |
| Last row in window | 2026-06-06 16:59:43.779026+00 |
| Source mix (all rows) | `chewy_us` 100% (4,927 / 4,927) |
| Partition mix (all rows) | `products_us` 100% (4,927 / 4,927) |
| Distinct source labels in window | 1 (`chewy_us`) |

## DB proof (canonical PostgreSQL @ maglev.proxy.rlwy.net:31310/railway)

- Direct count (re-ran 2026-06-06 17:33 UTC):
  ```sql
  SELECT COUNT(*) FROM products
  WHERE created_at >= '2026-06-06 16:00:00+00'
    AND created_at <  '2026-06-06 17:00:00+00';
  -- → 4927
  ```
  `EXPLAIN ANALYZE`: Parallel Append across `products_sg` (0 rows), `products_us` (4,927 rows), `products_default` (0 rows). Execution time 529 ms. Index path on `created_at` is not used (parallel seq scan), but the result is unambiguous: 4,927 rows.
- Source breakdown:
  ```sql
  SELECT source, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 16:00:00+00' AND created_at < '2026-06-06 17:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- chewy_us | 4927
  ```
- Partition breakdown:
  ```sql
  SELECT tableoid::regclass AS partition, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 16:00:00+00' AND created_at < '2026-06-06 17:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- products_us | 4927
  ```
- Writer status (re-checked at 17:32 UTC): the writer **is alive** in the 17:00–18:00 hour — at 17:32 UTC the 17:00 hour already holds 2,814 rows (also `chewy_us`). The fleet is delivering rows, but the chewy_us lane is the only channel currently producing volume.

## Per-minute breakdown of the failing hour (2026-06-06 16:00–17:00 UTC)

The writer was active throughout the hour but capped at a low per-minute rate (average **~82 rows/min**, peak 224 rows at 16:43). No 1-minute burst above 500 rows. 47 distinct minute-buckets received rows; 13 minute-buckets received zero rows (e.g. 16:08–16:13, 16:17–16:18, 16:53, 16:55). Full breakdown captured in this run.

## Recent hourly buckets (UTC), derived this run

| Hour (UTC)        | Rows     | >=150k? |
|-------------------|---------:|:-------:|
| 2026-06-06 16:00  |   4,927  | NO |
| 2026-06-06 15:00  |   4,593  | NO |
| 2026-06-06 14:00  |   2,126  | NO |
| 2026-06-06 13:00  |   6,812  | NO |
| 2026-06-06 04:00  |     148  | NO |
| 2026-06-05 19:00  |       9  | NO |
| 2026-06-06 17:00 (in flight, 32m in) | 2,708 | likely FAIL |

The 14:00–17:00 UTC stretch on 2026-06-06 is a sustained low-throughput window: every closed hour since 13:00 has come in **far below the 150,000/hr bar**, and the live 17:00 hour is on the same trajectory.

## Why the 16:00–17:00 hour was a FAIL (per Rich: "explain your failure on an hourly basis")

- **No infrastructure cap observed.** DB writes succeed; no `INGESTION_HOLD`; the writer is alive and is delivering rows to `products_us`/`chewy_us` in the next hour.
- **Only one channel delivered rows in the window.** The `chewy_us` source contributed 4,927 / 4,927 = 100% of the rows. All other ingest lanes (Shopify US/SG discovery, WooCommerce, brand-direct, zalora, hunter/scout sublanes) are not currently producing hour-level volume into canonical PostgreSQL — or their batches landed outside the 16:00–17:00 window.
- **Per-minute ceiling is low.** The highest single minute was 224 rows at 16:43; the per-minute average is ~82. Even sustained for the full 60 minutes, the chewy_us lane alone would top out near 5,000 rows/hr — two orders of magnitude short of 150,000.
- **Source-mix concentration is the gap.** 100% chewy_us fails the 60/20/20 (Shopify / brand-direct / WooCommerce) target on the unblocker thread under [BUY-30590](/BUY/issues/BUY-30590). The non-chewy/non-Shopify lanes must come back online at hour-level volume before the 150k/hr bar is reachable from a single channel's product.
- **No new ingest burst landed in the window.** The previous fire ([BUY-32749](/BUY/issues/BUY-32749), 15:00–16:00) reported 339,766 rows with an active 4-session writer. By 16:00 UTC that burst had ended; the residual chewy_us trickle was all that remained.

## Action taken
- **Failure-report child issue created** under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, priority `critical`, status `todo`. Linked from the BUY-32224 closing comment.
- BUY-32224 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 18:00 UTC will measure 17:00–18:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
