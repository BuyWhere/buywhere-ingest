# BUY-30597 — Hourly throughput check (2026-06-04 23:00–00:00 UTC)

**Result: FAIL — failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of BUY-29861 assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-04T23:00:00+00:00 → 2026-06-05T00:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **50,350** |
| Real rows (excluding synthetic merchants & `example.com`) | **50,350** |
| Threshold | 150,000 |
| Shortfall vs. threshold | **−99,650 (−66.4%)** |

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-04 23:00:00+00' AND created_at < '2026-06-05 00:00:00+00'`.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/`merchant_id` filter → 0 rows.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_ryderwear | 2,132 |
| shopify_jonathanadler | 1,414 |
| shopify_fullyfilmy_in | 1,267 |
| shopify_katib_pk | 1,266 |
| shopify_gant_in | 1,263 |
| shopify_galoir_com | 1,259 |
| shopify_galeriaavanti_com | 1,253 |
| shopify_kenelestore_jp | 1,250 |
| shopify_kidzvilla_online | 1,250 |
| shopify_kilol_in | 1,250 |

Top-10 merchants contributed ~14,000 rows (~28% of the hour). The rest of the fleet produced only ~36,000 rows — fleet-wide weakness, not a single-merchant collapse.

## Comparison vs. prior hours

| Hour (UTC) | Rows | Threshold | Margin |
|---|---:|---:|---:|
| 2026-06-04 20:00–21:00 | 122,383 | 150,000 | −27,617 (−18.4%) FAIL |
| 2026-06-04 21:00–22:00 | 182,795 | 150,000 | +32,795 (+21.9%) PASS |
| 2026-06-04 22:00–23:00 | 119,120 | 150,000 | −30,880 (−20.6%) FAIL |
| **2026-06-04 23:00–00:00** | **50,350** | **150,000** | **−99,650 (−66.4%) FAIL** |

Hour-over-hour: −68,770 (−57.7%). Throughput collapsed in the just-completed hour — three of the last four hours failed, this one by the widest margin.

## Action taken
- **New failure-report child issue created**: [BUY-30633](/BUY/issues/BUY-30633) under [BUY-29861](/BUY/issues/BUY-29861), assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.
- BUY-30597 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. It produced this run issue at the top of this hour.

## Parent
- BUY-29861 — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
- Sustained-discovery blocker on the parent: [BUY-30590](/BUY/issues/BUY-30590) — Oracle owns continuous fleet runtime; tonight's slide matches the idle-discovery pattern BUY-30590 was opened to fix.
