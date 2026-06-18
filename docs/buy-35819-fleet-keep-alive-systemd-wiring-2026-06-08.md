# BUY-35819 — BUY-31716 fleet keep-alive systemd wiring

Timestamp: 2026-06-08T19:23Z

## Summary

The repository already contained the 5-minute `BUY-31716` fleet keep-alive
unit pair:

- `systemd/paperclip-buy31716-fleet-keep-alive.service`
- `systemd/paperclip-buy31716-fleet-keep-alive.timer`

The gap was deployment wiring. `scripts/deploy-systemd-units.sh` did not copy,
enable, or start either `BUY-31716` unit, so a root operator running the
installer would not put the 8-lane fleet watchdog onto the host timer path.

## Change

Updated `scripts/deploy-systemd-units.sh` so `PLAIN_UNITS` now includes:

- `paperclip-buy31716-fleet-keep-alive.service`
- `paperclip-buy31716-fleet-keep-alive.timer`

This keeps the `BUY-31716` fleet watchdog aligned with the existing
deployment workflow used for other long-running units.

## Verification

- `bash -n scripts/deploy-systemd-units.sh`
- `systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer`

`systemd-analyze verify` accepted the `BUY-31716` units. The only emitted
warning was unrelated host noise from `/etc/systemd/system/hindsight.service`.

## Remaining operator step

This workspace cannot write `/etc/systemd/system`, so a root-capable operator
still needs to run:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer
```

Once that is done, the `BUY-31716` watchdog will be installed and enabled on
the host's 5-minute timer cadence for the 8 discovery lanes.
