# BUY-35856 — BUY-31716 fleet keep-alive 5-minute restart status

Timestamp: 2026-06-08T19:43:30Z

## Summary

The repository side of the `BUY-31716` fleet keep-alive is present for all 8
discovery lanes and the matching 5-minute systemd timer is wired into the
deployment script. The live host still does not have the unit installed, so the
production 5-minute restart path is blocked on a root-capable operator running
the deploy step.

## Repo evidence

- `scripts/buy31716-fleet-keep-alive.sh` calls `restart_if_dead` for 8 lanes at
  lines 410-461:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`,
  `hunt2_page`, and `stock_page`.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` sets:
  `OnBootSec=1min` and `OnUnitActiveSec=5min`.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` runs:
  `ExecStart=/bin/bash scripts/buy31716-fleet-keep-alive.sh`.
- `scripts/deploy-systemd-units.sh` includes both
  `paperclip-buy31716-fleet-keep-alive.service` and
  `paperclip-buy31716-fleet-keep-alive.timer` in `PLAIN_UNITS`.

## Verification

- `bash -n scripts/buy31716-fleet-keep-alive.sh`
- `bash -n scripts/deploy-systemd-units.sh`
- `systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer`

`systemd-analyze verify` accepted both units. The only emitted warning was
unrelated host noise from `/etc/systemd/system/hindsight.service`:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

## Live host status

- `systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned: `Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.`
- `systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned `0 timers listed`.

## Blocker

The live 5-minute restart path for the 8 `BUY-31716` discovery lanes is blocked
until a root-capable operator installs the units onto the host.

Required operator action:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
```
