# BUY-36369 fleet keep-alive tick

Timestamp: 2026-06-08T23:42Z

## Action

Ran:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
bash scripts/buy31716-fleet-keep-alive.sh
pgrep -af 'buy30331-sustained-loop\.mjs'
pgrep -af 'buy30590-brand-sitemap-miner\.mjs'
pgrep -af 'buy30590-retailer-sitemap-loop\.mjs'
pgrep -af 'buy31452-fast-wc-loop\.mjs'
pgrep -af 'cc-shopify-index-loop\.mjs'
pgrep -af 'buy30620-page-lane-runner\.mjs.*--role=crate|buy30620-crate-deep-page-lane\.mjs'
pgrep -af 'buy30620-page-lane-runner\.mjs.*--role=hunt2|buy30620-hunt2-page-lane\.mjs'
pgrep -af 'buy30620-page-lane-runner\.mjs.*--role=stock|buy30620-stock-page-lane\.mjs'
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
```

## Result

The watchdog completed a fresh tick at `2026-06-08T23:41:46Z` and reported all 8
BUY-31716 lanes healthy:

- `burst_discovery` OK `pid=2691392`
- `brand_sitemap_miner` OK `pid=2316250` `heartbeat_age=3s`
- `retailer_sitemap_miner` OK `pid=2316426` `heartbeat_age=26s`
- `fast_wc_probe` OK `pid=3848747`
- `shopify_index_expansion` OK `pid=3848851`
- `crate_deep_page` OK `pid=2316670`
- `hunt2_page` OK `pid=2316743`
- `stock_page` OK `pid=2316883`

The state file remains healthy after the tick: every lane dead-count is `0`,
sampled disk usage is `90%`, and the disk-pressure guard threshold remains
`95%`.

## Evidence

- Live keep-alive log shows repeated 5-minute firings at `2026-06-08T23:30:04Z`,
  `2026-06-08T23:36:49Z`, and `2026-06-08T23:41:46Z`, each ending
  `keep-alive tick complete`:
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`
- Shared state file:
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
- The process table still shows both the `bash -c ... & wait` parent and the
  child `node` process for each lane, which is the expected orphan-reaper-safe
  shape from the current watchdog implementation.
- `systemd-analyze verify` passed for
  `systemd/paperclip-buy31716-fleet-keep-alive.{service,timer}`. The only
  warning came from unrelated host unit `/etc/systemd/system/hindsight.service`.

## Note

`data/buy31716-fleet-keep-alive-escalation.json` still contains historical
entries from the pre-fix restart-loop window around `2026-06-08T04:20Z` to
`2026-06-08T05:51Z`, but this execution added no new escalation and all current
dead counters are back at `0`.
