# BUY-30757 — Hourly throughput check (2026-06-05 03:00–04:00 UTC)

**Result: PASS — 202,843 ≥ 150,000. No failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T03:00:00+00:00 → 2026-06-05T04:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **202,843** |
| Real rows (excluding synthetic merchants & `example.com`) | **202,843** |
| Threshold | 150,000 |
| Margin vs. threshold | **+52,843 (+35.2%)** |

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 03:00:00+00' AND created_at < '2026-06-05 04:00:00+00'`.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL filter → 0 rows.

## Source mix this hour

| Source | Rows |
|---|---:|
| shopify (sustained-loop) | 144,699 (71.3%) |
| google_shopping | 47,205 (23.3%) |
| shopify_carbon38 | 5,840 (2.9%) |
| shopify_filson | 1,097 |
| shopify_blackdiamond | 1,050 |
| shopify_seatosummit | 623 |
| shopify_stanley | 401 |
| shopify_goalzero | 391 |
| shopify_darntough | 377 |
| shopify_cascadedesigns | 370 |
| other long-tail shopify | balance |

Two-lane hour: shopify sustained-loop + google_shopping batch. The google_shopping contribution restored breadth and pushed the hour back over threshold.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_carbon38 | 5,840 |
| shopify_truck_parts_warehouse_myshopify_com | 1,500 |
| shopify_skechersth_myshopify_com | 1,500 |
| shopify_suta_in_myshopify_com | 1,500 |
| shopify_truckpartsstore_myshopify_com | 1,500 |
| shopify_riflepaperco_com | 1,500 |
| shopify_toy_kingdom_ph_myshopify_com | 1,500 |
| shopify_jixhobbies_co_za | 1,291 |
| shopify_rosadababy_com | 1,285 |
| shopify_thegametree_co_nz | 1,280 |

Several merchants near the 1,500 page-cap ceiling — broad merchant breadth, no single-merchant spike.

## Comparison vs. prior hours

| Hour (UTC) | Rows | Threshold | Margin |
|---|---:|---:|---:|
| 2026-06-04 20:00–21:00 | 122,383 | 150,000 | −27,617 (−18.4%) FAIL |
| 2026-06-04 21:00–22:00 | 182,795 | 150,000 | +32,795 (+21.9%) PASS |
| 2026-06-04 22:00–23:00 | 119,120 | 150,000 | −30,880 (−20.6%) FAIL |
| 2026-06-04 23:00–00:00 | 50,350 | 150,000 | −99,650 (−66.4%) FAIL |
| 2026-06-05 00:00–01:00 | 208,694 | 150,000 | +58,694 (+39.1%) PASS |
| 2026-06-05 01:00–02:00 | 312,321 | 150,000 | +162,321 (+108.2%) PASS |
| 2026-06-05 02:00–03:00 | 98,001 | 150,000 | −51,999 (−34.7%) FAIL |
| **2026-06-05 03:00–04:00** | **202,843** | **150,000** | **+52,843 (+35.2%) PASS** |

Hour-over-hour: +104,842 (+107.0%). Recovery from the 02:00 FAIL via google_shopping batch landing alongside the steady shopify loop. Threshold cleared cleanly.

## Action taken
- **No failure-report child issue created** — hour was a PASS.
- BUY-30757 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 05:00 UTC will measure 04:00–05:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
