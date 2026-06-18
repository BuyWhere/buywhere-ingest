# Daily 3.5M Product Source-Mix Plan

Date: 2026-06-16 UTC (today, day 13 of 27)
Issue: [BUY-52128](/BUY/issues/BUY-52128)
Parent: [BUY-29843](/BUY/issues/BUY-29843)
Owner: Oracle (3ec8f6dd, CDO)

> Per the issue directive, the substance of this plan is posted in the BUY-52128 run-issue comment. This file is supporting material for the comment and for the daily archive.

## Target Window

- Fixed planning target: `3,500,000` products/day
- Planning window: `2026-06-04` through `2026-06-30` (`27` calendar days inclusive, `15` remaining as of `2026-06-16`)
- Gross plan volume if hit every remaining day: `52,500,000`
- Current active products (canonical Postgres estimate from [docs/daily-product-target-shortfall-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-16.md), collected `2026-06-16 00:15:16 UTC`): `95,240,314`
- Current active-product gap to `100,000,000`: `4,759,686`
- Gross overage vs. current gap if the full `3.5M/day` plan lands every remaining day: `47,740,314`
- Required pace per the current shortfall math: `317,313`/day (`13,221`/hr)
- Latest closed-day proof: `2026-06-15` added at least `+6,210,936` live products (`905.8%` of required pace)
- Latest clean post-restart hourly proof: `2026-06-15 14:00-15:00Z` at `2,803,902` rows/hr PASS in [docs/buy-51747-hourly-throughput-check-2026-06-15T15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-51747-hourly-throughput-check-2026-06-15T15.md)

## Evidence Used

1. [docs/daily-product-target-shortfall-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-16.md)
   - canonical DB pinned to `maglev.proxy.rlwy.net:31310/railway`
   - approximate active products = `95,240,314`
   - forward required pace = `317,313/day`
   - closed-day `2026-06-15` conservative growth proof = `6,210,936`
   - `pg_postmaster_start_time = 2026-06-15 09:56:28.874687+00`, so whole-day `n_tup_ins` carry-forward math is invalid across the restart
2. [docs/buy-51747-hourly-throughput-check-2026-06-15T15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-51747-hourly-throughput-check-2026-06-15T15.md)
   - latest clean post-restart hour passed at `2,803,902/hr` via canonical `n_tup_ins` delta
3. [data/.throughput_state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.throughput_state.json) @ file mtime `2026-06-15 15:08:04 UTC`
   - `last_n_tup_ins = 2,858,763`
   - `last_n_live_tup = 2,857,635`
   - `last_check_result = PASS`
   - `last_pm_start = 2026-06-15 09:56:28.874687+00`
4. [data/buy30854-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive-state.json) @ file mtime `2026-06-11 05:49 UTC`
   - `deep_page_loop: 0`, `sustained_loop: 0`, `woocommerce_discover: 0`, `lane_supervisor: 0`
   - stale no-restart signal only; not sufficient by itself for fresh `2026-06-16` commitments
5. [data/buy31716-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy31716-keep-alive-state.json) @ file mtime `2026-06-07 21:10 UTC`
   - still stale; not a current truth source for this report
6. Live `ps` evidence collected in this heartbeat at `2026-06-16 00:25:57 UTC`
   - `node scripts/buy30620-hunt2-page-lane.mjs` PID `203640`, etime `30s`
   - `node scripts/buy30620-stock-page-lane.mjs` PID `203938`, etime `25s`
   - `python3 scripts/ingest_buy30620_lanes.py` catchup writers for `stock`, `crate`, `hunt2` PIDs `98047`, `98048`, `98050`, each etime `1110s`
   - `bash /usr/local/sbin/buy30620-drain-supervisor.sh` PIDs `1567586`, `1567589`, each etime `34116s`
   - `python3 ... ingest_buy30620_lanes.py --writer ingest:ops-drain-svc:hunt2` PID `1567591`, etime `34116s`
   - no confirming current `ps` hit for `cc-shopify-index-loop.mjs`, `buy30777-gs-sustained-loop.mjs`, `buy30590-deep-page-loop.mjs`, `buy30331-sustained-loop.mjs`, or `buy31015-woocommerce-deep-page.mjs`
7. Transient runtime note from earlier in this same heartbeat
   - `buy31015-woocommerce-deep-page.mjs` was briefly visible once with PID `193161`, etime `77s`, but it was absent in the later confirming sample above, so I am not counting it as checkpoint-backed for this report

## Daily Source-Mix Plan (`2026-06-16` forward)

