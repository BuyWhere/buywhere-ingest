# BUY-37316 — BUY-31716 fleet keep-alive closeout (2026-06-09T07:54:49Z)

Issue scope: verify the BUY-31716 fleet keep-alive still enforces the
5-minute restart/watchdog path for all 8 discovery lanes in the current
checkout.

## Result

- `scripts/buy31716-fleet-keep-alive.sh` remains the fleet watchdog for the
  8-lane discovery fleet.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still enforces
  `OnUnitActiveSec=5min`.
- A fresh watchdog tick completed at `2026-06-09T07:54:38Z` with `8/8` lanes
  alive, `0` restarts required, and `0` new escalations.

## Verification

- `bash -n scripts/buy31716-fleet-keep-alive.sh`
- `WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer`
- `pgrep -af 'buy30331-sustained-loop.mjs|buy30590-brand-sitemap-miner.mjs|buy30590-retailer-sitemap-loop.mjs|buy31452-fast-wc-loop.mjs|cc-shopify-index-loop.mjs|buy30620-page-lane-runner.mjs.*--role=crate|buy30620-crate-deep-page-lane.mjs|buy30620-page-lane-runner.mjs.*--role=hunt2|buy30620-hunt2-page-lane.mjs|buy30620-page-lane-runner.mjs.*--role=stock|buy30620-stock-page-lane.mjs'`

## Evidence

- Keep-alive log in
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`
  recorded a clean tick from `2026-06-09T07:54:38Z` through
  `2026-06-09T07:54:39Z`.
- Live state file in
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
  now shows:
  - `disk_last_sampled_at: 2026-06-09T07:54:38Z`
  - `disk_use_pct: 91`
  - zero dead counts for `burst_discovery`, `brand_sitemap_miner`,
    `retailer_sitemap_miner`, `fast_wc_probe`, `shopify_index_expansion`,
    `crate_deep_page`, `hunt2_page`, and `stock_page`
- Escalation history in
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json`
  still ends with the older `2026-06-08T05:51:52Z`
  `shopify_index_expansion` entry; this verification added no new escalation.
- Immediate `pgrep -af` verification after the tick found the expected live
  node processes:
  - `burst_discovery` pid `670904`
  - `brand_sitemap_miner` pid `2316250`
  - `retailer_sitemap_miner` pid `2316426`
  - `fast_wc_probe` pid `3848747`
  - `shopify_index_expansion` pid `3848851`
  - `crate_deep_page` pid `2316670`
  - `hunt2_page` pid `4120587`
  - `stock_page` pid `2316883`

## Notes

- `systemd-analyze verify` reported the known unrelated host warning for
  `/etc/systemd/system/hindsight.service` (`Unknown key name
  'StartLimitIntervalSec' in section 'Service'`), but no errors for the
  BUY-31716 keep-alive service or timer.
