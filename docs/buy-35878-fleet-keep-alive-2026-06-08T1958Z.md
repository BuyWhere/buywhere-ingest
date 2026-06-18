# BUY-35878 — BUY-31716 fleet keep-alive heartbeat check

Timestamp: 2026-06-08T19:58:05Z

## Summary

The BUY-31716 fleet keep-alive script is healthy when run directly from the
Oracle workspace: all 8 tracked lanes reported `OK` on the latest tick and the
state file still shows dead counters at `0`. The unresolved gap is host
installation of the 5-minute systemd timer. This runner still cannot find
`paperclip-buy31716-fleet-keep-alive.timer`, so automatic restart cadence
remains blocked on a root-owned deploy step.

## Commands run

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c \
  bash scripts/buy31716-fleet-keep-alive.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
```

## Latest watchdog evidence

Latest block from
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-08T19:58:05Z =====
[2026-06-08T19:58:05Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-08T19:58:05Z] host disk use=84% (threshold=95%, recover=90%)
[2026-06-08T19:58:05Z] burst_discovery OK pid=2350985 (no_heartbeat_file)
[2026-06-08T19:58:05Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=27s
[2026-06-08T19:58:05Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=6s
[2026-06-08T19:58:05Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-08T19:58:05Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-08T19:58:05Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-08T19:58:05Z] hunt2_page OK pid=2316743 (no_heartbeat_file)
[2026-06-08T19:58:05Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-08T19:58:05Z] keep-alive tick complete
```

State file
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
after this tick:

- `disk_last_sampled_at = 2026-06-08T19:58:05Z`
- `disk_use_pct = 84`
- all 8 tracked lane counters remain `0`

## Host timer status

- `systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned `Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.`
- `systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned `0 timers listed.`

## Unblock action

A root-capable operator needs to install the systemd units from this checkout:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
```
