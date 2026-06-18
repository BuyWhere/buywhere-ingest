# BUY-35862 — BUY-31716 fleet keep-alive 5-minute restart check

Timestamp: 2026-06-08T19:48:37Z

## Summary

The `BUY-31716` fleet keep-alive path is working in the live Oracle workspace:
the watchdog tick completed successfully and reported all 8 discovery lanes
healthy. The remaining gap is host installation of the systemd timer. This
runner still cannot find `paperclip-buy31716-fleet-keep-alive.timer`, so the
promised automatic 5-minute cadence is blocked on a root deploy step.

## Action taken

- Ran the live watchdog path directly against the Oracle workspace:

```bash
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c \
  bash scripts/buy31716-fleet-keep-alive.sh
```

- Re-verified the repo-side systemd units and current host timer visibility:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify \
  systemd/paperclip-buy31716-fleet-keep-alive.service \
  systemd/paperclip-buy31716-fleet-keep-alive.timer
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
```

## Live runtime evidence

Latest log block from
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-08T19:48:37Z =====
[2026-06-08T19:48:37Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-08T19:48:37Z] host disk use=84% (threshold=95%, recover=90%)
[2026-06-08T19:48:37Z] burst_discovery OK pid=2350985 (no_heartbeat_file)
[2026-06-08T19:48:37Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=29s
[2026-06-08T19:48:37Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=24s
[2026-06-08T19:48:38Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-08T19:48:38Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-08T19:48:38Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-08T19:48:38Z] hunt2_page OK pid=2316743 (no_heartbeat_file)
[2026-06-08T19:48:38Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-08T19:48:38Z] keep-alive tick complete
```

State file
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
now shows:

- `disk_last_sampled_at = 2026-06-08T19:48:37Z`
- `disk_use_pct = 84`
- dead counters at `0` for all 8 tracked lanes

Immediate process-table spot check still showed the expected lane processes for:

- `burst_discovery`
- `brand_sitemap_miner`
- `retailer_sitemap_miner`
- `fast_wc_probe`
- `shopify_index_expansion`
- `crate_deep_page`
- `hunt2_page`
- `stock_page`

## Host timer status

- `systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned: `Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.`
- `systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned `0 timers listed`.

## Blocker and unblock action

The repo and live watchdog behavior are ready, but the automatic 5-minute
restart cadence is still blocked until a root-capable operator installs the
units on the host:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
```
