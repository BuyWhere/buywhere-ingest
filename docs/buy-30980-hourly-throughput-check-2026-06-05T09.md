# BUY-30980 — Hourly throughput check (2026-06-05 09:00–10:00 UTC)

**Result: PASS — 1,319,762 ≥ 150,000. No failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T09:00:00+00:00 → 2026-06-05T10:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **1,319,762** |
| Real rows (excluding synthetic merchants & `example.com`) | **1,319,762** |
| Threshold | 150,000 |
| Margin vs. threshold | **+1,169,762 (+779.8%)** |

Strictly above 150,000 → no failure report required per [BUY-29861](/BUY/issues/BUY-29861).

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 09:00:00+00' AND created_at < '2026-06-05 10:00:00+00'` → **1,319,762**.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Source mix this hour

| Source | Rows | Share |
|---|---:|---:|
| shopify (all lanes) | 1,318,412 | 99.9% |
| woocommerce | 1,350 | 0.1% |

Single-platform run — Shopify family delivered 1.318M rows (99.9%), the largest hour of the day by a wide margin. No `ebay_us`, `s3cdx`/CC-MAIN, `google_shopping`. Main `shopify` loop plus dedicated shopper lanes saturated the per-merchant cap across many catalogs.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_agradi_com | 18,487 |
| shopify_paradigme_fr | 18,251 |
| shopify_bubbleroom_dk | 18,151 |
| shopify_bubbleroom_no | 17,840 |
| shopify_derpycards_ca | 17,737 |
| shopify_hobium_com | 16,498 |
| shopify_chitoroshop_com | 15,998 |
| shopify_ramseyoutdoor_com | 15,997 |
| shopify_quiltingbookspatternsandnotions_com | 15,989 |
| shopify_billyhydemusic_com_au | 15,000 |

Top-10 ≈ 169,948 rows (~12.9% — much flatter long-tail than prior hours). Dozens of Shopify catalogs each hit ~15–18.5k near the per-merchant cap, consistent with a broad fan-out cycle.

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
| **2026-06-05 09:00–10:00** | **1,319,762** | **150,000** | **+1,169,762 (+779.8%) PASS** |

Hour-over-hour: **+995,681 (+307.2%)** vs. 08:00 — the day's clear high-water mark and a 4× jump. Four consecutive PASSes. Prior hourly values are quoted from BUY-30946's hour-close snapshot; per [[project-buy30902-null-source-delete-reconciliation]] those numbers are the authoritative threshold-decision counts even if a re-query now would differ slightly.

## Action taken
- No failure-report child issue created (PASS).
- BUY-30980 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" remains active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 11:00 UTC will measure 10:00–11:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