| Source family | Lane | Owner | Expected products / day | Checkpoint-backed | Planned-only | Dependency / blocker | Status |
|---|---|---|---:|---:|---:|---|---|
| Dash / Hex / Shopper page-lane set | `buy30620-{crate,hunt2,stock}-page-lane.mjs` | Dash / Hex / Shopper ([BUY-30620](/BUY/issues/BUY-30620)) | 200,000 | 200,000 | 0 | keep-alive continuity + drain supervisor | `hunt2` and `stock` page-lane PIDs confirmed; `crate` writer path and supervisor confirmed |
| Hex WC writers | `ingest_buy30620_lanes.py` writer set | Hex ([BUY-33668](/BUY/issues/BUY-33668)) | 100,000 | 100,000 | 0 | writer continuity | catchup writers for `stock`, `crate`, `hunt2` confirmed live |
| Non-Shopify - WC deep-page | `buy31015-woocommerce-deep-page.mjs` | Dash / Hex ([BUY-31231](/BUY/issues/BUY-31231)) + Oracle | 1,000,000 | 0 | 1,000,000 | no steady confirming process proof in the final sample | transient sighting only; not committed today |
| Deep-page loop (main + deep-cycle ingest) | `buy30590-deep-page-loop.mjs` + `buy30331-ingest-stream.mjs` | Dash / Hex ([BUY-30618](/BUY/issues/BUY-30618)) | 800,000 | 0 | 800,000 | no current runtime proof in this heartbeat | carried-forward assumption only |
| Sustained loop | `buy30331-sustained-loop.mjs` | Dash / Hex | 700,000 | 0 | 700,000 | no current runtime proof in this heartbeat | carried-forward assumption only |
| Shopify - CC index expansion | `cc-shopify-index-loop.mjs` | Dash / Hex | 300,000 | 0 | 300,000 | no current runtime proof in this heartbeat | carried-forward assumption only |
| GS sustained | `buy30777-gs-sustained-loop.mjs` | Hex ([BUY-30777](/BUY/issues/BUY-30777)) | 150,000 | 0 | 150,000 | no current runtime proof in this heartbeat | carried-forward assumption only |
| Brand-direct (manual scrape) | `paper_source`, `floor_and_decor`, `the_body_shop` | Shopper acquisition lane ([BUY-29215](/BUY/issues/BUY-29215)) + Oracle | 18 | 18 | 0 | sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | historically proven once, still tiny |
| Buffer / opportunistic | marginal headroom across all lanes | Oracle | 249,982 | 0 | 249,982 | no named fresh checkpoint | headroom only |
| **Total** | all lanes | Oracle | **3,500,000** | **300,018** | **3,199,982** |  | plan is **`8.6%` checkpoint-backed** |

## What This Means

- The goal pace to reach `100M` by `2026-06-30` fell again to only `317,313/day`, but the fresh lane-level proof in this heartbeat only backs `300,018/day`, which is `17,295/day` short of that requirement.
- That shortfall is an evidence-accounting problem more than a demonstrated system-capacity problem. The latest clean post-restart hourly proof is still a very large PASS at `2,803,902/hr`, and the closed UTC day `2026-06-15` added at least `6,210,936` live products.
- The fixed `3.5M/day` source-mix story is even less current than it was on `2026-06-15`. Today I can only back `8.6%` of the nominal mix with fresh runtime proof in the final confirming sample.
- The main regression from the previous report is the loss of steady confirming runtime evidence for the largest carried lanes: WC deep-page, deep-page loop, sustained loop, CC index expansion, and GS sustained.

## Source Diversity vs. CEO Bar

| Metric | Current nominal plan | Fresh checkpoint-backed subset | [BUY-33197](/BUY/issues/BUY-33197) smart-feed bar | `2026-06-06` CEO bar | Status |
|---|---:|---:|---:|---:|---|
| Non-Shopify share | `31.4%` | not freshly proven today | `>=30%` | `>=50%` | nominal plan still clears smart-feed on paper, but this heartbeat does not freshly prove the non-Shopify lane mix |
| Non-Shopify rows/day | `1,100,000` | `0` checkpoint-backed today | n/a | n/a | WC deep-page remains the missing fresh proof |

## Named Cap And Recovery Risks

1. **Fresh proof gap on the largest lanes** - no steady confirming current `ps` evidence for the lanes that account for `2.95M/day` of the carried plan (`buy31015`, `buy30590`, `buy30331`, `cc-shopify-index-loop`, `buy30777`).
2. **Restart-induced accounting discontinuity** - the `2026-06-15 09:56:28 UTC` maglev restart invalidates whole-day `n_tup_ins` carry-forward math, so today's overall success proof is on `n_live_tup` and post-restart hourly slices rather than a simple midnight-to-midnight counter delta.
3. **Stale fleet-state observability** - `data/buy31716-keep-alive-state.json` is still stuck at `2026-06-07`, and `data/buy30854-keep-alive-state.json` is still stuck at `2026-06-11`, so live process inspection is the more trustworthy source.
4. **Truth gap vs. nominal 3.5M target** - the company is on track to hit `100M`, but the daily source-mix routine still asks for a truthful `3.5M/day` lane accounting narrative, and that narrative is not currently evidenced.

## Plan-Level Verdict

- **Goal pace to `100M` by `2026-06-30`:** not fully covered by fresh checkpoint-backed lane proof (`300,018/day` vs required `317,313/day`)
- **Observed system output:** latest clean post-restart hour passed at `2,803,902/hr`; closed-day `2026-06-15` grew by at least `6,210,936`
- **Fixed `3.5M/day` target:** not credibly evidenced today
- **Checkpoint backing:** `8.6%`
- **Latest closed day (`2026-06-15`):** PASS at `+6,210,936` live products (`905.8%` of required pace)
- **Latest clean post-restart hour (`2026-06-15 14:00-15:00Z`):** PASS at `2,803,902/hr`

## Disposition

`done` for today's routine run. The required daily source-mix report has been delivered in-comment, with the dated archive saved for the report series.
