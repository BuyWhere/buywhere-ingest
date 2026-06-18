# BUY-36013 — BUY-31716 fleet keep-alive host-install check (2026-06-08T21:06Z)

## Summary

The `BUY-31716` fleet keep-alive path is healthy in the workspace, but the
host still does not have `paperclip-buy31716-fleet-keep-alive.timer`
installed under systemd. This heartbeat re-verified the live watchdog run and
confirmed the remaining blocker is root-only host installation.

## Verification

Commands run from the project workspace:

```bash
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl cat paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemd-analyze verify \
  systemd/paperclip-buy31716-fleet-keep-alive.service \
  systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
sudo -n true
```

Observed results:

- `systemctl status ...timer` returned `Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.`
- `systemctl list-timers ...timer` returned `0 timers listed.`
- `systemctl cat ...timer` returned `No files found for paperclip-buy31716-fleet-keep-alive.timer.`
- `systemd-analyze verify` passed for the BUY-31716 units; the only output was
  the known unrelated warning from `/etc/systemd/system/hindsight.service`.
- `bash scripts/buy31716-fleet-keep-alive.sh` completed and refreshed the shared
  state file at
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`.
- `sudo -n true` failed with `sudo: a password is required`, so this workspace
  cannot perform the host install step non-interactively.

State excerpt after the manual tick:

```json
{
  "brand_sitemap_miner": 0,
  "burst_discovery": 0,
  "crate_deep_page": 0,
  "disk_last_sampled_at": "2026-06-08T21:06:14Z",
  "disk_pressure_pauses": 10,
  "disk_use_pct": "83",
  "fast_wc_probe": 0,
  "hunt2_page": 0,
  "retailer_sitemap_miner": 0,
  "shopify_index_expansion": 0,
  "stock_page": 0
}
```

## Remaining blocker

A root-capable host operator must install and enable the timer, for example:

```bash
cd /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default
sudo bash scripts/deploy-systemd-units.sh
sudo systemctl enable --now paperclip-buy31716-fleet-keep-alive.timer
sudo systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
sudo systemctl list-timers --all paperclip-buy31716-fleet-keep-alive.timer --no-pager
```
