# BUY-37095 — BUY-31716 fleet keep-alive closeout (2026-06-09T05:59Z)

Issue scope: verify that the BUY-31716 5-minute fleet keep-alive path still
monitors the eight discovery lanes and leave fresh runtime evidence for this
routine execution issue.

## Current wiring

- `scripts/buy31716-fleet-keep-alive.sh` remains the active watchdog for the
  mixed-workspace 8-lane BUY-31716 fleet.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` still runs the
  watchdog as a oneshot from this workspace.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still enforces the
  5-minute cadence with `OnUnitActiveSec=5min`.

## Verification run

Commands executed:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh
pgrep -af 'buy30331-sustained-loop.mjs|buy30590-brand-sitemap-miner.mjs|buy30590-retailer-sitemap-loop.mjs|buy31452-fast-wc-loop.mjs|cc-shopify-index-loop.mjs|buy30620-page-lane-runner.mjs.*--role=crate|buy30620-crate-deep-page-lane.mjs|buy30620-page-lane-runner.mjs.*--role=hunt2|buy30620-hunt2-page-lane.mjs|buy30620-page-lane-runner.mjs.*--role=stock|buy30620-stock-page-lane.mjs'
```

Results:

- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; it reported no errors for the
  BUY-31716 service or timer units.
- The live watchdog log now shows consecutive clean ticks at
  `2026-06-09T05:54:33Z` and `2026-06-09T05:59:43Z`.
- The latest tick sampled host disk use at `89%`, below the `95%`
  disk-pressure threshold.
- No restart or escalation was needed on the verification tick.

## Lane state after tick

| lane | status |
| --- | --- |
| `burst_discovery` | OK, pid `3907215` |
| `brand_sitemap_miner` | OK, pid `2316250`, heartbeat age `22s` |
| `retailer_sitemap_miner` | OK, pid `2316426`, heartbeat age `23s` |
| `fast_wc_probe` | OK, pid `3848747` |
| `shopify_index_expansion` | OK, pid `3848851` |
| `crate_deep_page` | OK, pid `2316670` |
| `hunt2_page` | OK, pid `4120587` |
| `stock_page` | OK, pid `2316883` |

## Evidence

- `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`
  recorded healthy ticks through `2026-06-09T05:59:43Z`.
- `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
  advanced `disk_last_sampled_at` to `2026-06-09T05:59:43Z`, set
  `disk_use_pct` to `89`, and kept every tracked lane dead count at `0`.
- Immediate `pgrep -af` verification after the watchdog run showed the expected
  process set for all eight lanes.
- `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json`
  did not gain any new entries on this tick; the file still ends with the
  historical `2026-06-08T05:51:52Z` `shopify_index_expansion` escalation.

## Disposition

`BUY-37095` can close `done`: the 5-minute BUY-31716 fleet keep-alive wiring
verified cleanly on `2026-06-09T05:59Z`, and the watchdog observed all eight
expected lanes alive without needing any restart action.
