# BUY-35332 — Fleet keep-alive heartbeat (2026-06-08T07:31Z)

Wake scope: 5-min restart watchdog for the 8 BUY-31716 fleet discovery lanes.
Driver: `scripts/buy31716-fleet-keep-alive.sh` (consolidated canonical copy,
symlinked into Oracle's workspace for the routine path).
Fire cadence: routine `476009cc` (Oracle) every 5 min via Paperclip; cron is
on RESETSEQ-2026-06-09 hold through 01:30Z per prior board decision.

## Tick verification (2026-06-08T07:31:50Z, manual fire)

8/8 lanes OK, 0 dead_ticks each, no escalation:

| lane                    | pid      | pattern                                       | status |
|-------------------------|----------|-----------------------------------------------|--------|
| burst_discovery         | 4173035  | buy30331-sustained-loop.mjs                   | OK     |
| brand_sitemap_miner     | 3848535  | buy30590-brand-sitemap-miner.mjs              | OK     |
| retailer_sitemap_miner  | 3848662  | buy30590-retailer-sitemap-loop.mjs            | OK     |
| fast_wc_probe           | 3848747  | buy31452-fast-wc-loop.mjs                     | OK     |
| shopify_index_expansion | 3848851  | cc-shopify-index-loop.mjs                     | OK     |
| crate_deep_page         | 1482306  | buy30620-page-lane-runner.mjs --role=crate    | OK     |
| hunt2_page              | 1531301  | buy30620-page-lane-runner.mjs --role=hunt2    | OK     |
| stock_page              | 1554525  | buy30620-page-lane-runner.mjs --role=stock    | OK     |

host disk use=84% (threshold=95%, recover=90%) — under guard, no pause.

## Steady state

- Last escalation in escalation log: 2026-06-08T05:51:52Z (retailer_sitemap + shopify_index,
  12 consecutive dead_ticks each). Pre-BUY-35231-fix orphan-reaper incident.
- All 8 lanes have been OK since 2026-06-08T06:00:36Z (~90+ min stable).
- Recent ticks: 06:55:37Z, 07:16:07Z, 07:24:39Z, 07:31:50Z. Cadence 5–25 min
  (routine `skip_if_active` keeps it from double-firing).

## Stack of fixes already in script

- BUY-34462 — self-loop driver pattern (no orphan bash wrapper)
- BUY-34726 — R2 env sourcing for stock_page lane
- BUY-34381 — disk-pressure lib + FLEET-prefixed state file
- BUY-35012 — pgrep pattern fix for Shopper's unified runner
- BUY-35030 — do_wait fix (pushd/setsid/exit 0)
- BUY-35231 — orphan-reaper fix (`& wait` keeps bash-c alive)
- BUY-35280 — pgrep_pat wrapper regex (path-optional)
- BUY-35267 — STUCK classification (D-state heartbeat-frozen detection)

## Disposition

Issue remains `in_progress`. Live continuation path = routine `476009cc`
(every 5 min). No new action required this heartbeat.
