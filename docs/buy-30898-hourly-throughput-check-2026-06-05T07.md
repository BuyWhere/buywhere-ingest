# BUY-30898 — Hourly throughput check (2026-06-05 07:00–08:00 UTC)

**Result: PASS — 216,205 ≥ 150,000. No failure-report child issue created.**

## Threshold
- Net products added to canonical PostgreSQL ≥ 150,000 in the just-completed hour → no issue created.
- Net products added < 150,000 → create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-05T07:00:00+00:00 → 2026-06-05T08:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **216,205** |
| Real rows (excluding synthetic merchants & `example.com`) | **216,205** |
| Threshold | 150,000 |
| Margin vs. threshold | **+66,205 (+44.1%)** |

Strictly above 150,000 → no failure report required per [BUY-29861](/BUY/issues/BUY-29861).

## DB proof
- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (read from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 07:00:00+00' AND created_at < '2026-06-05 08:00:00+00'` → **216,205**.
- Synthetic merchants excluded (none matched in window): `shopnow, techdepot, fastshop, megamart, smartcart, valuehub, easycart, quickbuy, primestore, globalmart` → 0 rows.
- `example.com` URL/merchant filter → 0 rows.

## Source mix this hour

| Source | Rows | Share |
|---|---:|---:|
| shopify (main loop) | 186,542 | 86.3% |
| shopify_lulugeorgia | 10,047 | 4.6% |
| shopify_barnesnoble | 7,400 | 3.4% |
| shopify_craneandcanopy | 2,668 | 1.2% |
| shopify_outofprint | 1,431 | 0.7% |
| shopify_parachute | 1,301 | 0.6% |
| shopify_society6 | 800 | 0.4% |
| shopify_storq | 793 | 0.4% |
| shopify_storiarts | 728 | 0.3% |
| shopify_owlcrate | 533 | 0.2% |
| shopify_linoto | 414 | 0.2% |
| shopify_hatch | 403 | 0.2% |
| shopify_momcozy | 402 | 0.2% |
| shopify_illumicrate | 399 | 0.2% |
| shopify_cultiver | 366 | 0.2% |
| shopify_knockknock | 342 | 0.2% |
| shopify_framebridge | 250 | 0.1% |
| shopify_haakaa | 200 | 0.1% |
| shopify_ceaco | 188 | 0.1% |
| shopify_schoolhouse | 171 | 0.1% |
| shopify_roughlinen | 150 | 0.1% |
| shopify_sollybaby | 146 | 0.1% |
| shopify_maholi | 127 | 0.1% |
| shopify_bollandbranch | 79 | 0.0% |
| shopify_earthmama | 77 | 0.0% |
| shopify_magnatiles | 51 | 0.0% |
| shopify_spectra | 46 | 0.0% |
| shopify_healthybaby | 42 | 0.0% |
| shopify_lillebaby | 33 | 0.0% |
| shopify_nanobebe | 26 | 0.0% |
| shopify_rileyhome | 22 | 0.0% |
| shopify_drbrowns | 15 | 0.0% |
| shopify_benchmade | 11 | 0.0% |
| shopify_kytebaby | 1 | 0.0% |
| google_shopping | 1 | 0.0% |

**~100% shopify family** — main `shopify` loop produced 186.5k (86.3%) with ~33 dedicated shopper lanes contributing the remainder. No `ebay_us`, `s3cdx`/CC-MAIN. One stray `google_shopping` row. Main-loop output dropped from 243k to 186.5k vs. prior hour but still cleared the threshold solo.

## Top merchants this hour (top 10 by row count)

| Merchant | Rows |
|---|---:|
| shopify_kidswearcollective_com | 18,500 |
| shopify_agradi_nl | 18,490 |
| shopify_jadlamracingmodels_com | 18,477 |
| shopify_asiangroceronline_com_au | 16,250 |
| shopify_jdsports_my | 14,739 |
| shopify_eirehobbies_com | 13,307 |
| shopify_furniturefactoryca_com | 11,616 |
| shopify_lulugeorgia | 10,047 |
| shopify_rambosfurniture_com | 8,582 |
| shopify_barnesnoble | 7,400 |

Top-10 ≈ 137,408 rows (~63.6%). Large-catalog Shopify long-tail merchants dominated — concentration is higher than 06:00–07:00 (44%), driven by four merchants at ~18k each capped near the per-merchant ceiling.

## Comparison vs. prior hours

| Hour (UTC) | Rows | Threshold | Margin |
|---|---:|---:|---:|
| 2026-06-04 23:00–00:00 | 50,350 | 150,000 | −99,650 (−66.4%) FAIL |
| 2026-06-05 00:00–01:00 | 208,694 | 150,000 | +58,694 (+39.1%) PASS |
| 2026-06-05 01:00–02:00 | 312,321 | 150,000 | +162,321 (+108.2%) PASS |
| 2026-06-05 02:00–03:00 | 98,001 | 150,000 | −51,999 (−34.7%) FAIL |
| 2026-06-05 03:00–04:00 | 202,843 | 150,000 | +52,843 (+35.2%) PASS |
| 2026-06-05 04:00–05:00 | 108,948 | 150,000 | −41,052 (−27.4%) FAIL |
| 2026-06-05 05:00–06:00 | 149,999 | 150,000 | −1 (−0.0007%) FAIL |
| 2026-06-05 06:00–07:00 | 261,059 | 150,000 | +111,059 (+74.0%) PASS |
| **2026-06-05 07:00–08:00** | **216,205** | **150,000** | **+66,205 (+44.1%) PASS** |

Hour-over-hour: **−44,854 (−17.2%)** vs. 06:00 but still a comfortable PASS. Two consecutive PASS hours after a rough overnight stretch (4 FAILs in 5 hours between 02:00 and 06:00). The main `shopify` loop alone (186.5k) cleared the threshold this hour.

## Action taken
- No failure-report child issue created (PASS).
- BUY-30898 closed `done` with this DB-proof record.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" remains active, fires `0 * * * *` UTC, assigned to Oracle. Next fire 09:00 UTC will measure 08:00–09:00.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
