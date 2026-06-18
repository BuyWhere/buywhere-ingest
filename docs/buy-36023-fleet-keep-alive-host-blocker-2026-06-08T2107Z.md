# BUY-36023 — BUY-31716 fleet keep-alive host-install blocker (2026-06-08T21:07Z)

## Summary

The `BUY-31716` fleet keep-alive watchdog is functional in the live workspace
and can restart dead lanes, but the host still does not have
`paperclip-buy31716-fleet-keep-alive.timer` installed under systemd. That
means the repo-side implementation is ready while the promised host-level
5-minute cadence remains blocked on a root-capable operator step.

## Verification

Commands run from the project workspace:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c \
  bash scripts/buy31716-fleet-keep-alive.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
```

Observed results:

- `bash -n` passed.
- The live keep-alive tick refreshed the shared Oracle-workspace log and state.
- `systemctl status ...timer` returned `Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.`
- `systemctl list-timers ...timer` returned `0 timers listed.`

## Live evidence

Recent log blocks from
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-08T20:57:43Z =====
[2026-06-08T20:57:43Z] host disk use=83% (threshold=95%, recover=90%)
[2026-06-08T20:57:43Z] burst_discovery DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-08T20:57:45Z] burst_discovery restarted pid=2691392 (spawned=2691390)
[2026-06-08T20:57:45Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=4s
[2026-06-08T20:57:45Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=11s
[2026-06-08T20:57:45Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-08T20:57:45Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-08T20:57:45Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-08T20:57:45Z] hunt2_page OK pid=2316743 (no_heartbeat_file)
[2026-06-08T20:57:45Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-08T20:57:45Z] keep-alive tick complete

===== BUY-31716 fleet keep-alive tick 2026-06-08T21:06:14Z =====
[2026-06-08T21:06:14Z] burst_discovery OK pid=2691392 (no_heartbeat_file)
[2026-06-08T21:06:14Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=3s
[2026-06-08T21:06:14Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=27s
[2026-06-08T21:06:14Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-08T21:06:14Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-08T21:06:14Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-08T21:06:14Z] hunt2_page OK pid=2316743 (no_heartbeat_file)
[2026-06-08T21:06:14Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-08T21:06:14Z] keep-alive tick complete
```

State file after the run:

```json
{
  "brand_sitemap_miner": 0,
  "burst_discovery": 0,
  "crate_deep_page": 0,
  "disk_last_sampled_at": "2026-06-08T21:07:41Z",
  "disk_pressure_pauses": 10,
  "disk_use_pct": "85",
  "fast_wc_probe": 0,
  "hunt2_page": 0,
  "retailer_sitemap_miner": 0,
  "shopify_index_expansion": 0,
  "stock_page": 0
}
```

## Blocker

Unblock owner: a root-capable host operator.

Required action:

```bash
cd /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default
sudo bash scripts/deploy-systemd-units.sh
sudo systemctl enable --now paperclip-buy31716-fleet-keep-alive.timer
sudo systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
sudo systemctl list-timers --all paperclip-buy31716-fleet-keep-alive.timer --no-pager
```
