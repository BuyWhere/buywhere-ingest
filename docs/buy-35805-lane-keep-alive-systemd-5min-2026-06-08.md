# BUY-35805 — BUY-30854 lane keep-alive systemd 5-minute wiring

## Summary

The repo already had the Oracle keep-alive watchdog implementation in
`scripts/buy30854-lane-keep-alive.sh`, but the systemd unit was wired as a
single `Type=simple` service with no timer. That shape does not provide a true
5-minute cadence after a clean exit.

This heartbeat converts the systemd wiring to the same `oneshot + .timer`
pattern already used by the BUY-31716 fleet keep-alive path and updates the
deployment script so the timer is installed and enabled with the service.

## Changes

- changed `systemd/paperclip-lane-keep-alive.service` from `Type=simple` to
  `Type=oneshot`
- removed `Restart=on-failure` / `RestartSec=30` from the Oracle keep-alive
  service because cadence now belongs to the timer
- added `systemd/paperclip-lane-keep-alive.timer` with:
  - `OnBootSec=1min`
  - `OnUnitActiveSec=5min`
  - `Persistent=true`
- updated `scripts/deploy-systemd-units.sh` so
  `paperclip-lane-keep-alive.timer` is copied to `/etc/systemd/system`,
  enabled, and started alongside the service

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash -n scripts/deploy-systemd-units.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`

`systemd-analyze verify` completed without complaints about the new Oracle
units. The only emitted warning was unrelated global noise from an existing
host unit:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

## Remaining operator step

This runner is not root (`uid 997`), so it could not run
`scripts/deploy-systemd-units.sh` against `/etc/systemd/system` in this
heartbeat. A root-capable operator still needs to deploy the updated units and
confirm:

```text
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-lane-keep-alive.timer --no-pager
systemctl list-timers paperclip-lane-keep-alive.timer
```
