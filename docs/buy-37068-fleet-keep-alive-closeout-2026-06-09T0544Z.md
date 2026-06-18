# BUY-37068 — BUY-31716 fleet keep-alive closeout (2026-06-09T05:44Z)

Issue scope: confirm the 5-minute BUY-31716 fleet keep-alive path still
monitors and restarts the eight discovery lanes, and leave fresh runtime
evidence before closing the issue.

## Current wiring

- `scripts/buy31716-fleet-keep-alive.sh` remains the active watchdog for the
  mixed-workspace 8-lane fleet.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` still runs that
  watchdog as a oneshot from this workspace.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still enforces the
  5-minute cadence via `OnUnitActiveSec=5min`.

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
- The live watchdog wrote a clean tick from `2026-06-09T05:44:38Z` through
  `2026-06-09T05:44:39Z` in
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`.
- Host disk use during the tick was `88%`, below the `95%` write-side guard.
- No restart or escalation was needed on this tick.

## Lane state after tick

| lane | status |
| --- | --- |
| `burst_discovery` | OK, pid `3907215` |
| `brand_sitemap_miner` | OK, pid `2316250`, heartbeat age `19s` |
| `retailer_sitemap_miner` | OK, pid `2316426`, heartbeat age `14s` |
| `fast_wc_probe` | OK, pid `3848747` |
| `shopify_index_expansion` | OK, pid `3848851` |
| `crate_deep_page` | OK, pid `2316670` |
| `hunt2_page` | OK, pid `4120587` |
| `stock_page` | OK, pid `2316883` |

## Evidence

- Live state file
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
  advanced `disk_last_sampled_at` to `2026-06-09T05:44:38Z`, set
  `disk_use_pct` to `88`, and kept all tracked lane dead counts at `0`.
- Live escalation file
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json`
  still ends with the historical `2026-06-08T05:51:52Z`
  `shopify_index_expansion` entry; this closeout tick added no new escalation.
- Immediate `pgrep -af` confirmation after the tick showed the expected process
  set for all eight lanes.

## Disposition

`BUY-37068` can close `done`: the keep-alive watchdog, 5-minute timer wiring,
and live eight-lane fleet state all verified cleanly on `2026-06-09T05:44Z`.
