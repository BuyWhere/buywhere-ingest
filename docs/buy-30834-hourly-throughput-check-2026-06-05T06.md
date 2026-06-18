# BUY-30834 — Hourly throughput check (2026-06-05 05:00–06:00 UTC)

**Result: FAIL — failure-report child issue [BUY-30840](/BUY/issues/BUY-30840) created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T05:00:00+00:00 → 2026-06-05T06:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **149,999** |
| Real rows (excluding synthetic merchants & `example.com`) | **149,999** |
| Threshold | 150,000 |
| Margin vs. threshold | **−1 (−0.0007%)** |

This is the closest near-miss FAIL recorded. Strictly below 150,000 → failure report required per [BUY-29861](/BUY/issues/BUY-29861).

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 05:00:00+00' AND created_at < '2026-06-05 06:00:00+00'` → **149,999**.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Source mix this hour

| Source | Rows | Share |
|---|---:|---:|
| shopify (main loop) | 117,694 | 78.5% |
| shopify_pleasurements | 7,900 | 5.3% |
| shopify_natori | 7,800 | 5.2% |
| shopify_gymshark | 7,388 | 4.9% |
| shopify_aloyoga | 3,605 | 2.4% |
| shopify_soulcycle | 1,751 | 1.2% |
| shopify_keen | 1,275 | 0.9% |
| shopify_hanro | 1,015 | 0.7% |
| shopify_eberjey | 660 | 0.4% |
| shopify_hankypanky | 556 | 0.4% |
| shopify_megafood | 105 | 0.1% |
| shopify_cosabella | 101 | 0.1% |
| shopify_reebok | 81 | 0.1% |
| shopify_tonal | 48 | 0.0% |
| shopify_cora | 14 | 0.0% |
| shopify_livonlabs | 5 | 0.0% |
| shopify_newchapter | 1 | 0.0% |

**100% shopify family** (one sustained loop + ~16 dedicated shopper lanes). `ebay_us` contributed 5,092 rows last hour and 0 rows this hour — its absence is exactly what kept the hour under the 150k bar. No `s3cdx` / CC-MAIN / Google Shopping contribution.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_pleasurements | 7,900 |
| shopify_natori | 7,800 |
| shopify_gymshark | 7,388 |
| shopify_aloyoga | 3,605 |
| shopify_soulcycle | 1,751 |
| shopify_binasarts_com | 1,500 |
| shopify_bikescootercity_com_au | 1,500 |
| shopify_pushmycart_in | 1,500 |
| shopify_livestainable_co_za | 1,499 |
| shopify_bighello_in | 1,442 |

Top-10 ≈ 35,985 rows (~24%). Distribution is broad outside the named shopper lanes. No single-merchant spike or collapse. The shortfall is *breadth* (only the shopify family is writing), not *depth*.

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
| **2026-06-05 05:00–06:00** | **149,999** | **150,000** | **−1 (−0.0007%) FAIL** |

Hour-over-hour: **+41,051 (+37.7%)**. Throughput is climbing back toward threshold but the lane mix did not quite clear it. One additional row from any active lane (or 1 minute of `ebay_us` shopping) would have made this a PASS.

## Action taken
- **Failure-report child issue [BUY-30840](/BUY/issues/BUY-30840) created** under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, priority `critical`, status `todo`.
- BUY-30834 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 07:00 UTC will measure 06:00–07:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
