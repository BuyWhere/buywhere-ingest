# BUY-35838 — BUY-31716 fleet keep-alive 5-minute restart status

Timestamp: 2026-06-08T19:33:50Z

## Summary

The repository contains the `BUY-31716` fleet keep-alive implementation for
all 8 discovery lanes and the matching 5-minute systemd unit pair, but the
live host does not currently have those units installed.

## Repo evidence

- `scripts/buy31716-fleet-keep-alive.sh` defines `restart_if_dead` entries for
  exactly 8 labels:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`,
  `hunt2_page`, and `stock_page`.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` uses:
  `OnBootSec=1min` and `OnUnitActiveSec=5min`.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` runs:
  `ExecStart=/bin/bash scripts/buy31716-fleet-keep-alive.sh`.
- `scripts/deploy-systemd-units.sh` includes both:
  `paperclip-buy31716-fleet-keep-alive.service` and
  `paperclip-buy31716-fleet-keep-alive.timer` in `PLAIN_UNITS`.

## Verification

- `bash -n scripts/buy31716-fleet-keep-alive.sh`
- `bash -n scripts/deploy-systemd-units.sh`
- `systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer`

`systemd-analyze verify` accepted the `BUY-31716` units. The only emitted
warning was unrelated host noise from `/etc/systemd/system/hindsight.service`.

## Live host status

- `systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned: `Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.`
- `systemctl status paperclip-buy31716-fleet-keep-alive.service --no-pager`
  returned: `Unit paperclip-buy31716-fleet-keep-alive.service could not be found.`
- `systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned `0 timers listed`.

## Blocker

The live 5-minute restart path for the 8 BUY-31716 lanes is blocked on a
root-capable operator installing the units onto the host.

Required operator action:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
```
