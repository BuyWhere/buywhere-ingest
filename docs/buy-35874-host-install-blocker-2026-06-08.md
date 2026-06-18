# BUY-35874 — BUY-31716 fleet keep-alive host install blocker (2026-06-08)

Issue scope: install the `BUY-31716` fleet keep-alive systemd timer on the host.

## What was verified

- The target unit files exist in-repo:
  - `systemd/paperclip-buy31716-fleet-keep-alive.service`
  - `systemd/paperclip-buy31716-fleet-keep-alive.timer`
- The service runs `scripts/buy31716-fleet-keep-alive.sh` from the current
  workspace root.
- The timer cadence is `OnBootSec=1min`, `OnUnitActiveSec=5min`,
  `Persistent=true`.
- The deployment helper already includes both units in `PLAIN_UNITS`:
  `scripts/deploy-systemd-units.sh`

## Blocker

Host installation requires root because the units must be copied to
`/etc/systemd/system` and enabled via `systemctl`.

This session does not have non-interactive sudo:

```text
$ sudo -n true
sudo: a password is required
```

The host confirms the timer is not installed yet:

```text
$ systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.
```

## Install commands for a host operator with sudo

```bash
cd /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default
sudo bash scripts/deploy-systemd-units.sh
sudo systemctl enable --now paperclip-buy31716-fleet-keep-alive.timer
sudo systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
sudo systemctl list-timers --all 'paperclip-buy31716-fleet-keep-alive.timer'
```

## Expected result after unblock

- `/etc/systemd/system/paperclip-buy31716-fleet-keep-alive.service` exists
- `/etc/systemd/system/paperclip-buy31716-fleet-keep-alive.timer` exists
- `systemctl status paperclip-buy31716-fleet-keep-alive.timer` shows `active`
- `systemctl list-timers` shows the next 5-minute keep-alive fire
