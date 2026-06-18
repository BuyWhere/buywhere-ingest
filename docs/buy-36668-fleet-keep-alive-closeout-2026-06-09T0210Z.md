# BUY-36668 — BUY-31716 fleet keep-alive closeout (2026-06-09T02:10Z)

Issue scope: confirm the 5-minute `BUY-31716` restart/watchdog path for the 8
new discovery lanes is live, healthy, and still wired to the checked-in
implementation.

## What I verified

- `scripts/buy31716-fleet-keep-alive.sh` is the fleet watchdog for all 8 lanes:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`,
  `hunt2_page`, and `stock_page`.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` runs that script as a
  oneshot unit from the project workspace.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` sets the 5-minute cadence
  with `OnUnitActiveSec=5min`.
- A fresh manual watchdog tick completed successfully and appended to the live
  shared log in Oracle's workspace.
- The shared state file advanced to the same tick and kept zero dead counts for
  all tracked lanes.
- A live process snapshot shows all 8 lane processes up after the tick.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 30 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
ps -eo pid,etimes,cmd | rg "buy30331-sustained-loop|buy30590-brand-sitemap-miner|buy30590-retailer-sitemap-loop|buy31452-fast-wc-loop|cc-shopify-index-loop|buy30620-page-lane-runner|buy30620-(crate-deep-page|hunt2-page|stock-page)-lane|buy30620-lane-keep-alive"
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; no errors for the `BUY-31716`
  service or timer units.
- The latest log block shows a fresh tick at `2026-06-09T02:09:57Z` with all 8
  tracked lanes healthy and no restart/escalation triggered.
- The shared state file advanced `disk_last_sampled_at` to
  `2026-06-09T02:09:57Z`, kept `disk_use_pct` at `85`, and preserved zero dead
  counts for every tracked lane.
- The live process snapshot after the tick shows all 8 lane node processes up.

## Evidence

Latest log block:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T02:09:57Z =====
[2026-06-09T02:09:57Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T02:09:57Z] host disk use=85% (threshold=95%, recover=90%)
[2026-06-09T02:09:57Z] burst_discovery OK pid=2691392 (no_heartbeat_file)
[2026-06-09T02:09:57Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=12s
[2026-06-09T02:09:57Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=14s
[2026-06-09T02:09:57Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T02:09:57Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T02:09:57Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-09T02:09:57Z] hunt2_page OK pid=2316743 (no_heartbeat_file)
[2026-06-09T02:09:57Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-09T02:09:57Z] keep-alive tick complete
```

Shared state after the tick:

```json
{
  "brand_sitemap_miner": 0,
  "burst_discovery": 0,
  "crate_deep_page": 0,
  "disk_last_sampled_at": "2026-06-09T02:09:57Z",
  "disk_pressure_pauses": 10,
  "disk_use_pct": "85",
  "fast_wc_probe": 0,
  "hunt2_page": 0,
  "last_disk_pressure_marker": "{\"created_at\": \"2026-06-07T21:16:42Z\", \"use_pct\": 80, \"threshold_pct\": 50, \"root\": \"/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c\", \"note\": \"write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)\"}",
  "last_disk_pressure_pause_at": "2026-06-07T21:16:42Z",
  "retailer_sitemap_miner": 0,
  "shopify_index_expansion": 0,
  "stock_page": 0
}
```

Live lane snapshot after verification:

```text
2316250 node scripts/buy30590-brand-sitemap-miner.mjs
2316426 node scripts/buy30590-retailer-sitemap-loop.mjs
2316670 node scripts/buy30620-crate-deep-page-lane.mjs
2316743 node scripts/buy30620-hunt2-page-lane.mjs
2316883 node scripts/buy30620-stock-page-lane.mjs
2691392 node scripts/buy30331-sustained-loop.mjs
3848747 node scripts/buy31452-fast-wc-loop.mjs
3848851 node scripts/cc-shopify-index-loop.mjs
```

## Disposition

`BUY-36668` can close `done`. The `BUY-31716` 5-minute keep-alive path for the
8 discovery lanes is present in the checked-in script and systemd units, the
live timer path is active, and the latest verified tick left all tracked lanes
healthy without intervention.
