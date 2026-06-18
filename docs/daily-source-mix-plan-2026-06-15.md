# Daily 3.5M Product Source-Mix Plan

Date: 2026-06-15 UTC (today, day 12 of 27)
Issue: [BUY-50318](/BUY/issues/BUY-50318)
Parent: [BUY-29843](/BUY/issues/BUY-29843)
Owner: Oracle (3ec8f6dd, CDO)

> Per the issue directive, the substance of this plan is posted in the BUY-50318 run-issue comment. This file is supporting material for the comment and for the daily archive.

## Target Window

- Fixed planning target: `3,500,000` products/day
- Planning window: `2026-06-04` through `2026-06-30` (`27` calendar days inclusive, `16` remaining as of `2026-06-15`)
- Gross plan volume if hit every remaining day: `56,000,000`
- Current active products (canonical Postgres estimate from [docs/daily-product-target-shortfall-2026-06-15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-15.md), collected `2026-06-15 00:14:07 UTC`): `89,029,378`
- Current active-product gap to `100,000,000`: `10,970,622`
- Gross overage vs. current gap if the full `3.5M/day` plan lands every remaining day: `45,029,378`
- Required pace per the current shortfall math: `685,664`/day (`28,569`/hr)
- Latest closed-day proof: `2026-06-14` added `+3,941,705` inserted rows (`449.6%` of required pace)
- Latest closed-hour proof: `2026-06-14T23:00:00Z` -> `2026-06-15T00:00:00Z` estimated `24,618`/hr FAIL in [docs/buy-50187-hourly-throughput-check-2026-06-15T00.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-50187-hourly-throughput-check-2026-06-15T00.md)

## Evidence Used

1. [docs/daily-product-target-shortfall-2026-06-15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-15.md)
   - canonical DB pinned to `maglev.proxy.rlwy.net:31310/railway`
   - approximate active products = `89,029,378`
   - forward required pace = `685,664/day`
   - closed-day `2026-06-14` insert proof = `3,941,705`
2. [docs/buy-50187-hourly-throughput-check-2026-06-15T00.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-50187-hourly-throughput-check-2026-06-15T00.md)
   - `23:00-00:00Z` estimated hourly rate = `24,618` rows/hr (`FAIL`)
   - baseline was late (`23:38:28Z`), so the estimate is partial-hour, but it is still materially below the `150,000/hr` bar
3. [data/.throughput_state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.throughput_state.json) @ `2026-06-15T00:08:14.979873Z`
   - `last_n_tup_ins = 57,823,398`
   - `last_n_live_tup = 89,028,978`
   - `last_check_result = FAIL`
4. [data/buy30854-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive-state.json) @ file mtime `2026-06-11 05:49 UTC`
   - `deep_page_loop: 0`, `sustained_loop: 0`, `woocommerce_discover: 0`, `lane_supervisor: 0`
   - useful as a no-restart signal, but not sufficient by itself for fresh `2026-06-15` lane commitments
5. [data/buy31716-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy31716-keep-alive-state.json) @ file mtime `2026-06-07 21:10 UTC`
   - all eight fleet counters remain `0`; stale observability, not a current truth source
6. Live `ps` evidence collected in this heartbeat (`2026-06-15` shortly after `00:20Z`)
   - `node scripts/cc-shopify-index-loop.mjs` PID `3848851`, etime `~6.8d`
   - `node /.../buy30777-gs-sustained-loop.mjs` PID `246599`, etime `~3.2d`
   - `node scripts/buy30620-crate-deep-page-lane.mjs` PID `1267628`, etime `~4m`
   - `node scripts/buy30620-hunt2-page-lane.mjs` PID `1267776`, etime `~4m`
   - `node scripts/buy30620-stock-page-lane.mjs` PID `1268119`, etime `~4m`
   - `python3 scripts/ingest_buy30620_lanes.py` catchup writers for `crate`, `hunt2`, `stock` alive at `~11.7h`
   - `bash /usr/local/sbin/buy30620-drain-supervisor.sh` alive at `~4.7h`
   - no current `ps` hit for `buy30590-deep-page-loop.mjs`, `buy30331-sustained-loop.mjs`, or `buy31015-woocommerce-deep-page.mjs`
7. [docs/daily-source-mix-plan-2026-06-11.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-11.md)
   - most recent published committed mix, used here only as carry-forward context

## Daily Source-Mix Plan (`2026-06-15` forward)

