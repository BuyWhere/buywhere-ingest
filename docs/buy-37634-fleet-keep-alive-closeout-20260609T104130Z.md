# BUY-37634 / BUY-31716 fleet keep-alive closeout

- Timestamp: `2026-06-09T10:41:30Z`
- Workspace: `project_primary` checkout with fleet state/log rooted in Oracle workspace `3ec8f6dd-1735-4479-9825-a2c42edac34c`

## What I verified

- `scripts/buy31716-fleet-keep-alive.sh` is still the active 8-lane fleet watchdog and retains the cross-workspace restart logic.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still runs on a 5-minute cadence with `Persistent=true`.
- `bash -n scripts/buy31716-fleet-keep-alive.sh` passed.
- `systemd-analyze verify` reported only the known unrelated warning from `/etc/systemd/system/hindsight.service` and no BUY-31716 unit or timer errors.
- A fresh manual keep-alive tick succeeded in this heartbeat, and the shared fleet log showed an actual dead-lane recovery sequence followed by healthy steady-state ticks.

## Fresh runtime evidence

Manual verification commands:

- `WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh`
- `tail -n 120 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`
- `cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`

Observed restart event from the live keep-alive log:

- Tick `2026-06-09T10:14:27Z` detected 5 dead lanes and relaunched them:
  - `brand_sitemap_miner` restarted as pid `2146097`
  - `retailer_sitemap_miner` restarted as pid `2146225`
  - `crate_deep_page` restarted as pid `2146381`
  - `hunt2_page` restarted as pid `2146496`
  - `stock_page` restarted as pid `2146632`
- The immediately following tick at `2026-06-09T10:15:01Z` showed all 8 lanes healthy again.

Latest confirmed healthy fleet tick from the same log:

- Tick timestamp: `2026-06-09T10:41:19Z`
- Disk sample: `host disk use=93%` with threshold `95%`
- Healthy lanes:
  - `burst_discovery` pid `2139271`
  - `brand_sitemap_miner` pid `2146097`
  - `retailer_sitemap_miner` pid `2146225`
  - `fast_wc_probe` pid `3848747`
  - `shopify_index_expansion` pid `3848851`
  - `crate_deep_page` pid `2146381`
  - `hunt2_page` pid `2146496`
  - `stock_page` pid `2146632`

Shared state after the latest tick:

- `disk_last_sampled_at=2026-06-09T10:41:19Z`
- `disk_use_pct=93`
- `disk_pressure_pauses=10`
- All tracked per-lane dead counts remained `0`

Escalation file check:

- `data/buy31716-fleet-keep-alive-escalation.json` did not receive a new entry from this heartbeat; it still ends with the prior June 8 escalation history.

## Disposition

`BUY-37634` can close `done`: the 5-minute BUY-31716 fleet keep-alive is still wired correctly, a fresh manual tick completed successfully, and the live watchdog log proves it can detect dead lanes and bring the fleet back to a healthy 8-lane state.
