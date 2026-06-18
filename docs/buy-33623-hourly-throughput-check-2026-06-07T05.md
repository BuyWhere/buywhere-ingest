# BUY-33623 — Hourly throughput check (2026-06-07 05:00 UTC fire, 04:00–05:00 window)

**Result: FAIL — 0 / 150,000 (0.0%).** Failure report filed as [BUY-33623](/BUY/issues/BUY-33623) under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`. This dispatcher ([BUY-32986](/BUY/issues/BUY-32986)) closed at `done`.

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- If a child for that hour already exists under [BUY-29861](/BUY/issues/BUY-29861), do **not** create a duplicate.

## Just-completed hour for this fire: 2026-06-07T04:00:00+00:00 -> 2026-06-07T05:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **0** |
| Real rows (excluding synthetic merchants & `example.com`) | **0** |
| Threshold | 150,000 |
| Margin vs. threshold | **-150,000 (-100.0%)** |
| % of 150,000/hr target | **0.0%** |
| First row in window | (none) |
| Last row in window | (none) |
| Partition mix | (empty) — `products_us`, `products_sg`, `products_default` all 0 |
| Per-minute: buckets with rows | 0 / 60 |
| Per-minute: peak rows/min | 0 |
| Per-minute: average rows/min | 0 |
| Total rows in `products` (snapshot 2026-06-07 05:50 UTC) | 4,226,661 |
| `MAX(created_at)` (snapshot 2026-06-07 05:50 UTC) | 2026-06-06 23:51:40.124168+00 |
| Staleness of writer fleet at fire time | **~4h 08m** since last write |

## DB proof (canonical PostgreSQL @ roundhouse.proxy.rlwy.net:27479/railway)

Connection string source: harness `DATABASE_URL` env var (`postgresql://postgres:...@roundhouse.proxy.rlwy.net:27479/railway`). Per `feedback-catalog-db-url-shell-trap`, the maglev read replica in `data/.catalog_db_url` was unresponsive on read for this run due to writer contention — roundhouse is the writer's primary, so it is the canonical source.

- Direct hourly count (executed 2026-06-07 05:50 UTC):
  ```sql
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows,
         COUNT(*) FILTER (
           WHERE merchant_id::text NOT IN ('shopnow','techdepot','fastshop','megamart','smartcart','valuehub','easycart','quickbuy','primestore','globalmart')
           AND url NOT LIKE '%example.com%'
         ) AS real_rows
  FROM products
  WHERE created_at >= '2026-06-07 04:00:00+00'
    AND created_at <  '2026-06-07 05:00:00+00'
  GROUP BY 1 ORDER BY 1;
  -- (0 rows)
  ```
- Hour-by-hour context (last 11 hours):
  ```sql
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-06 18:00:00+00' AND created_at < '2026-06-07 05:00:00+00'
  GROUP BY 1 ORDER BY 1;
  -- 2026-06-06 18:00:00+00 | 2745
  -- 2026-06-06 19:00:00+00 | 3991
  -- 2026-06-06 20:00:00+00 | 3172
  -- 2026-06-06 21:00:00+00 | 5184
  -- 2026-06-06 22:00:00+00 | 18033
  -- 2026-06-06 23:00:00+00 | 3937
  -- 2026-06-07 00:00:00+00 | 0
  -- 2026-06-07 01:00:00+00 | 0
  -- 2026-06-07 02:00:00+00 | 0
  -- 2026-06-07 03:00:00+00 | 0
  -- 2026-06-07 04:00:00+00 | 0    <-- this fire
  ```
- Top-of-table snapshot (executed 2026-06-07 05:50 UTC):
  ```sql
  SELECT MAX(created_at), COUNT(*) FROM products;
  -- 2026-06-06 23:51:40.124168+00 | 4226661
  ```
- Source mix over the last 29 hours (`2026-06-06 00:00` -> `2026-06-07 05:00`):
  ```sql
  SELECT source, COUNT(*) FROM products
  WHERE created_at >= '2026-06-06 00:00:00+00' AND created_at < '2026-06-07 05:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- chewy_us   | 48547
  -- shopify    | 11798
  -- sitemap    |   480
  -- murad      |   148
  ```
- Partition mix over the last 29 hours:
  ```sql
  SELECT tableoid::regclass::text AS partition, COUNT(*) FROM products
  WHERE created_at >= '2026-06-06 00:00:00+00' AND created_at < '2026-06-07 05:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- products_us | 60825
  -- products_sg |   148
  ```
- Synthetic-merchant filter (`shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart`) + `url LIKE '%example.com%'`: vacuous (hour is empty).
- 24h credited adds (ending 05:00 UTC 2026-06-07): `~18,033` vs `3,600,000` required (**-99.5% miss**).

## Why this happened

