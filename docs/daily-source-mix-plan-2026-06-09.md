# Daily 3.5M Product Source-Mix Plan

Date: 2026-06-09 UTC
Issue: [BUY-36475](/BUY/issues/BUY-36475)
Parent: [BUY-29843](/BUY/issues/BUY-29843) (carried-forward family: BUY-29847 -> BUY-29843 -> BUY-36475)
Owner: Oracle

> Per the issue directive, the substance of this plan is posted in the BUY-36475 run-issue comment. This file is supporting material for the comment and for the daily archive.

## Target Window

- Fixed planning target: `3,500,000` products/day
- Planning window: `2026-06-04` through `2026-06-30` (`27` calendar days inclusive, `22` remaining as of `2026-06-09`)
- Gross plan volume if hit every remaining day: `77,000,000`
- Current active products (canonical Postgres estimate from [docs/daily-product-target-shortfall-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-09.md), collected `2026-06-09 00:12:47 UTC`): `55,374,575`
- Current active-product gap to `100,000,000`: `44,625,425`
- Gross overage vs. the current gap if the full `3.5M/day` plan lands every day for the remaining `22` days: `32,374,575`
- Required pace per the current shortfall math: `2,028,429`/day (about `84,518`/hr)
- Latest closed-hour evidence: `126,890` rows/hr FAIL in `22:00-23:00Z` and `229,921` rows/hr PASS in `23:00-00:00Z`, both on canonical `n_tup_ins` delta proof

## Evidence Used

1. [docs/daily-product-target-shortfall-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-09.md)
   - canonical DB is correctly pinned to `maglev.proxy.rlwy.net:31310/railway`
   - approximate active products = `55,374,575`
   - forward required pace = `2,028,429/day`
   - closed-day `2026-06-08` conservative insert proof = `12,900,511`
2. [docs/buy-36280-hourly-throughput-check-2026-06-08T22.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-36280-hourly-throughput-check-2026-06-08T22.md)
   - `22:00-23:00Z` hourly rate = `126,890` rows/hr (FAIL)
3. [docs/buy-36417-hourly-throughput-check-2026-06-08T23.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-36417-hourly-throughput-check-2026-06-08T23.md)
   - `23:00-00:00Z` hourly rate = `229,921` rows/hr (PASS)
4. [data/.throughput_state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.throughput_state.json) @ file mtime `2026-06-08 23:07:56 UTC`
   - last saved baseline: `last_n_tup_ins = 19,207,565`, `last_n_live_tup = 55,833,044`
5. [data/buy30854-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive-state.json) @ file mtime `2026-06-09 00:21:52 UTC`
   - `deep_page_loop: 0`, `sustained_loop: 0`, `woocommerce_discover: 2`
6. [data/buy31716-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy31716-keep-alive-state.json) @ file mtime `2026-06-07 21:10:02 UTC`
   - all 8 fleet lanes at `0` (same stale fleet-state signature as yesterday; wrapper-owned lanes remain the more trustworthy signal)
7. [docs/buy-33277-wc-unblock-2026-06-07.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-33277-wc-unblock-2026-06-07.md)
   - last-hour file-level WC proof = `119,101` rows
   - spot-check `5/5` SKUs round-tripped into DB with `source = woocommerce`
   - `n_tup_ins` pace at unblock time = `773,575/hr`
8. [data/.buy33277_source_breakdown_state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.buy33277_source_breakdown_state.json) @ `2026-06-07T09:50:59Z`
   - stored `n_tup_ins = 400,286`, `n_tup_upd = 2,069,119`
9. [data/.merchant_configs.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.merchant_configs.json)
   - `paper_source`, `floor_and_decor`, `the_body_shop`, `woocommerce` registered
10. [docs/daily-source-mix-plan-2026-06-08.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-08.md)
   - prior committed lane mix and checkpoint-backing standard

## Daily Source-Mix Plan (`2026-06-09` forward)

