# BUY-48231 — Oracle catalog count reconciliation (2026-06-14 UTC)

Issue: [BUY-48231](/BUY/issues/BUY-48231)  
Owner: Oracle (`3ec8f6dd`)  
Collected at: `2026-06-14 06:22:58 UTC` to `2026-06-14 06:26:01 UTC`

## Decision Summary

1. The CEO report's merchant KPI remains **product-backed merchants**, defined only as exact `COUNT(DISTINCT public.products.merchant_id)` on the canonical maglev DB.
2. `public.merchants` is **formally retired from CEO reporting as the merchant KPI surface**. It may remain an operational registry/dimension table, but it must not populate the `Real merchants` KPI row.
3. The approved daily product top-line remains the canonical DB `pg_class.reltuples(public.products)` value, with `pg_stat_user_tables.products.n_live_tup` kept only as an operational cross-check. The stale `16.8M` exact-count report path stays retired.
4. The approved daily fallback for the merchant KPI, when a fresh exact `COUNT(DISTINCT)` is too expensive inside a heartbeat, is: **carry the last confirmed exact product-backed merchant count with its as-of timestamp and explicitly mark the row stale / blocked for fresh refresh**. Do not swap in `public.merchants`.

## Fresh Canonical DB Evidence

Source of truth:

- `data/.catalog_db_url`
- Host resolved from the file: `maglev.proxy.rlwy.net:31310/railway`

Observed on `2026-06-14`:

- `public.products`:
  - `pg_class.reltuples = 77,343,112`
  - `pg_stat_user_tables.n_live_tup = 85,318,362`
  - gap = `7,975,250` (`10.31%`) with `n_live_tup` higher than `reltuples`
  - `last_analyze = 2026-06-11 13:20:05 UTC`
  - fresh exact `COUNT(*)` with `statement_timeout='20s'` timed out (`exit=124`)
- `public.merchants`:
  - physical `count(*) = 74,848`
  - `pg_class.reltuples = 74,791`
  - `84.86%` of rows (`63,514 / 74,848`) have `products_count IS NULL`
  - only `15.12%` of rows (`11,320 / 74,848`) have `products_count > 0`
  - `first_indexed_at IS NOT NULL` on `8,097` rows
  - fresh exact `COUNT(DISTINCT public.products.merchant_id)` with `statement_timeout='20s'` timed out (`exit=124`)

## Reconciliation

### Merchant KPI

The June 13 correction request is valid: `public.merchants` and `COUNT(DISTINCT public.products.merchant_id)` are not interchangeable.

Why `public.merchants` is retired from the KPI slot:

- it measures registry rows, not the distinct merchant ids actually referenced by products
- the table currently contains many rows without populated `products_count` (`63,514`)
- a registry row count can move because of registry maintenance, backfills, or dimension work even when product-backed merchant coverage does not

Approved contract:

- canonical metric: `COUNT(DISTINCT public.products.merchant_id)`
- approved daily fallback when a fresh exact run is too expensive: carry the **last confirmed exact** distinct-merchant value and label it stale with the refresh blocker
- not approved as fallback: `public.merchants.count(*)`, `public.merchants.reltuples`, `public.merchants.products_count > 0`, or `pg_stats.n_distinct`

Operational note:

- `public.merchants` may still be useful as a registry-size/context table, but only in prose and only when labeled as such

### Product Top-Line

The standing CEO-report format contract already requires one canonical DB number for the catalog top-line. The current reconciliation is:

- CEO daily top-line: `pg_class.reltuples(public.products)` from the canonical DB
- support-only cross-check: `pg_stat_user_tables.products.n_live_tup`
- retired daily path: fresh exact full-table `COUNT(*)` inside a heartbeat, because it no longer returns within the daily execution budget on the current maglev catalog size
- retired stale package: the old `16.8M` exact-count path from `2026-06-01`

This keeps one daily headline number while preserving the more volatile `n_live_tup` estimate as a sanity check for ops/debugging and growth pacing.

## Canonical Query / Metric Contract

### Merchant KPI

Canonical exact query:

```sql
SELECT COUNT(DISTINCT merchant_id)
FROM public.products;
```

Daily reporting rule:

- use the exact query when it returns within heartbeat budget
- otherwise report the last confirmed exact value with its as-of timestamp and an explicit stale/blocked reason
- never replace the KPI with any `public.merchants`-derived number

### Product Top-Line

Canonical daily query:

```sql
SELECT reltuples::bigint
FROM pg_class
WHERE oid = 'public.products'::regclass;
```

Support-only cross-check:

```sql
SELECT n_live_tup::bigint, last_analyze
FROM pg_stat_user_tables
WHERE relid = 'public.products'::regclass;
```

Daily reporting rule:

- cite only `reltuples` in the KPI row
- use `n_live_tup` only as supporting prose / operational context
- do not cite runtime `/v1/catalog/stats` or the retired `16.8M` exact package as the CEO top-line

## Required 2026-06-13 CEO Report Correction

The corrected Oracle section should read as follows:

- merchant KPI surface: **product-backed merchants from `public.products` only**
- merchant fallback if fresh exact is too expensive: **last confirmed exact distinct merchant count, explicitly labeled stale/blocked**
- `public.merchants`: **retired from the KPI slot; registry-only context**
- product top-line: **canonical DB `reltuples` only**, with `n_live_tup` mentioned only as supporting context if needed

## Verification

- Verified live maglev reads via `data/.catalog_db_url`
- Verified both fresh exact `COUNT(*)` on `public.products` and fresh exact `COUNT(DISTINCT merchant_id)` on `public.products` exceed a `20s` heartbeat-safe budget on this runner
- Updated the standing CEO report format contract to prevent future merchant-surface drift
