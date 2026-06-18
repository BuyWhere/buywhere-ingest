# BUY-31006 — Hourly throughput check (2026-06-05 10:00–11:00 UTC)

**Result: PASS — 1,016,100 ≥ 150,000. No failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T10:00:00+00:00 → 2026-06-05T11:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **1,016,100** |
| Real rows (excluding synthetic merchants & `example.com`) | **1,016,100** |
| Threshold | 150,000 |
| Margin vs. threshold | **+866,100 (+577.4%)** |

Strictly above 150,000 → no failure report required per [BUY-29861](/BUY/issues/BUY-29861).

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 10:00:00+00' AND created_at < '2026-06-05 11:00:00+00'` → **1,016,100**.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Source mix this hour

| Source | Rows | Share |
|---|---:|---:|
| shopify (all lanes) | 1,016,100 | 100.0% |

Pure-Shopify hour — no `woocommerce`, `ebay_us`, `s3cdx`/CC-MAIN, `google_shopping` rows landed. Main `shopify` loop plus dedicated shopper lanes carried the entire million-row throughput.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_clarkesgolf_co_uk | 18,500 |
| shopify_tmcmotorsport_com | 18,500 |
| shopify_fabledgames_store | 18,500 |
| shopify_evotech_performance_com | 18,500 |
| shopify_stuffssaver_com | 18,500 |
| shopify_lamoodcomics_ca | 18,500 |
| shopify_axionnow_com | 18,500 |
| shopify_delibertiboutique_com | 18,500 |
| shopify_agradi_de | 18,491 |
| shopify_moonbehindthehill_ie | 18,353 |

Top-10 ≈ 184,844 rows (~18.2%). Eight of the top ten cleanly hit the 18,500 per-merchant cap, with `agradi_de` and `moonbehindthehill_ie` just under — consistent with a saturated cap-bound fan-out across many catalogs (long tail similar to the prior hour).

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
| **2026-06-05 10:00–11:00** | **1,016,100** | **150,000** | **+866,100 (+577.4%) PASS** |

Hour-over-hour: **−303,662 (−23.0%)** vs. 09:00 but still the second-largest hour of the day. Five consecutive PASSes (06→10). Prior hourly values are quoted from BUY-30980's hour-close snapshot; per [[project-buy30902-null-source-delete-reconciliation]] those numbers are the authoritative threshold-decision counts.

## Action taken
- No failure-report child issue created (PASS).
- BUY-31006 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" remains active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 12:00 UTC will measure 11:00–12:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
