# BUY-30457 — Hourly throughput check (2026-06-04 21:00–22:00 UTC)

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
- Connection at: 2026-06-04T22:27:23Z.
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-04 21:00:00+00' AND created_at < '2026-06-04 22:00:00+00'`.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart`.
- `example.com` URL filter excluded: 0 rows matched.

## Last 6 hours context (real rows)

| Hour (UTC) | Total rows | Real rows | vs 150k |
|---|---:|---:|---|
| 15:00 | 3 | 2 | FAIL |
| 16:00 | 22,182 | 22,182 | FAIL |
| 17:00 | 1,480,829 | 1,480,829 | PASS |
| 18:00 | 2,506,163 | 2,506,163 | PASS |
| 19:00 | 452,209 | 452,209 | PASS |
| 20:00 | 122,383 | 122,383 | FAIL |
| **21:00** | **182,795** | **182,795** | **PASS (this hour)** |

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
- BUY-30457 closed `done` with this DB-proof record.

## Parent
- BUY-29861 — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
