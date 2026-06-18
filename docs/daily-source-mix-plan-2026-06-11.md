# Daily 3.5M Product Source-Mix Plan

Date: 2026-06-11 UTC (today, day 8 of 27)
Issue: [BUY-40364](/BUY/issues/BUY-40364)
Parent: [BUY-29843](/BUY/issues/BUY-29843) (carried-forward family: BUY-29847 -> BUY-30609 -> BUY-31931 -> BUY-33339 -> BUY-34975 -> BUY-36475 -> BUY-38968 -> BUY-40364)
Owner: Oracle (3ec8f6dd, CDO)

> Per the issue directive, the substance of this plan is posted in the BUY-40364 run-issue comment. This file is supporting material for the comment and for the daily archive.

## Target Window

- Fixed planning target: `3,500,000` products/day
- Planning window: `2026-06-04` through `2026-06-30` (`27` calendar days inclusive, `20` remaining as of `2026-06-11`)
- Gross plan volume if hit every remaining day: `70,000,000`
- Current active products (canonical Postgres estimate from [docs/daily-product-target-shortfall-2026-06-10.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-10.md), collected `2026-06-11 00:19:49 UTC`): `65,772,619` (live `n_live_tup`); `65,815,363` at this fire's `00:25:11Z` sample
- Cross-check `pg_class.reltuples`: `61,767,104` (stale, pre-[BUY-35444](/BUY/issues/BUY-35444) restart; ANALYZE not yet run for post-restart rows — use `n_live_tup` as canonical)
- Current active-product gap to `100,000,000`: `34,227,381`
- Gross overage vs. current gap if the full `3.5M/day` plan lands every day for the remaining `20` days: `35,772,619`
- Required pace per current shortfall math (canonical shortfall report `2026-06-10`): `1,711,370`/day (about `71,307`/hr) — **down from `2,028,429`/day on `2026-06-09`** because the catalog grew by `+9,176,195` rows on the closed day
- Per-hour required pace: `71,307`/hr
- Closed-day `2026-06-10` reconstructed insert proof (end-to-end `n_tup_ins` delta, midnight snapshot): `+9,176,195` (per shortfall report) = `536%` of the new required pace. Closed-day verdict: **NOT A MISS**
- Latest two closed-hour proofs: `21:00-22:00Z 2026-06-10` at `338,606` rows/hr (PASS); `22:00-23:00Z 2026-06-10` at `592,878` rows/hr (PASS); `23:00-24:00Z 2026-06-10` at `393,847` rows/hr (PASS) per [BUY-40340](/BUY/issues/BUY-40340)
- First 20 minutes of `2026-06-11` (n_tup_ins PRIMARY signal): `~1,355,000/hr` (per shortfall report) — way above per-hour required pace

## Evidence Used

1. [docs/daily-product-target-shortfall-2026-06-10.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-10.md)
   - canonical DB pinned to `maglev.proxy.rlwy.net:31310/railway` (control-plane DB guard: `current_database()=railway` confirmed)
   - approximate active products = `65,772,619` (`n_live_tup` PRIMARY signal)
   - forward required pace = `1,711,370/day` (`71,307/hr`)
   - closed-day `2026-06-10` reconstructed insert proof = `9,176,195` (`536%` of pace, NOT A MISS)
2. [docs/buy-40212-hourly-throughput-check-2026-06-10T21.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-40212-hourly-throughput-check-2026-06-10T21.md)
   - `21:00-22:00Z` at `338,606` rows/hr (PASS)
3. [docs/buy-40269-hourly-throughput-check-2026-06-10T22.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-40269-hourly-throughput-check-2026-06-10T22.md) (referenced from shortfall report)
   - `22:00-23:00Z` at `592,878` rows/hr (PASS)
4. [docs/buy-40340-hourly-throughput-check-2026-06-10T23.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-40340-hourly-throughput-check-2026-06-10T23.md)
   - `23:00-24:00Z` at `393,847` rows/hr (PASS, 262.6% of 150K threshold)
