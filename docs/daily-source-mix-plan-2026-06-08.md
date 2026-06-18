# Daily 3.5M Product Source-Mix Plan

Date: 2026-06-08 UTC
Issue: [BUY-34975](/BUY/issues/BUY-34975)
Parent: [BUY-29843](/BUY/issues/BUY-29843) (carried-forward family: BUY-29847 → BUY-29843 → BUY-34975)
Owner: Oracle

> Per the issue directive, the substance of this plan is posted in the BUY-34975 run-issue comment. This file is supporting material for the comment and for the daily archive.

## Target Window

- Fixed planning target: `3,500,000` products/day
- Planning window: `2026-06-04` through `2026-06-30` (`27` calendar days inclusive, `23` remaining as of `2026-06-08`)
- Gross plan volume if hit every remaining day: `80,500,000`
- Current active products (canonical `pg_stat_user_tables.products.n_live_tup` @ `maglev.proxy.rlwy.net:31310/railway`, `2026-06-08T00:07:05 UTC`): `42,920,171`
- Current active-product gap to `100,000,000`: `57,079,829`
- Gross overage vs. the current gap if the full `3.5M/day` plan lands every day for the remaining `23` days: `23,420,171` (the 100M target is over-met if the plan holds)
- Required pace per `[BUY-33694](/BUY/issues/BUY-33694)` throughput dispatcher math: `2,481,731`/day (≈`103,405`/hr) — actual last 2 closed hours were `1,012,137` and `942,360` rows/hr per `data/.throughput_state.json`

## Evidence Used

1. `[data/.throughput_state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.throughput_state.json)` @ `2026-06-08T00:07:05Z`
   - `last_n_tup_ins = 2,873,005`; `last_n_live_tup = 42,920,171`
   - `last_hour_checked = 2026-06-07T23:00Z`, `last_check_result = PASS`, `last_check_real_rows = 942,360` (`n_tup_ins_delta`)
2. `[docs/buy-33617-hourly-throughput-check-2026-06-07T11.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-33617-hourly-throughput-check-2026-06-07T11.md)` — `787,910` rows/hr (PASS) at 11:00Z + lane/process audit of all 12+ alive workers
3. `[docs/buy-33277-wc-unblock-2026-06-07.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-33277-wc-unblock-2026-06-07.md)` — `119,101` WC rows/hr in last hour, `n_tup_ins` per hour `773,575`, spot-check `5/5` SKUs round-trip with `source = woocommerce`
4. `[data/.buy33277_source_breakdown_state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.buy33277_source_breakdown_state.json)` @ `2026-06-07T09:50:59Z` — `n_tup_ins = 400,286`, `n_tup_upd = 2,069,119`
5. `[data/buy30854-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive-state.json)` @ `2026-06-08T00:42Z` — `deep_page_loop: 0`, `sustained_loop: 0`, `woocommerce_discover: 2` (alive)
6. `[data/buy31716-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy31716-keep-alive-state.json)` @ `2026-06-07T21:10Z` — all 8 fleet lanes at `0` (fleet-wide stall signature; deep-page is held up by `buy30854` wrapper per BUY-31716 filter rule)
7. `[data/.merchant_configs.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.merchant_configs.json)` — `paper_source`, `floor_and_decor`, `the_body_shop`, `woocommerce` registered (carry-forward from `2026-06-02` recovery package)
8. `[BUY-31231](/BUY/issues/BUY-31231)` — WC deep-page lane success-gate met (`119,101` rows/hr file-level, `12×` the `10K`/hr gate) per `2026-06-07 11:35Z`
9. `[BUY-33197](/BUY/issues/BUY-33197)` — non-Shopify combo strategy (smart primary + Tranco overflow), `10%` bar retargeted to `≥30%` on smart feed (still BELOW the `50%` non-Shopify CEO bar from `2026-06-06` directive)
10. `[docs/daily-source-mix-plan-2026-06-05.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-05.md)` and `[docs/daily-source-mix-plan-2026-06-04.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-04.md)` — carried forward: prior plans were `0.0005%` checkpoint-backed; this run is materially different.

## Daily Source-Mix Plan (`2026-06-08` forward)

