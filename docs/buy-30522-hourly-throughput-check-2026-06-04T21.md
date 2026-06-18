# BUY-30522 — Hourly throughput check (2026-06-04 21:00–22:00 UTC)

**Result: PASS — no failure-report issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of BUY-29861 assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-04T21:00:00+00:00 → 2026-06-04T22:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **182,795** |
| Real rows (excluding synthetic merchants & `example.com`) | **182,795** |
| Threshold | 150,000 |
| Margin over threshold | +32,795 (+21.9%) |

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-04 21:00:00+00' AND created_at < '2026-06-04 22:00:00+00'`.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL filter excluded → 0 rows.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_showmeyourmumu | 4,107 |
| shopify_nakedcph | 1,687 |
| shopify_carkart_com | 1,500 |
| shopify_fiperformance_com | 1,500 |
| shopify_strictlydiscs_com | 1,500 |
| shopify_fashamo_com | 1,497 |
| shopify_kith | 1,493 |
| shopify_averdo_com | 1,462 |
| shopify_kamerastore_com | 1,448 |
| shopify_pueblodirect_com | 1,367 |

## Action taken
- **No new failure-report issue created** (threshold met).
- BUY-30522 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC, assigned to Oracle. It produced this run issue at 2026-06-04T22:01:02Z.

## Parent
- BUY-29861 — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
