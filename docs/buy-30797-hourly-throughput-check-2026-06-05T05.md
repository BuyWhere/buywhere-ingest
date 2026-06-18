# BUY-30797 — Hourly throughput check (2026-06-05 04:00–05:00 UTC)

**Result: FAIL — failure-report child issue [BUY-30801](/BUY/issues/BUY-30801) created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T04:00:00+00:00 → 2026-06-05T05:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **108,948** |
| Real rows (excluding synthetic merchants & `example.com`) | **108,948** |
| Threshold | 150,000 |
| Margin vs. threshold | **−41,052 (−27.4%)** |

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 04:00:00+00' AND created_at < '2026-06-05 05:00:00+00'`.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Source mix this hour

| Source | Rows | Share |
|---|---:|---:|
| shopify | 103,856 | 95.3% |
| ebay_us | 5,092 | 4.7% |

Only the shopify sustained-loop and `ebay_us` shopper lane wrote this hour. No `s3cdx` / CC-MAIN / Google Shopping contribution.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| ebay_us | 5,092 |
| shopify_quickshipkeys_com | 1,500 |
| shopify_autoshopping24_com | 1,500 |
| shopify_vipoutlet_com | 1,463 |
| shopify_beadaholique_com | 1,351 |
| shopify_kantagiri_com | 1,286 |
| shopify_bloompharmacy_com | 1,279 |
| shopify_sanskrutihomes_in | 1,258 |
| shopify_activ_eg | 1,254 |
| shopify_karachibookshop_com | 1,252 |

Broad distribution outside `ebay_us`; no single-merchant spike or collapse. The shortfall is *breadth* (only two source lanes active), not *depth*.

## Comparison vs. prior hours

| Hour (UTC) | Rows | Threshold | Margin |
|---|---:|---:|---:|
| 2026-06-04 22:00–23:00 | 119,120 | 150,000 | −30,880 (−20.6%) FAIL |
| 2026-06-04 23:00–00:00 | 50,350 | 150,000 | −99,650 (−66.4%) FAIL |
| 2026-06-05 00:00–01:00 | 208,694 | 150,000 | +58,694 (+39.1%) PASS |
| 2026-06-05 01:00–02:00 | 312,321 | 150,000 | +162,321 (+108.2%) PASS |
| 2026-06-05 02:00–03:00 | 98,001 | 150,000 | −51,999 (−34.7%) FAIL |
| 2026-06-05 03:00–04:00 | 202,843 | 150,000 | +52,843 (+35.2%) PASS |
| **2026-06-05 04:00–05:00** | **108,948** | **150,000** | **−41,052 (−27.4%) FAIL** |

Hour-over-hour: −93,895 (−46.3%). The 03:00 PASS streak broke after one hour — same drained-CC-MAIN-lane pattern as [BUY-30736](/BUY/issues/BUY-30736) at 02:00 UTC.

## Action taken
- **Failure-report child issue [BUY-30801](/BUY/issues/BUY-30801) created** under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, priority `critical`, status `todo`.
- BUY-30797 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 06:00 UTC will measure 05:00–06:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
