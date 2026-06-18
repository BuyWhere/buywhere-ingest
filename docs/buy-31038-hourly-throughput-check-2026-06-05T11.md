# BUY-31038 — Hourly throughput check (2026-06-05 11:00–12:00 UTC)

**Result: PASS — 344,468 ≥ 150,000. No failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T11:00:00+00:00 → 2026-06-05T12:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **344,468** |
| Real rows (excluding synthetic merchants & `example.com`) | **344,468** |
| Threshold | 150,000 |
| Margin vs. threshold | **+194,468 (+129.6%)** |

Strictly above 150,000 → no failure report required per [BUY-29861](/BUY/issues/BUY-29861).

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 11:00:00+00' AND created_at < '2026-06-05 12:00:00+00'` → **344,468**.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Source mix this hour

| Source | Rows | Share |
|---|---:|---:|
| shopify | 343,368 | 99.68% |
| shopify_redheart | 400 | 0.12% |
| shopify_yarnspirations | 400 | 0.12% |
| shopify_jimmybeans | 300 | 0.09% |

Pure-Shopify hour again — main `shopify` loop dominates with three dedicated shopper lanes contributing 1,100 rows combined. No `woocommerce`, `ebay_us`, `s3cdx`/CC-MAIN, or `google_shopping` rows landed in the window.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_013554_2c_myshopify_com | 18,500 |
| shopify_lens_cl_myshopify_com | 17,557 |
| shopify_buysoundtrax_myshopify_com | 15,250 |
| shopify_ec_model_on_search_en_myshopify_com | 15,000 |
| shopify_1008stores_myshopify_com | 14,942 |
| shopify_cepfd6_w6_myshopify_com | 13,633 |
| shopify_89cb49_6d_myshopify_com | 13,421 |
| shopify_tapetenshop_lv_myshopify_com | 13,338 |
| shopify_wizardi_myshopify_com | 12,808 |
| shopify_ritzjewelryinc_myshopify_com | 12,215 |

Top-10 ≈ 146,664 rows (~42.6%). Only `013554_2c` cleanly hit the 18,500 per-merchant cap; the rest tail off — consistent with a long-tail catalog hour rather than a saturated cap-bound fan-out.

## Comparison vs. prior hours

| Hour (UTC) | Rows | Threshold | Margin |
|---|---:|---:|---:|
| 2026-06-05 00:00–01:00 | 208,694 | 150,000 | +58,694 (+39.1%) PASS |
| 2026-06-05 01:00–02:00 | 312,321 | 150,000 | +162,321 (+108.2%) PASS |
| 2026-06-05 02:00–03:00 | 98,001 | 150,000 | −51,999 (−34.7%) FAIL |
| 2026-06-05 03:00–04:00 | 202,843 | 150,000 | +52,843 (+35.2%) PASS |
| 2026-06-05 04:00–05:00 | 108,948 | 150,000 | −41,052 (−27.4%) FAIL |
| 2026-06-05 05:00–06:00 | 149,999 | 150,000 | −1 (−0.0007%) FAIL |
| 2026-06-05 06:00–07:00 | 261,059 | 150,000 | +111,059 (+74.0%) PASS |
| 2026-06-05 07:00–08:00 | 216,205 | 150,000 | +66,205 (+44.1%) PASS |
| 2026-06-05 08:00–09:00 | 324,081 | 150,000 | +174,081 (+116.1%) PASS |
| 2026-06-05 09:00–10:00 | 1,319,762 | 150,000 | +1,169,762 (+779.8%) PASS |
| 2026-06-05 10:00–11:00 | 1,016,100 | 150,000 | +866,100 (+577.4%) PASS |
| **2026-06-05 11:00–12:00** | **344,468** | **150,000** | **+194,468 (+129.6%) PASS** |

Hour-over-hour: **−671,632 (−66.1%)** vs. 10:00 — throughput stepped down sharply from the 1M-row peak but still clears the threshold by a healthy margin. Six consecutive PASSes (06→11). Prior hourly values are quoted from BUY-31006's hour-close snapshot; per [[project-buy30902-null-source-delete-reconciliation]] those numbers are the authoritative threshold-decision counts.

## Action taken
- No failure-report child issue created (PASS).
- BUY-31038 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" remains active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 13:00 UTC will measure 12:00–13:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
