# BUY-30869 — Hourly throughput check (2026-06-05 06:00–07:00 UTC)

**Result: PASS — 261,059 ≥ 150,000. No failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T06:00:00+00:00 → 2026-06-05T07:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **261,059** |
| Real rows (excluding synthetic merchants & `example.com`) | **261,059** |
| Threshold | 150,000 |
| Margin vs. threshold | **+111,059 (+74.0%)** |

Strictly above 150,000 → no failure report required per [BUY-29861](/BUY/issues/BUY-29861).

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 06:00:00+00' AND created_at < '2026-06-05 07:00:00+00'` → **261,059**.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Source mix this hour

| Source | Rows | Share |
|---|---:|---:|
| shopify (main loop) | 243,323 | 93.2% |
| shopify_brighton | 3,277 | 1.3% |
| shopify_step2 | 3,116 | 1.2% |
| shopify_astridandmiyu | 2,059 | 0.8% |
| shopify_baublebar | 1,891 | 0.7% |
| shopify_trytheworld | 1,707 | 0.7% |
| shopify_missoma | 1,234 | 0.5% |
| shopify_tateossian | 1,183 | 0.5% |
| shopify_melissadoug | 976 | 0.4% |
| shopify_sparkpaws | 538 | 0.2% |
| shopify_jennybird | 428 | 0.2% |
| shopify_godiva | 359 | 0.1% |
| shopify_littletikes | 314 | 0.1% |
| shopify_anaissa | 197 | 0.1% |
| shopify_instantpot | 121 | 0.0% |
| shopify_kettleandfire | 99 | 0.0% |
| shopify_pandasaurus | 77 | 0.0% |
| shopify_tower28 | 66 | 0.0% |
| shopify_blendtec | 53 | 0.0% |
| shopify_roguepet | 17 | 0.0% |
| shopify_bokksu | 13 | 0.0% |
| shopify_graze | 9 | 0.0% |
| shopify_tatcha | 1 | 0.0% |
| shopify_beautyblender | 1 | 0.0% |

**100% shopify family** — main `shopify` loop dominated at 243k (93%) with ~23 dedicated shopper lanes contributing the remainder. No `ebay_us`, `s3cdx`/CC-MAIN, or Google Shopping rows. The main-loop surge — not new sources — drove the +111k margin.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_develop_goldmarket_myshopify_com | 18,500 |
| shopify_designsbyaymara_myshopify_com | 15,000 |
| shopify_restaurantsupply_com | 15,000 |
| shopify_brandsamurai_myshopify_com | 12,524 |
| shopify_burch_fishing_tackle_myshopify_com | 12,123 |
| shopify_absolute_autoguard_myshopify_com | 11,747 |
| shopify_ebm_lux_time_myshopify_com | 9,704 |
| shopify_accbbe_e9_myshopify_com | 7,048 |
| shopify_gemsroot_com | 6,750 |
| shopify_burfordgardenco_myshopify_com | 6,220 |

Top-10 ≈ 114,616 rows (~44%). Distribution shifted toward large-catalog Shopify long-tail merchants — a healthy breadth-with-depth mix.

## Comparison vs. prior hours

| Hour (UTC) | Rows | Threshold | Margin |
|---|---:|---:|---:|
| 2026-06-04 22:00–23:00 | 119,120 | 150,000 | −30,880 (−20.6%) FAIL |
| 2026-06-04 23:00–00:00 | 50,350 | 150,000 | −99,650 (−66.4%) FAIL |
| 2026-06-05 00:00–01:00 | 208,694 | 150,000 | +58,694 (+39.1%) PASS |
| 2026-06-05 01:00–02:00 | 312,321 | 150,000 | +162,321 (+108.2%) PASS |
| 2026-06-05 02:00–03:00 | 98,001 | 150,000 | −51,999 (−34.7%) FAIL |
| 2026-06-05 03:00–04:00 | 202,843 | 150,000 | +52,843 (+35.2%) PASS |
| 2026-06-05 04:00–05:00 | 108,948 | 150,000 | −41,052 (−27.4%) FAIL |
| 2026-06-05 05:00–06:00 | 149,999 | 150,000 | −1 (−0.0007%) FAIL |
| **2026-06-05 06:00–07:00** | **261,059** | **150,000** | **+111,059 (+74.0%) PASS** |

Hour-over-hour: **+111,060 (+74.0%)**. Recovery from the 05:00 near-miss is decisive; the main shopify loop produced 243k on its own this hour, clearing the threshold without needing `ebay_us` or other non-shopify lanes.

## Action taken
- No failure-report child issue created (PASS).
- BUY-30869 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 08:00 UTC will measure 07:00–08:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