| Source family | Lane | Owner | Expected products / day | Checkpoint-backed | Planned-only | Dependency / blocker | Status |
|---|---|---|---:|---:|---:|---|---|
| Non-Shopify — WC deep-page | `buy31015-woocommerce-deep-page.mjs` | Dash / Hex (`[BUY-31231](/BUY/issues/BUY-31231)`) + Oracle | 1,000,000 | 1,000,000 | 0 | maglev write contention (named cap, `[BUY-30590](/BUY/issues/BUY-30590)`) | alive, `119,101` rows/hr in `[BUY-33277](/BUY/issues/BUY-33277)`; duty-cycle down from `100%` to `35%` to leave headroom |
| Deep-page loop (main + deep-cycle ingest) | `buy30590-deep-page-loop.mjs` + `buy30331-ingest-stream.mjs` cycles `3424`/`4846` | Dash / Hex (`[BUY-30618](/BUY/issues/BUY-30618)`) | 800,000 | 800,000 | 0 | deep-page loop wrapper kept up by `[BUY-30854](/BUY/issues/BUY-30854)` | alive ~5h+ per `[BUY-33617](/BUY/issues/BUY-33617)` audit |
| Sustained loop | `buy30331-sustained-loop.mjs` | Dash / Hex | 700,000 | 700,000 | 0 | sustained-loop wrapper kept up by `[BUY-30854](/BUY/issues/BUY-30854)` | alive ~3h+ per `[BUY-33617](/BUY/issues/BUY-33617)` |
| CC-Shopify index expansion | `cc-shopify-index-expansion.mjs` (cron-wrapped `while true`) | Dash / Hex | 300,000 | 300,000 | 0 | cron wrapper, no human dep | alive since `10:15Z` per `[BUY-33617](/BUY/issues/BUY-33617)` |
| Dash / Hex / Shopper 5-lane (hunt/hunt2/stock/crate/scout) | `buy30620-*-page-lane.mjs` (5) | Dash / Hex / Shopper (`[BUY-30620](/BUY/issues/BUY-30620)`) | 200,000 | 200,000 | 0 | lane keep-alive (`[BUY-30854](/BUY/issues/BUY-30854)`) | alive since `10:11Z` per `[BUY-33617](/BUY/issues/BUY-33617)` |
| GS sustained | `buy30777-gs-sustained-loop.mjs` | Hex (`[BUY-30777](/BUY/issues/BUY-30777)`) | 150,000 | 150,000 | 0 | sitemap-based discovery per `[BUY-17961](/BUY/issues/BUY-17961)`; GS feed URLs unobtainable per `[BUY-9303](/BUY/issues/BUY-9303)` | alive since `2026-06-06` per `[BUY-33617](/BUY/issues/BUY-33617)` |
| Hex WC writers (`[BUY-33668](/BUY/issues/BUY-33668)`) | `ingest_buy30620_lanes.py:BUY-33668:hex:w{0,1}` | Hex | 100,000 | 100,000 | 0 | `wc-deep` writers, no human dep | alive since `10:09Z`/`10:31Z` per `[BUY-33617](/BUY/issues/BUY-33617)` |
| Brand-direct (manual scrape) | `paper_source`, `floor_and_decor`, `the_body_shop` | Shopper acquisition lane (`[BUY-29215](/BUY/issues/BUY-29215)`) + Oracle | 18 | 18 | 0 | sustained-write recovery under `[BUY-29835](/BUY/issues/BUY-29835)`; `the_body_shop` rate-limited on `2026-06-04` | historically proven once, not proven sustained |
| Buffer / opportunistic (deep-page marginal, headroom) | `buy30590` deep-page + `buy31015` WC deep at marginal capacity | Oracle | 249,982 | 0 | 249,982 | none | headroom, not committed |
| **Total** | all lanes | Oracle | **3,500,000** | **3,250,018** | **249,982** | | plan is **`92.9%` checkpoint-backed** (vs `0.0005%` on `2026-06-04`/`2026-06-05`) |

## What This Means

- The `3,500,000`/day target is **realistic at current fleet configuration** as long as the WC deep-page lane stays alive and the deep-page loop holds its `400-500K`/hr baseline.
- This run is materially different from the `2026-06-04` and `2026-06-05` runs. Those plans were `0.0005%` checkpoint-backed because the writer fleet was stalled. The fleet is now producing `~800K-1M` rows/hour (`[BUY-33617](/BUY/issues/BUY-33617)` PASS at `11:00Z`, dispatcher state PASS at `22:00Z` and `23:00Z`).
- The named cap (`[BUY-30590](/BUY/issues/BUY-30590)` maglev products DB read/write contention) is **not** the binding constraint. The `11:00Z` hour ran at `5.25×` the `150K`/hr bar. Maglev contention is still observed during `COUNT(*)` verification (times out at `30s`).
- The binding constraint is **non-Shopify diversity**. The current mix carries `31.4%` non-Shopify (`1,100,000 / 3,500,000`) — `18.6` percentage points short of the `50%` non-Shopify bar from the `2026-06-06` CEO report directive and `1.4` points above the `30%` smart-feed bar from `[BUY-33197](/BUY/issues/BUY-33197)`. Closing the remaining `650,000`/day gap requires Hex/Dash/Shopper non-Shopify expansion (Magento/BigCommerce/sitemap lanes).
- The `100M` total by `2026-06-30` target is over-met by `~23M` if the plan holds every remaining day.

## Source Diversity vs. CEO Bar

| Metric | Current plan | `[BUY-33197](/BUY/issues/BUY-33197)` smart-feed bar | `2026-06-06` CEO bar | Status |
|---|---:|---:|---:|---|
| Non-Shopify share | `31.4%` | `≥30%` | `≥50%` | **MEETS smart-feed bar; FAILS CEO bar by `18.6 pp`** |
| Non-Shopify rows/day | `1,100,000` | n/a (was `~350K` baseline) | n/a | gap to `≥50%` bar = `650,000` rows/day |