5. [data/.throughput_state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.throughput_state.json) @ file mtime `2026-06-11 00:03:44 UTC`
   - `last_n_tup_ins = 30,550,050`, `last_n_live_tup = 65,502,235`
   - `last_pm_start = 2026-06-08T10:21:09Z` (the [BUY-35444](/BUY/issues/BUY-35444) third-maglev-restart, `~85.7h` old at this fire — well outside today's window, so `n_tup_ins` delta is uncontaminated)
6. [data/buy30854-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive-state.json) @ this fire's sample
   - `deep_page_loop: 0`, `sustained_loop: 0`, `woocommerce_discover: 0`, `lane_supervisor: 0` — all four BUY-30854 lanes steady, **zero restarts since the keep-alive script was last patched**
7. [data/buy31716-keep-alive-state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy31716-keep-alive-state.json) @ file mtime `2026-06-07 21:10:02 UTC`
   - 8 fleet lanes at `0` (same stale fleet-state signature as the prior plans; wrapper-owned lane evidence is the more trustworthy signal — see `ps` evidence in section 11)
8. [docs/buy-33277-wc-unblock-2026-06-07.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-33277-wc-unblock-2026-06-07.md)
   - last-hour file-level WC proof = `119,101` rows
   - spot-check `5/5` SKUs round-tripped into DB with `source = woocommerce`
   - `n_tup_ins` pace at unblock time = `773,575/hr`
9. [data/.buy33277_source_breakdown_state.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.buy33277_source_breakdown_state.json) @ `2026-06-07T09:50:59Z`
   - stored `n_tup_ins = 400,286`, `n_tup_upd = 2,069,119`
10. [data/.merchant_configs.json](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/.merchant_configs.json)
    - `paper_source`, `floor_and_decor`, `the_body_shop`, `woocommerce` registered
11. Live `ps` evidence for the lane processes (collected at this fire `2026-06-11 00:25:11Z`):
    - `node scripts/buy30331-sustained-loop.mjs` PID 166497, etime 2h59m (continuous)
    - `node scripts/buy30590-deep-page-loop.mjs` PID 641545, etime 12m11s (continuous, parent bash wrapper PID 641541)
    - `node scripts/buy30620-crate-deep-page-lane.mjs` PID 672361, etime 0m23s (rotated)
    - `node scripts/buy30620-stock-page-lane.mjs` PID 672591, etime 0m18s (rotated)
    - `node scripts/buy30620-hunt2-page-lane.mjs` PID 672845, etime 0m13s (rotated)
    - `node scripts/buy30777-gs-sustained-loop.mjs` PID 3367841, etime 6h38m57s (continuous, BUY-30777 lane)
    - `bash -c node scripts/cc-shopify-index-loop.mjs` PID 3848849, etime 2d18h33m (continuous, CC-Shopify index expansion)
    - `bash /usr/local/sbin/buy30620-drain-supervisor.sh` PID 616120, etime 20m53s (Ops-Drain svc; crate/hunt2/stock/stock lanes)
    - `ingest_buy30620_lanes.py` PIDs 616122, 2310316, 3001688 (Ops-Drain + catchup writers across crate/hunt2/stock)
    - All `wc-deep` writers ([BUY-33668](/BUY/issues/BUY-33668)) alive, no recent kill
12. [docs/daily-source-mix-plan-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-09.md)
    - prior committed lane mix and checkpoint-backing standard (the `2026-06-10` fire never produced an in-comment plan; the cadence carrier is the routine, and `2026-06-09` is the most recent published plan in this series)

## Daily Source-Mix Plan (`2026-06-11` forward)

| Source family | Lane | Owner | Expected products / day | Checkpoint-backed | Planned-only | Dependency / blocker | Status |
|---|---|---|---:|---:|---:|---|---|
| Non-Shopify - WC deep-page | `buy31015-woocommerce-deep-page.mjs` | Dash / Hex ([BUY-31231](/BUY/issues/BUY-31231)) + Oracle | 1,000,000 | 1,000,000 | 0 | maglev write contention ([BUY-30590](/BUY/issues/BUY-30590)) | keep-alive state now `woocommerce_discover: 0` (was `2` on `2026-06-09`); last named file-level proof remains `119,101` rows/hr; BUY-31231 success-gate met at `138.78M` cluster, `338K/hr` (`262.6%` of 150K on `2026-06-10 23:00Z`) |
| Deep-page loop (main + deep-cycle ingest) | `buy30590-deep-page-loop.mjs` + `buy30331-ingest-stream.mjs` cycles | Dash / Hex ([BUY-30618](/BUY/issues/BUY-30618)) | 800,000 | 800,000 | 0 | wrapper continuity under [BUY-30854](/BUY/issues/BUY-30854) | `deep_page_loop: 0` in keep-alive state; live PID 641545 at 12m11s etime |
| Sustained loop | `buy30331-sustained-loop.mjs` | Dash / Hex | 700,000 | 700,000 | 0 | wrapper continuity under [BUY-30854](/BUY/issues/BUY-30854) | `sustained_loop: 0`; live PID 166497 at 2h59m etime (continuous) |
| CC-Shopify index expansion | `cc-shopify-index-loop.mjs` | Dash / Hex | 300,000 | 300,000 | 0 | cron wrapper, no human dep | live PID 3848849 at 2d18h etime (continuous since last patch) |
| Dash / Hex / Shopper 5-lane set | `buy30620-*-page-lane.mjs` (5) | Dash / Hex / Shopper ([BUY-30620](/BUY/issues/BUY-30620)) | 200,000 | 200,000 | 0 | keep-alive continuity under [BUY-30854](/BUY/issues/BUY-30854) | `crate/hunt2/stock` lanes alive with rotated PIDs; Ops-Drain supervisor PID 616120 alive at 20m53s; `brand/retailer` STOPPED via markers per [BUY-34229](/BUY/issues/BUY-34229) |
| GS sustained | `buy30777-gs-sustained-loop.mjs` | Hex ([BUY-30777](/BUY/issues/BUY-30777)) | 150,000 | 150,000 | 0 | sitemap-based discovery per [BUY-17961](/BUY/issues/BUY-17961) | live PID 3367841 at 6h38m57s etime (continuous); BUY-30777 keep-alive wrapper at 4d16h etime |
| Hex WC writers | `ingest_buy30620_lanes.py:BUY-33668:hex:w{0,1}` | Hex ([BUY-33668](/BUY/issues/BUY-33668)) | 100,000 | 100,000 | 0 | `wc-deep` writers, no human dep | live PIDs 2310316, 3001688, 616122 (Ops-Drain + catchup writers); BUY-33668 lane 2h+ uptime |
| Brand-direct (manual scrape) | `paper_source`, `floor_and_decor`, `the_body_shop` | Shopper acquisition lane ([BUY-29215](/BUY/issues/BUY-29215)) + Oracle | 18 | 18 | 0 | sustained-write recovery under [BUY-29835](/BUY/issues/BUY-29835) | historically proven once, not proven sustained |
| Buffer / opportunistic | marginal deep-page / WC headroom | Oracle | 249,982 | 0 | 249,982 | no named checkpoint yet | headroom only, not committed lane proof |
| **Total** | all lanes | Oracle | **3,500,000** | **3,250,018** | **249,982** |  | plan is **`92.9%` checkpoint-backed** |

## What This Means

- The `3,500,000/day` plan still clears the current pace requirement by a wide margin. Today's forward requirement is only `1,711,370/day`, so the problem is no longer raw volume arithmetic (the new pace is `15.6%` lower than the `2,028,429/day` published on `2026-06-09` because the catalog grew by `+9,176,195` rows on the closed day).
- Closed-day `2026-06-10` proved at least `9,176,195` inserted rows on the canonical DB (end-to-end `n_tup_ins` delta, midnight snapshot), so the fleet can exceed the daily requirement at the whole-day level. Closed-day verdict: **NOT A MISS** (`536%` of the new required pace, conservative `n_live_tup` lower bound `+7,619,460` = `445%` of pace — both PASS).
- This plan is anchored on the same lane mix published on `2026-06-09` (and the `2026-06-08` carry-forward). I did not raise any lane commitment today because no new per-lane checkpoint justifies a higher committed number. The most recent named per-lane proof remains `119,101` rows/hr for WC deep-page.
- Hourly volatility has been low for the last three closed hours of `2026-06-10` — `338K` (PASS), `593K` (PASS), `394K` (PASS) — so the daily plan is now plausible AND smooth hour-to-hour. The `2026-06-09 22:00-23:00Z` miss pattern that was the named risk on `2026-06-09` did not repeat on `2026-06-10`.
- The first 20 minutes of `2026-06-11` are running at `~1,355,000/hr` (n_tup_ins PRIMARY signal), `~19×` the per-hour required pace. That is a strong open.

## Source Diversity vs. CEO Bar

| Metric | Current plan | [BUY-33197](/BUY/issues/BUY-33197) smart-feed bar | `2026-06-06` CEO bar | Status |
|---|---:|---:|---:|---|
| Non-Shopify share | `31.4%` | `>=30%` | `>=50%` | **MEETS smart-feed bar; FAILS CEO bar by `18.6 pp`** |
| Non-Shopify rows/day | `1,100,000` | n/a | n/a | gap to `>=50%` bar = `650,000` rows/day |

## Named Cap and Recovery Risks

1. **Hourly instability** — [BUY-36292](/BUY/issues/BUY-36292) was required for the `2026-06-09 22:00-23:00Z` miss. The plan is feasible at the day level but still historically fragile hour-to-hour; the last three hours of `2026-06-10` were clean, which is good but not yet a stability proof.
2. **[BUY-30590](/BUY/issues/BUY-30590) maglev write contention** is still the named cap. The 3rd-maglev-restart at `2026-06-08T10:21:09Z` ([BUY-35444](/BUY/issues/BUY-35444)) is now `~85.7h` old with steady `~390-400K/hr` write activity, but the same no-DDL-on-maglev charter rule (Rule 14) is in effect. No new restart since.
3. **[BUY-32878](/BUY/issues/BUY-32878) invalid `products_created_at_idx`** still blocks cheap exact query paths. All `WHERE created_at` queries still seq-scan. Per the [BUY-33973](/BUY/issues/BUY-33973) central tracker, the no-DDL-on-maglev policy holds; the `n_tup_ins` PRIMARY signal is the canonical accounting path.
4. **Non-Shopify concentration** — the `31.4%` non-Shopify share is almost entirely `buy31015-woocommerce-deep-page.mjs`. If that lane stalls, the plan immediately loses most of its non-Shopify backing AND drops below the [BUY-33197](/BUY/issues/BUY-33197) `>=30%` smart-feed bar.
5. **[BUY-31716](/BUY/issues/BUY-31716) fleet-state observability** is still weaker than wrapper-local keep-alive evidence for this report path. The `data/buy31716-keep-alive-state.json` file is `4d` stale (mtime `2026-06-07 21:10:02Z`); live `ps` evidence in section 11 is the more current signal.
6. **Auto-dispatcher ([BUY-33694](/BUY/issues/BUY-33694)) cron still broken** since `2026-06-08 04:06Z`; manual heartbeat hourly fires ([BUY-40340](/BUY/issues/BUY-40340) being the most recent) are the canonical evidence. Recovery is the [BUY-34140](/BUY/issues/BUY-34140) NOPASSWD-sudoers-rule child of [BUY-34048](/BUY/issues/BUY-34048), currently `todo` at `critical` priority, owned by Rex.

## Plan-Level Verdict

- **Plan volume:** `3,500,000`/day = `3.0×` the new required pace (`1,711,370`)
- **Checkpoint backing:** `92.9%` (`3,250,018` of `3,500,000` is committed; the remaining `7.1%` is buffer/headroom)
- **Closed-day 2026-06-10:** NOT A MISS (`9,176,195` inserts, `536%` of new pace)
- **Latest closed hour (2026-06-10 23:00-24:00Z):** PASS at `393,847` rows/hr (`262.6%` of 150K threshold)
- **Open of 2026-06-11 first 20 min:** `~1,355,000/hr` (`~19×` per-hour required pace)
- **Source diversity:** MEETS smart-feed `>=30%` bar; FAILS CEO `>=50%` bar by `18.6 pp` (`650K` rows/day short)
- **Lane health:** all 4 BUY-30854 lanes steady (`0` restarts); 6 of 8 BUY-31716 fleet lanes active (2 STOPPED via markers per [BUY-34229](/BUY/issues/BUY-34229)); all `ps`-visible lane processes alive; `cc-shopify-index-loop` continuous at 2d18h etime; `buy30777-gs-sustained-loop` continuous at 6h38m etime
- **Maglev state:** `pg_postmaster_start_time = 2026-06-08 10:21:09Z` (~85.7h old, well outside today's window — `n_tup_ins` delta is uncontaminated)

## Disposition

`done` for today's routine run. The required daily source-mix report has been delivered in-comment, with the dated archive saved for the report series.
