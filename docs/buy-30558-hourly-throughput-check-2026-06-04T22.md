# BUY-30558 — Hourly throughput check (2026-06-04 22:00–23:00 UTC)

**Result: FAIL — failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of BUY-29861 assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-04T22:00:00+00:00 → 2026-06-04T23:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **119,120** |
| Real rows (excluding synthetic merchants & `example.com`) | **119,120** |
| Threshold | 150,000 |
| Shortfall vs. threshold | **−30,880 (−20.6%)** |

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-04 22:00:00+00' AND created_at < '2026-06-04 23:00:00+00'`.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_manamarket_com_au | 1,500 |
| shopify_miot_store_com | 1,500 |
| shopify_akgalleria_com | 1,499 |
| shopify_blackvaultgaming_com | 1,498 |
| shopify_feldkampsfurniture_com | 1,496 |
| shopify_habitatrestore_ca | 1,352 |
| shopify_americanrattan_com | 1,295 |
| shopify_myrausa_com | 1,265 |
| shopify_whiskyandmore_co_nz | 1,261 |
| shopify_muji_com_au | 1,259 |

## Comparison vs. prior hours

| Hour (UTC) | Real rows | Threshold | Margin |
|---|---:|---:|---:|
| 2026-06-04 21:00–22:00 | 182,795 | 150,000 | +32,795 (+21.9%) |
| **2026-06-04 22:00–23:00** | **119,120** | **150,000** | **−30,880 (−20.6%)** |

A ~63,675-row hour-over-hour drop (−34.8%) tipped the just-completed hour below the threshold despite the prior hour passing comfortably.

## Action taken
- **New failure-report child issue created**: [BUY-30574](/BUY/issues/BUY-30574) under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- BUY-30558 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. It produced this run issue at 2026-06-04T23:01:05Z.

## Parent
- BUY-29861 — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
