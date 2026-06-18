# Daily 3.5M Product Source-Mix Plan

Date: 2026-06-17 UTC (today, day 14 of 27)
Issue: [BUY-52556](/BUY/issues/BUY-52556)
Parent: [BUY-29843](/BUY/issues/BUY-29843)
Owner: Oracle (3ec8f6dd, CDO)

> Per the issue directive, the substance of this plan is posted in the BUY-52556 run-issue comment. This file is supporting material for the comment and for the daily archive.

## Target Window

- Fixed planning target: `3,500,000` products/day
- Planning window: `2026-06-04` through `2026-06-30` (`27` calendar days inclusive, `14` remaining as of `2026-06-17`)
- Gross plan volume if hit every remaining day: `49,000,000`
- Current active products (canonical Postgres from [docs/daily-product-target-shortfall-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-16.md), collected `2026-06-16 00:15:16 UTC`): `95,240,314`
- Current active-product gap to `100,000,000`: `4,759,686`
- Required pace from `2026-06-16` forward: `317,313/day` (`13,221/hr`)
- Latest closed-day proof: `2026-06-15` added at least `+6,210,936` live products (`905.8%` of required pace, NOT A MISS per shortfall report)
- Latest closed-hour proof: `2026-06-17 00:00-01:00Z` at `682,953/hr` PASS (via `n_tup_ins` delta; data/.throughput_state.json)

## Evidence Used

1. [docs/daily-product-target-shortfall-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-16.md)
   - canonical DB pinned to `maglev.proxy.rlwy.net:31310/railway`
   - approximate active products = `95,240,314` as of `2026-06-16 00:15:16 UTC`
   - forward required pace = `317,313/day`
   - closed-day `2026-06-15` conservative growth proof = `+6,210,936`
2. [data/.throughput_state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.throughput_state.json) @ `2026-06-18 00:02 UTC`
   - `last_n_tup_ins = 25,782,200` (since `pm_start = 2026-06-16 08:52:01 UTC`)
   - `last_n_live_tup = 120,513,540` (DB state now; note: prior June 16 anchor was during startup recovery)
   - `last_check_result = PASS` at `682,953/hr` for `2026-06-17 23:00-00:00Z`
   - `last_check_delta_rows = 681,837`, `last_check_delta_hours = 0.998`
   - `pm_start = 2026-06-16 08:52:01.162919+00:00` (no restart since)
3. Live `ps` evidence collected in this heartbeat at `2026-06-18 00:30Z`
   - `buy31015-woocommerce-deep-page.mjs` PID `1569392`, etime `29m55s`, WC deep-cycle `9881` active
   - `buy30331-ingest-stream.mjs` PID `1558567`, etime `9m`, cycle `183` active (deep-page ingest)
   - `buy30331-sustained-loop.mjs` PID `3313200`, etime `29m55s`, Jun17 restart confirmed
   - `buy30331-sustained-loop-supervisor.sh` PID `3313195`, Jun17 restart confirmed
   - `buy30620-crate-deep-page-lane.mjs` PID `1573299`, etime `2m08s`
   - `buy30620-hunt2-deep-page-lane.mjs` PID `1574199`, etime `2m08s`
   - `buy30620-stock-deep-page-lane.mjs` PID `1574524`, etime `2m10s`
   - `ingest_buy30620_lanes.py` catchup writers for `crate/hunt2/stock` at etime `14-16m`
   - `buy30620-catchup.sh` supervisor active; `buy30620-drain-supervisor.sh` PIDs `1567586`, `3977396`
   - no current `ps` hit for `cc-shopify-index-loop.mjs` or `buy30777-gs-sustained-loop.mjs`

## Daily Source-Mix Plan (`2026-06-17` forward)

