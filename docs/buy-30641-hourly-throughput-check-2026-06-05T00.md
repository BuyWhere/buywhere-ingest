# BUY-30641 — Hourly throughput check (2026-06-05 00:00–01:00 UTC)

**Result: PASS — no failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T00:00:00+00:00 → 2026-06-05T01:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **208,694** |
| Real rows (excluding synthetic merchants & `example.com`) | **208,694** |
| Threshold | 150,000 |
| Margin vs. threshold | **+58,694 (+39.1%)** |

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 00:00:00+00' AND created_at < '2026-06-05 01:00:00+00'`.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL filter → 0 rows.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_kytebaby | 2,665 |
| shopify_stevemadden | 2,099 |
| shopify_winsornewton | 1,557 |
| shopify_pet_centar_rs | 1,317 |
| shopify_primary | 1,310 |
| shopify_sudhasilk_com | 1,307 |
| shopify_stylo_mx | 1,283 |
| shopify_homeschoolbuyersclub_com | 1,283 |
| shopify_minuman_com | 1,259 |
| shopify_speedfactoryracing_net | 1,258 |

Top-10 contributed ~15,300 rows (~7.3% of the hour). The distribution remains broad — fleet-wide contribution rather than a single-merchant spike.

## Comparison vs. prior hours

| Hour (UTC) | Rows | Threshold | Margin |
|---|---:|---:|---:|
| 2026-06-04 21:00–22:00 | 182,795 | 150,000 | +32,795 (+21.9%) PASS |
| 2026-06-04 22:00–23:00 | 119,120 | 150,000 | −30,880 (−20.6%) FAIL |
| 2026-06-04 23:00–00:00 | 50,350 | 150,000 | −99,650 (−66.4%) FAIL |
| **2026-06-05 00:00–01:00** | **208,694** | **150,000** | **+58,694 (+39.1%) PASS** |

Hour-over-hour: +158,344 (+314.5%). Throughput rebounded sharply from the 23:00 trough — first hour clearing threshold since 21:00.

## Action taken
- **No failure-report child issue created** (above threshold).
- BUY-30641 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. It produced this run issue at the top of this hour.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
