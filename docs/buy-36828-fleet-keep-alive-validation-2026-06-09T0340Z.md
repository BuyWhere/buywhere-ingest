# BUY-36828 — BUY-31716 fleet keep-alive validation (2026-06-09T03:40Z)

Validated the live 5-minute keep-alive watchdog for the eight BUY-31716
discovery lanes.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c \
  bash scripts/buy31716-fleet-keep-alive.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated
  `/etc/systemd/system/hindsight.service` warning; the BUY-36828 service and
  timer units verified cleanly.
- Manual keep-alive execution completed successfully.
- The live keep-alive log already showed a steady 5-minute cadence before and
  after the manual run:
  - `2026-06-09T03:24:31Z` tick complete
  - `2026-06-09T03:29:31Z` tick complete
  - `2026-06-09T03:34:34Z` tick complete
  - `2026-06-09T03:39:26Z` tick complete
- On the `2026-06-09T03:29Z` tick, `hunt2_page` was detected dead and
  restarted successfully as pid `4120587`; the next two ticks saw it healthy.
- The shared state file updated `disk_last_sampled_at` to
  `2026-06-09T03:39:26Z`, `disk_use_pct` to `87`, and preserved `0` dead counts
  for all eight tracked lanes:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`,
  `hunt2_page`, `stock_page`.

## Operational Note

`systemctl status/list-timers` still reports
`paperclip-buy31716-fleet-keep-alive.timer` as not installed on the host.
That does not block the issue's stated behavior: the watchdog is already firing
on a 5-minute cadence and is actively restarting dead lanes. Host-level systemd
deployment remains an optional follow-up if the team wants a second scheduler
path in addition to the current live routine.
