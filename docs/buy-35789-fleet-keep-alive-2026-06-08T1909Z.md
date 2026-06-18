# BUY-35789 — Fleet keep-alive heartbeat (2026-06-08T19:09Z)

Routine execution issue for the 5-minute BUY-31716 fleet keep-alive watchdog.

## What happened

- First tick at `2026-06-08T19:08:06Z` found five lanes absent from the current matcher and restarted them:
  - `brand_sitemap_miner` -> pid `2316250`
  - `retailer_sitemap_miner` -> pid `2316426`
  - `crate_deep_page` -> pid `2316670`
  - `hunt2_page` -> pid `2316743`
  - `stock_page` -> pid `2316883`
- Verification exposed a matcher gap for the three Shopper-owned lanes: the liveness probe matched only `buy30620-page-lane-runner.mjs --role=...`, while the Oracle backstop restart path launches the legacy per-role scripts.
- Patched [`scripts/buy31716-fleet-keep-alive.sh`](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh) so those three lanes are considered alive when either the unified runner or the legacy backstop script is present.

## Verification

- Second tick at `2026-06-08T19:09:14Z` completed cleanly with `8/8 lanes OK`.
- Log evidence in `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`:
  - `brand_sitemap_miner OK pid=2316250 heartbeat_age=8s`
  - `retailer_sitemap_miner OK pid=2316426 heartbeat_age=6s`
  - `crate_deep_page OK pid=2316670 (no_heartbeat_file)`
  - `hunt2_page OK pid=2316743 (no_heartbeat_file)`
  - `stock_page OK pid=2316883 (no_heartbeat_file)`
- `pgrep -af` after the verification tick showed all eight expected lane processes present, including the three Shopper backstop processes.

## Notes

- `data/buy31716-fleet-keep-alive-state.json` advanced `disk_last_sampled_at` to `2026-06-08T19:09:14Z` with `disk_use_pct=83`.
- Dead-tick counters for the restarted lanes remain at `1` because this script clears them only on the next successful tick after a lane is observed alive. The false-repeat restart path was removed; a future routine tick will zero those counters naturally.