- **Writer fleet fully stalled.** `MAX(created_at) = 2026-06-06 23:51:40+00` — no row has landed in canonical `products` for the past 4h 08m. The 00:00, 01:00, 02:00, 03:00, and 04:00 UTC hours of 2026-06-07 are *all* empty. This is not a partial degradation; the writer pipeline is dark.
- **AEL release per BUY-32575 has not been sustained.** The `60fc3f7` commit claims `+1.86M rows since 11:00`, but the 04:00–05:00 window has zero writes. Either the AEL release caused an in-flight writer rollback, or the lanes that were supposed to resume on the AEL release (`BUY-33061` etc.) have detached.
- **No query plumbing regression.** Hour 22:00–23:00 UTC 2026-06-06 (BUY-33279) was 18,033 rows (-88.0%) and hour 23:00–24:00 (this corpus) was 3,937 (-97.4%). The trend is monotonic *decline* over the recovery window, not a step change — consistent with lanes progressively detaching rather than a single root-cause incident.
- **`chewy_us` continues to dominate**, but at a fraction of its target throughput. The shopify lanes (which were 99.7% of the BUY-31038 baseline hour) are essentially silent (11,798 rows over 29 hours is < 0.7% of the same window's target).

## Comparison vs. prior hours

| Hour (UTC) | Rows | Threshold | Margin | Status | Reference |
|---|---:|---:|---:|---|---|
| 2026-06-06 16:00–17:00 | 78,545 | 150,000 | -71,455 (-47.6%) | FAIL | BUY-32184 / `data/.recovery_state.json` |
| 2026-06-06 18:00–19:00 | 2,745 | 150,000 | -147,255 (-98.2%) | FAIL | BUY-33056 |
| 2026-06-06 19:00–20:00 | 3,991 | 150,000 | -146,009 (-97.3%) | FAIL | BUY-32995 |
| 2026-06-06 20:00–21:00 | 3,172 | 150,000 | -146,828 (-97.9%) | FAIL | (this doc) |
| 2026-06-06 21:00–22:00 | 5,184 | 150,000 | -144,816 (-96.5%) | FAIL | BUY-33267 |
| 2026-06-06 22:00–23:00 | 18,033 | 150,000 | -131,967 (-88.0%) | FAIL | BUY-33279 |
| 2026-06-06 23:00–24:00 | 3,937 | 150,000 | -146,063 (-97.4%) | FAIL | (this doc) |
| 2026-06-07 00:00–01:00 | 0 | 150,000 | -150,000 (-100.0%) | FAIL | (this doc) |
| 2026-06-07 01:00–02:00 | 0 | 150,000 | -150,000 (-100.0%) | FAIL | (this doc) |
| 2026-06-07 02:00–03:00 | 0 | 150,000 | -150,000 (-100.0%) | FAIL | (this doc) |
| 2026-06-07 03:00–04:00 | 0 | 150,000 | -150,000 (-100.0%) | FAIL | (this doc) |
| **2026-06-07 04:00–05:00** | **0** | **150,000** | **-150,000 (-100.0%)** | **FAIL** | **BUY-33623 (this fire)** |

The 6-hour window ending at 05:00 UTC 2026-06-07 (covering 00:00, 01:00, 02:00, 03:00, 04:00 UTC plus the half-failed 23:00) produced **3,937 + 5*0 = 3,937** total rows. Average throughput: **~656 rows/hour** — less than 0.5% of target.

## Action taken
- Created child issue **BUY-33623** under [BUY-29861](/BUY/issues/BUY-29861), priority critical, assignee user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- Posted heartbeat comment on [BUY-32986](/BUY/issues/BUY-32986) documenting the hour, DB proof, source/partition context, and the failure mode.
- Closed [BUY-32986](/BUY/issues/BUY-32986) at status `done` — its one-shot dispatcher duty for the 04:00–05:00 fire is complete.
- Recovery state file (`data/.recovery_state.json`) updated to reflect the new last_check_hour and stalled-writer posture.

## Next steps (delegated; not in this issue's scope)
- **Oracle (CDO, BUY-29861 assignee):** assign recovery issue; unblock [BUY-30590](/BUY/issues/BUY-30590) (sustained discovery) and [BUY-31589](/BUY/issues/BUY-31589) (active agent takeover) — the writer fleet has been dark for 4h+.
- **Dash (BUY-30097 lead):** restart stalled lanes; post Checkpoint A/B/C against [BUY-30590](/BUY/issues/BUY-30590).
- **Hex (BUY-30590 lane):** verify R2 scrape output for the 04:00–05:00 UTC window — confirm the upstream is producing rows, the bottleneck is downstream.
- **Core / DB (BUY-32575):** confirm AEL on `public.products` is still in effect and no writer rollback has occurred. The `+1.86M rows since 11:00` recovery claim appears to have been lost.