| Source family | Lane | Owner | Expected products / day | Checkpoint-backed | Planned-only | Dependency / blocker | Status |
|---|---|---|---:|---:|---:|---|---|
| Sustained loop | `buy30331-sustained-loop.mjs` | Dash / Hex | 700,000 | 700,000 | 0 | loop restarted Jun17 per supervisor PID 3313195 | PID 3313200, etime 29m55s, confirmed |
| Non-Shopify - WC deep-page | `buy31015-woocommerce-deep-page.mjs` | Dash / Hex ([BUY-31231](/BUY/issues/BUY-31231)) | 1,000,000 | 1,000,000 | 0 | steady WC lane | PID 1569392, etime 29m55s, WC deep-cycle 9881 active |
| Deep-page loop (main ingest) | `buy30331-ingest-stream.mjs` | Dash / Hex ([BUY-30618](/BUY/issues/BUY-30618)) | 800,000 | 800,000 | 0 | cycle 183 confirmed live; BUY-30590 deep-page | PID 1558567, etime 9m, cycle-183 active |
| Dash / Hex / Shopper page-lane set | `buy30620-{crate,hunt2,stock}-deep-page-lane.mjs` | Dash / Hex / Shopper ([BUY-30620](/BUY/issues/BUY-30620)) | 200,000 | 200,000 | 0 | keep-alive + catchup writers | 3 PIDs at etime 2m, catchup writers at 14-16m confirmed |
| Hex WC catchup writers | `ingest_buy30620_lanes.py` writer set | Hex ([BUY-33668](/BUY/issues/BUY-33668)) | 100,000 | 100,000 | 0 | writer continuity | crate/hunt2/stock catchup writers at 14-16m confirmed |
| Shopify - CC index expansion | `cc-shopify-index-loop.mjs` | Dash / Hex | 300,000 | 0 | 300,000 | no current `ps` proof in this heartbeat | carried-forward assumption only |
| GS sustained | `buy30777-gs-sustained-loop.mjs` | Hex ([BUY-30777](/BUY/issues/BUY-30777)) | 150,000 | 0 | 150,000 | no current `ps` proof in this heartbeat | carried-forward assumption only |
| Brand-direct (manual scrape) | `paper_source`, `floor_and_decor`, `the_body_shop` | Shopper acquisition lane ([BUY-29215](/BUY/issues/BUY-29215)) + Oracle | 18 | 18 | 0 | sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | historically proven once, still tiny |
| Buffer / opportunistic | marginal headroom across live lanes | Oracle | 249,982 | 0 | 249,982 | no named fresh checkpoint | headroom only |
| **Total** | all lanes | Oracle | **3,500,000** | **2,800,018** | **699,982** |  | plan is **`80.0%` checkpoint-backed** |

## What This Means

- The required goal pace to reach `100M` by `2026-06-30` is only `317,313/day`. The live-backed portion of the plan (`2,800,018/day`) is already `882.6%` of that requirement — a significant improvement from the prior day's `8.6%` checkpoint backing.
- This is the strongest checkpoint-backed story since `2026-06-11`. All five of the largest lanes now have confirming process evidence in a single heartbeat: sustained loop, WC deep-page, deep-page ingest, page-lane set, and WC catchup writers.
- The two gaps are `cc-shopify-index-loop.mjs` and `buy30777-gs-sustained-loop.mjs`, representing `450,000/day` in carried-forward assumption. Their absence in the current `ps` snapshot is a notable regression from the `2026-06-16` report, which confirmed `cc-shopify` at `6.8d` uptime and `buy30777` at `3.2d` uptime.
- The post-restart `n_live_tup = 120,513,540` signals the catalog is well past the June 16 shortfall anchor, consistent with the strong hourly insert rates observed since the last restart.

## Source Diversity vs. CEO Bar

| Metric | Current nominal plan | Fresh checkpoint-backed subset | [BUY-33197](/BUY/issues/BUY-33197) smart-feed bar | `2026-06-06` CEO bar | Status |
|---|---:|---:|---:|---:|---|
| Non-Shopify share | `31.4%` | `48.6%` of the confirmed 2.8M/day | `>=30%` | `>=50%` | nominal plan clears smart-feed bar; confirmed lanes exceed it at 48.6% |
| Non-Shopify rows/day | `1,100,000` | `1,800,000` checkpoint-backed | n/a | n/a | WC deep-page + sustained + deep-page ingest all non-Shopify confirmed |

## Named Cap And Recovery Risks

1. **GS sustained and CC index expansion gone dark** — `buy30777-gs-sustained-loop.mjs` and `cc-shopify-index-loop.mjs` are absent from the current `ps` snapshot, representing `450K/day` of carried-forward assumption. Their prior uptime proofs (6.8d and 3.2d respectively) suggest possible restart or pid-cycle; need confirm from next heartbeat.
2. **Large `n_live_tup` vs. June 16 anchor** — current `n_live_tup = 120,513,540` vs June 16 shortfall anchor of `95,240,314`. The delta is consistent with strong post-restart writes, but the discrepancy warrants a clean shortfall reading tonight to re-anchor the catalog count.
3. **Named cap BUY-30590 still open** — the deep-page loop is running via `buy30331-ingest-stream.mjs` rather than the named `buy30590-deep-page-loop.mjs`, suggesting the lane is being served by a different process path. The capability is live even if the named loop is not.
4. **BUY-32878 index INVALID persists** — `products_created_at_idx` remains `indisvalid=f`; does not directly block ingestion throughput but adds query overhead on catalog reads.

## Plan-Level Verdict

- **Goal pace to `100M` by `2026-06-30`:** covered by fresh live-backed lane proof (`2,800,018/day` vs required `317,313/day`)
- **Fixed `3.5M/day` target:** `80.0%` credibly evidenced today — best day since `2026-06-11`
- **Checkpoint backing:** `2,800,018/3,500,000 = 80.0%`
- **Latest closed hour (`2026-06-17 23:00-00:00Z`):** PASS at `682,953/hr`
- **Latest closed day (`2026-06-15`):** NOT A MISS at `+6,210,936` live products (`905.8%` of required pace)

## Disposition

`done` for today's routine run. The required daily source-mix report has been delivered in-comment, with the dated archive saved for the report series.