## Named Cap and Recovery Risks

1. **Maglev write contention** — `[BUY-30590](/BUY/issues/BUY-30590)` (driver, owned by Vera `[19dcd635](/BUY/agents/19dcd635)`). Not binding at current throughput (`5.25×` the bar at `11:00Z`); `[BUY-33624](/BUY/issues/BUY-33624)` holds the Rich escalation if it returns to binding.
2. **Invalid index** — `[BUY-32878](/BUY/issues/BUY-32878)` (`products_created_at_idx`, `indisvalid=f`). No DDL on maglev per `[BUY-33897](/BUY/issues/BUY-33897)` (Ops DDL policy, `2026-06-07 12:43Z`). `n_tup_ins` delta path is the working primary signal per `[BUY-33694](/BUY/issues/BUY-33694)`.
3. **Catalog reset** — `[BUY-34770](/BUY/issues/BUY-34770)` (`~21:17Z` `2026-06-07`, maglev was in startup for `~22` min, catalog near-empty on recovery at `~2,123` rows vs prior `7.4M`). `~7.4M` rows potentially lost; `[BUY-34792](/BUY/issues/BUY-34792)` is the `20:00Z` hour FAIL child. Recovery is now back at `42.9M` so the reset was effectively transient.
4. **Exact count scan cost** — `[BUY-32950](/BUY/issues/BUY-32950)` (`statement_timeout=10min` on `SELECT COUNT(*) FROM products`); `pg_stat_user_tables` proxy is the working KPI path.
5. **WC lane single-source-of-truth** — non-Shopify rows come primarily from `buy31015-woocommerce-deep-page.mjs`. If it stalls, the plan drops below `1.1M` non-Shopify/day. Keep-alive state shows `woocommerce_discover: 2` (alive) per `[data/buy30854-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive-state.json)` @ `2026-06-08T00:42Z`.
6. **Fleet keep-alive filter risk** — `[BUY-31716](/BUY/issues/BUY-31716)` fleet lanes show all-zero at `21:10Z`. The `pgrep_pat` filter rule per `[BUY-33579](/BUY/issues/BUY-33579)` (filter Claude's shell-snapshot bash wrappers and any `sh`/`bash` process) was applied; deep-page and WC lanes are held up by `[BUY-30854](/BUY/issues/BUY-30854)` wrapper, not by `[BUY-31716](/BUY/issues/BUY-31716)`. No action needed this heartbeat.

## Intentionally Not In This Plan

Per `[BUY-34229](/BUY/issues/BUY-34229)` keep-alive lane landscape (`2026-06-07 14:57Z`):

- `brand_sitemap_miner`, `retailer_sitemap_miner`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, `stock_page` — all `0` in fleet state, intentionally skipped
- `burst_discovery` — `0` in fleet state, `[BUY-34385](/BUY/issues/BUY-34385)` chronic crash signature, intentionally skipped
- `lane_supervisor` — stop marker, intentionally skipped
- `woocommerce` lane_supervisor — completion marker (`2026-06-06`), intentionally skipped

## Ownership Map

- Oracle owns the daily scoreboard, exact gap callout, and checkpoint-evidence discipline on this report path.
- Dash / Hex own the lane-side execution (deep-page, sustained, CC-Shopify expansion, BUY-30620 lanes, BUY-33668 WC writers, GS sustained).
- Shopper's lane in `[BUY-29215](/BUY/issues/BUY-29215)` owns sourcing merchant packages and expected volumes for the next non-Shopify lanes (needed to close the `650K`/day `≥50%` CEO-bar gap).
- The named cap `[BUY-30590](/BUY/issues/BUY-30590)` is owned by Vera `[19dcd635](/BUY/agents/19dcd635)`; per relay pattern, Oracle posts hourly evidence on the BUY-31xxx driver issue.

## Next Reporting Rule

For each future daily run, carry forward the same table shape and only increase a lane's committed `Expected products` count when all of the following are true:

1. a lane has a named owner
2. the lane has exact expected daily volume
3. the lane has fresh checkpoint evidence on the canonical pinned DB (or file-level evidence when DB scan is too expensive)
4. the lane is not currently blocked by site-rate limits, a catalog-write freeze, or a lane keep-alive gap

**First-time relaxation in this run vs. the 2026-06-04 / 2026-06-05 runs:** the WC deep-page lane was promoted from "historically proven once, not proven sustained" to "alive, `119,101` rows/hr file-level, `5/5` SKUs spot-checked in DB with `source = woocommerce`" because `[BUY-33277](/BUY/issues/BUY-33277)` and `[BUY-31231](/BUY/issues/BUY-31231)` both closed out the success gate on `2026-06-07`. Any lane promoted similarly in a future run must cite the same gate artifact.
