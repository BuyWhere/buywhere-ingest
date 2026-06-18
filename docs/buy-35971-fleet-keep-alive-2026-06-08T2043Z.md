# BUY-35971 — BUY-31716 fleet keep-alive 5-minute restart check

Timestamp: 2026-06-08T20:43Z

## Summary

The live `BUY-31716` watchdog path is healthy in the Oracle workspace, but the
host-level `paperclip-buy31716-fleet-keep-alive.timer` is still not installed.
This runner cannot complete the deploy because `sudo` requires a password, so
the remaining work is a root-capable host operator action.

## Verification

Commands run:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify \
  systemd/paperclip-buy31716-fleet-keep-alive.service \
  systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c \
  bash scripts/buy31716-fleet-keep-alive.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
sudo -n true
```

Observed results:

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated
  `/etc/systemd/system/hindsight.service` warning and no errors for the BUY-31716
  service or timer units.
- The live watchdog tick completed successfully at `2026-06-08T20:37:34Z`.
- `systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned `Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.`
- `sudo -n true` returned `sudo: a password is required`.

## Live runtime evidence

Latest keep-alive log block from
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-08T20:37:34Z =====
[2026-06-08T20:37:34Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-08T20:37:34Z] host disk use=83% (threshold=95%, recover=90%)
[2026-06-08T20:37:34Z] burst_discovery OK pid=2350985 (no_heartbeat_file)
[2026-06-08T20:37:34Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=24s
[2026-06-08T20:37:34Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=1s
[2026-06-08T20:37:34Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-08T20:37:34Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-08T20:37:34Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-08T20:37:34Z] hunt2_page OK pid=2316743 (no_heartbeat_file)
[2026-06-08T20:37:34Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-08T20:37:34Z] keep-alive tick complete
```

State file
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
after the run:

- `disk_last_sampled_at = 2026-06-08T20:37:34Z`
- `disk_use_pct = 83`
- dead counters remained `0` for the tracked lanes present in the state file

## Unblock action

A root-capable host operator needs to install the timer on the host:

```bash
cd /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
```
