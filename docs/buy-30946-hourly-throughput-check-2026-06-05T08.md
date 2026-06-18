# BUY-30946 — Hourly throughput check (2026-06-05 08:00–09:00 UTC)

**Result: PASS — 324,081 ≥ 150,000. No failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T08:00:00+00:00 → 2026-06-05T09:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **324,081** |
| Real rows (excluding synthetic merchants & `example.com`) | **324,081** |
| Threshold | 150,000 |
| Margin vs. threshold | **+174,081 (+116.1%)** |

Strictly above 150,000 → no failure report required per [BUY-29861](/BUY/issues/BUY-29861).

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 08:00:00+00' AND created_at < '2026-06-05 09:00:00+00'` → **324,081**.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Source mix this hour

| Source | Rows | Share |
|---|---:|---:|
| shopify (main loop) | 266,828 | 82.3% |
| shopify_barnesnoble | 17,180 | 5.3% |
| shopify_47brand | 11,300 | 3.5% |
| shopify_johnnieo | 10,600 | 3.3% |
| shopify_burga | 6,700 | 2.1% |
| shopify_neweracap | 6,200 | 1.9% |
| shopify_trueclassic | 1,694 | 0.5% |
| shopify_southerntide | 1,462 | 0.5% |
| shopify_ministryofsupply | 370 | 0.1% |
| shopify_legends | 323 | 0.1% |
| shopify_wandrd | 274 | 0.1% |
| shopify_ryze | 252 | 0.1% |
| shopify_thinktank | 145 | 0.0% |
| shopify_nomatic | 111 | 0.0% |
| shopify_orbitkey2 | 110 | 0.0% |
| shopify_cado | 105 | 0.0% |
| shopify_orgain | 102 | 0.0% |
| shopify_olly | 73 | 0.0% |
| shopify_healthade | 62 | 0.0% |
| shopify_vitacup | 61 | 0.0% |
| shopify_olipop | 48 | 0.0% |
| shopify_vitalplan | 30 | 0.0% |
| shopify_untuckit | 28 | 0.0% |
| shopify_woodies | 18 | 0.0% |
| shopify_mudwtr | 4 | 0.0% |
| shopify_spigen | 1 | 0.0% |

**~100% shopify family** — main `shopify` loop produced 266.8k (82.3%) with 25 dedicated shopper lanes contributing the remainder. No `ebay_us`, `s3cdx`/CC-MAIN, `google_shopping`. Main-loop output rose to 266.8k vs. 186.5k in the prior hour (+43%), comfortably clearing the threshold solo.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_ribescasals_com | 18,500 |
| shopify_littlethingsme_com | 18,459 |
| shopify_emiliejoly_com | 18,176 |
| shopify_drownedworldrecords_com | 17,704 |
| shopify_barnesnoble | 17,180 |
| shopify_tecisoft_com | 15,500 |
| shopify_order2india_com | 15,000 |
| shopify_superlative_ro | 12,237 |
| shopify_47brand | 11,300 |
| shopify_johnnieo | 10,600 |

Top-10 ≈ 154,656 rows (~47.7%). Long-tail Shopify catalogs continue to dominate — five merchants near the ~18k per-merchant cap drove the top of the table.

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
| **2026-06-05 08:00–09:00** | **324,081** | **150,000** | **+174,081 (+116.1%) PASS** |

Hour-over-hour: **+107,876 (+49.9%)** vs. 07:00, the strongest hour since 01:00. Three consecutive PASSes; main `shopify` loop alone (266.8k) cleared the threshold by +78%.

Note on [[project-buy30902-null-source-delete-reconciliation]]: Dash's bounded delete may retroactively reduce historical row counts on re-query. The 08:00–09:00 result is queried once at hour-close so this snapshot is the authoritative count for the streak/threshold decision.

## Action taken
- No failure-report child issue created (PASS).
- BUY-30946 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" remains active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 10:00 UTC will measure 09:00–10:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
