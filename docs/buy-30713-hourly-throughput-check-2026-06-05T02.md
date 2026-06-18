# BUY-30713 — Hourly throughput check (2026-06-05 02:00–03:00 UTC)

**Result: FAIL — failure-report child issue [BUY-30736](/BUY/issues/BUY-30736) created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T02:00:00+00:00 → 2026-06-05T03:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **98,001** |
| Real rows (excluding synthetic merchants & `example.com`) | **98,001** |
| Threshold | 150,000 |
| Margin vs. threshold | **−51,999 (−34.7%)** |

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 02:00:00+00' AND created_at < '2026-06-05 03:00:00+00'`.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Source mix this hour

| Source | Rows |
|---|---:|
| shopify | 98,001 (100%) |

Only the shopify sustained-loop wrote this hour. No `s3cdx` / CC-MAIN / Google Shopping contribution.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_dirtcheep_com | 1,261 |
| shopify_misscayces_com | 1,260 |
| shopify_bonussuperstore_co_uk | 1,258 |
| shopify_woodturnerscatalog_com | 1,254 |
| shopify_xoticbrands_net | 1,253 |
| shopify_feidclothes_com | 1,252 |
| shopify_robertsfurniture_com | 1,252 |
| shopify_farmaciascurie_cl | 1,251 |
| shopify_mastershop_com_au | 1,251 |
| shopify_festinachile_cl | 1,250 |

Broad distribution; no single-merchant spike or collapse. The shortfall is *breadth* (one source lane active), not *depth*.

## Comparison vs. prior hours

| Hour (UTC) | Rows | Threshold | Margin |
|---|---:|---:|---:|
| 2026-06-04 20:00–21:00 | 122,383 | 150,000 | −27,617 (−18.4%) FAIL |
| 2026-06-04 21:00–22:00 | 182,795 | 150,000 | +32,795 (+21.9%) PASS |
| 2026-06-04 22:00–23:00 | 119,120 | 150,000 | −30,880 (−20.6%) FAIL |
| 2026-06-04 23:00–00:00 | 50,350 | 150,000 | −99,650 (−66.4%) FAIL |
| 2026-06-05 00:00–01:00 | 208,694 | 150,000 | +58,694 (+39.1%) PASS |
| 2026-06-05 01:00–02:00 | 312,321 | 150,000 | +162,321 (+108.2%) PASS |
| **2026-06-05 02:00–03:00** | **98,001** | **150,000** | **−51,999 (−34.7%) FAIL** |

Hour-over-hour: −214,320 (−68.6%). The two-hour PASS streak (00:00 + 01:00 UTC) broke. Matches the drained-CC-MAIN-lane pattern diagnosed in [BUY-30645](/BUY/issues/BUY-30645).

## Action taken
- **Failure-report child issue [BUY-30736](/BUY/issues/BUY-30736) created** under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, priority `critical`, status `todo`.
- BUY-30713 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 04:00 UTC will measure 03:00–04:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