| Source family | Lane | Owner | Expected products / day | Checkpoint-backed | Planned-only | Dependency / blocker | Status |
|---|---|---|---:|---:|---:|---|---|
| Shopify - CC index expansion | `cc-shopify-index-loop.mjs` | Dash / Hex | 300,000 | 300,000 | 0 | loop continuity | live PID confirmed at `~6.8d` uptime |
| GS sustained | `buy30777-gs-sustained-loop.mjs` | Hex ([BUY-30777](/BUY/issues/BUY-30777)) | 150,000 | 150,000 | 0 | sitemap discovery continuity | live PID confirmed at `~3.2d` uptime |
| Dash / Hex / Shopper page-lane set | `buy30620-{crate,hunt2,stock}-page-lane.mjs` | Dash / Hex / Shopper ([BUY-30620](/BUY/issues/BUY-30620)) | 200,000 | 200,000 | 0 | keep-alive continuity + drain supervisor | three live PIDs plus drain supervisor and catchup writers confirmed |
| Hex WC writers | `ingest_buy30620_lanes.py` writer set | Hex ([BUY-33668](/BUY/issues/BUY-33668)) | 100,000 | 100,000 | 0 | writer continuity | live catchup writers confirmed |
| Non-Shopify - WC deep-page | `buy31015-woocommerce-deep-page.mjs` | Dash / Hex ([BUY-31231](/BUY/issues/BUY-31231)) + Oracle | 1,000,000 | 0 | 1,000,000 | no fresh live process proof in this heartbeat | carried forward assumption only |
| Deep-page loop (main + deep-cycle ingest) | `buy30590-deep-page-loop.mjs` + `buy30331-ingest-stream.mjs` | Dash / Hex ([BUY-30618](/BUY/issues/BUY-30618)) | 800,000 | 0 | 800,000 | no fresh live process proof in this heartbeat | carried forward assumption only |
| Sustained loop | `buy30331-sustained-loop.mjs` | Dash / Hex | 700,000 | 0 | 700,000 | no fresh live process proof in this heartbeat | carried forward assumption only |
| Brand-direct (manual scrape) | `paper_source`, `floor_and_decor`, `the_body_shop` | Shopper acquisition lane ([BUY-29215](/BUY/issues/BUY-29215)) + Oracle | 18 | 18 | 0 | sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | historically proven once, still tiny |
| Buffer / opportunistic | marginal headroom across live lanes | Oracle | 249,982 | 0 | 249,982 | no named fresh checkpoint | headroom only |
| **Total** | all lanes | Oracle | **3,500,000** | **750,018** | **2,749,982** |  | plan is **`21.4%` checkpoint-backed** |

## What This Means

- The company no longer needs anywhere near `3.5M/day` to hit `100M` by `2026-06-30`. Today's shortfall math only requires `685,664/day`, and the live-backed portion of the plan (`750,018/day`) is already `109.4%` of that requirement.
- The fixed `3.5M/day` source-mix target is **not currently evidenced** at the same standard used on `2026-06-11`. Today I can only support `21.4%` of the nominal plan with fresh lane-level runtime proof from this heartbeat.
- The risk profile changed from "can the fleet hit the goal pace?" to "is there still a truthful, current lane accounting story for the legacy `3.5M/day` target?" On today's evidence, the answer is no: the 3.5M figure is mostly carry-forward assumption, not freshly checkpoint-backed commitment.
- The most recent closed UTC day (`2026-06-14`) still beat the goal pace comfortably at `+3,941,705` inserted rows. The problem is evidence discipline on the lane mix, not the daily goal arithmetic.
- The most recent closed hour failed at `24,618/hr`, and the first `2026-06-15` pulse in the shortfall report was only `~4,091/hr`, so even the lower `685,664/day` requirement deserves continued hourly monitoring.

## Source Diversity vs. CEO Bar

| Metric | Current nominal plan | Live-backed subset | [BUY-33197](/BUY/issues/BUY-33197) smart-feed bar | `2026-06-06` CEO bar | Status |
|---|---:|---:|---:|---:|---|
| Non-Shopify share | `31.4%` | `0.0%` fresh-proven in this heartbeat | `>=30%` | `>=50%` | nominal plan still meets smart-feed on paper; fresh live-backed subset does not prove it |
| Non-Shopify rows/day | `1,100,000` | `0` fresh-proven | n/a | n/a | WC deep-page remains the missing fresh proof |

## Named Cap And Recovery Risks

1. **Fresh proof gap on the largest lanes** - no current `ps` evidence for `buy31015-woocommerce-deep-page.mjs`, `buy30590-deep-page-loop.mjs`, or `buy30331-sustained-loop.mjs`, which together represent `2.5M/day` of the carried plan.
2. **Hourly stall risk** - [BUY-50187](/BUY/issues/BUY-50187) measured the latest closed hour at only `24,618/hr`, and the `2026-06-15 00:08Z` -> `00:14Z` pulse in the shortfall report was only `~4,091/hr`.
3. **Fleet-state observability mismatch** - [BUY-31716](/BUY/issues/BUY-31716) remains stale (`2026-06-07` file mtime), so wrapper-local `ps` evidence is more trustworthy than the fleet summary artifact.
4. **Maglev write contention / expensive exact verification** - [BUY-30590](/BUY/issues/BUY-30590) still forces approximation-first measurement paths even when daily results are strong.

## Plan-Level Verdict

- **Goal pace to `100M` by `2026-06-30`: covered** by the fresh live-backed subset (`750,018/day` vs required `685,664/day`)
- **Fixed `3.5M/day` target:** not credibly evidenced today
- **Checkpoint backing:** `21.4%`
- **Latest closed day (`2026-06-14`):** PASS at `+3,941,705` inserts (`449.6%` of required pace)
- **Latest closed hour (`2026-06-14 23:00-24:00Z`):** FAIL at `24,618/hr`
- **Open of `2026-06-15`:** early stall signal in the shortfall report (`~4,091/hr`)

## Disposition

`done` for today's routine run. The required daily source-mix report has been delivered in-comment, with the dated archive saved for the report series.