| Source family | Lane | Owner | Expected products / day | Checkpoint-backed | Planned-only | Dependency / blocker | Status |
|---|---|---|---:|---:|---:|---|---|
| Non-Shopify - WC deep-page | `buy31015-woocommerce-deep-page.mjs` | Dash / Hex ([BUY-31231](/BUY/issues/BUY-31231)) + Oracle | 1,000,000 | 1,000,000 | 0 | maglev write contention ([BUY-30590](/BUY/issues/BUY-30590)) | keep-alive still shows `woocommerce_discover: 2`; last named file-level proof remains `119,101` rows/hr |
| Deep-page loop (main + deep-cycle ingest) | `buy30590-deep-page-loop.mjs` + `buy30331-ingest-stream.mjs` cycles | Dash / Hex ([BUY-30618](/BUY/issues/BUY-30618)) | 800,000 | 800,000 | 0 | wrapper continuity under [BUY-30854](/BUY/issues/BUY-30854) | carried forward from the `2026-06-08` plan; latest closed day still far above required pace |
| Sustained loop | `buy30331-sustained-loop.mjs` | Dash / Hex | 700,000 | 700,000 | 0 | wrapper continuity under [BUY-30854](/BUY/issues/BUY-30854) | carried forward from the `2026-06-08` plan |
| CC-Shopify index expansion | `cc-shopify-index-expansion.mjs` | Dash / Hex | 300,000 | 300,000 | 0 | cron wrapper, no human dep | carried forward from the `2026-06-08` plan |
| Dash / Hex / Shopper 5-lane set | `buy30620-*-page-lane.mjs` (5) | Dash / Hex / Shopper ([BUY-30620](/BUY/issues/BUY-30620)) | 200,000 | 200,000 | 0 | keep-alive continuity under [BUY-30854](/BUY/issues/BUY-30854) | carried forward from the `2026-06-08` plan |
| GS sustained | `buy30777-gs-sustained-loop.mjs` | Hex ([BUY-30777](/BUY/issues/BUY-30777)) | 150,000 | 150,000 | 0 | sitemap-based discovery per [BUY-17961](/BUY/issues/BUY-17961) | carried forward from the `2026-06-08` plan |
| Hex WC writers | `ingest_buy30620_lanes.py:BUY-33668:hex:w{0,1}` | Hex ([BUY-33668](/BUY/issues/BUY-33668)) | 100,000 | 100,000 | 0 | `wc-deep` writers, no human dep | carried forward from the `2026-06-08` plan |
| Brand-direct (manual scrape) | `paper_source`, `floor_and_decor`, `the_body_shop` | Shopper acquisition lane ([BUY-29215](/BUY/issues/BUY-29215)) + Oracle | 18 | 18 | 0 | sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | historically proven once, not proven sustained |
| Buffer / opportunistic | marginal deep-page / WC headroom | Oracle | 249,982 | 0 | 249,982 | no named checkpoint yet | headroom only, not committed lane proof |
| **Total** | all lanes | Oracle | **3,500,000** | **3,250,018** | **249,982** |  | plan is **`92.9%` checkpoint-backed** |

## What This Means

- The `3,500,000/day` plan still clears the **current** pace requirement by a wide margin. Today's forward requirement is only `2,028,429/day`, so the problem is no longer raw volume arithmetic.
- The binding constraint remains **source diversity and lane stability**, not whether the fleet can theoretically push enough rows on a good day. Closed-day `2026-06-08` already proved at least `12,900,511` inserted rows on the canonical DB.
- This plan is still anchored on the same lane mix published on `2026-06-08`. I did not increase any lane commitment today because there is no new per-lane checkpoint that would justify a higher committed number.
- Hourly volatility is real. The last two closed hours split `FAIL` then `PASS` (`126,890` then `229,921` rows/hr), so the daily plan is plausible but not yet hour-to-hour smooth.

## Source Diversity vs. CEO Bar

| Metric | Current plan | [BUY-33197](/BUY/issues/BUY-33197) smart-feed bar | `2026-06-06` CEO bar | Status |
|---|---:|---:|---:|---|
| Non-Shopify share | `31.4%` | `>=30%` | `>=50%` | **MEETS smart-feed bar; FAILS CEO bar by `18.6 pp`** |
| Non-Shopify rows/day | `1,100,000` | n/a | n/a | gap to `>=50%` bar = `650,000` rows/day |

## Named Cap and Recovery Risks

1. **Hourly instability** - [BUY-36292](/BUY/issues/BUY-36292) was required for the `22:00-23:00Z` miss even though the next hour recovered. The plan is feasible at the day level but still fragile hour-to-hour.
2. **Maglev write contention** - [BUY-30590](/BUY/issues/BUY-30590) remains the named cap. It does not block today's daily arithmetic, but it still forces fallback measurement paths and makes exact verification expensive.
3. **Invalid index / no ANALYZE** - [BUY-32878](/BUY/issues/BUY-32878) (`products_created_at_idx`, `indisvalid=f`) still prevents cheap exact count/query paths on `products`.
4. **WC lane single-source-of-truth risk** - non-Shopify rows still rely primarily on `buy31015-woocommerce-deep-page.mjs`. If that lane stalls, the plan loses the bulk of its non-Shopify share immediately.
5. **Fleet-state observability mismatch** - [BUY-31716](/BUY/issues/BUY-31716) still shows all-zero fleet lanes in its stale state file, so wrapper-local keep-alive evidence remains more trustworthy than the fleet summary artifact for this report.

## Ownership Map

- Oracle owns the daily scoreboard, gap math, and checkpoint-evidence discipline on this report path.
- Dash / Hex own lane-side execution for deep-page, sustained, CC-Shopify expansion, the BUY-30620 lane family, GS sustained, and WC writers.
- Shopper's lane in [BUY-29215](/BUY/issues/BUY-29215) owns the next non-Shopify merchant packages needed to close the remaining `650,000/day` gap to the CEO's `>=50%` non-Shopify bar.
- Vera ([19dcd635](/BUY/agents/19dcd635)) owns the named cap [BUY-30590](/BUY/issues/BUY-30590); Oracle's role here is evidence and daily mix accounting, not lane execution.

## Next Reporting Rule

For each future daily run, keep the same table shape and only increase a lane's committed `Expected products` count when all of the following are true:

1. a lane has a named owner
2. the lane has exact expected daily volume
3. the lane has fresh checkpoint evidence on the canonical pinned DB (or an explicitly accepted file-level substitute when DB scans are too expensive)
4. the lane is not currently blocked by site-rate limits, a catalog-write freeze, or a lane keep-alive gap
