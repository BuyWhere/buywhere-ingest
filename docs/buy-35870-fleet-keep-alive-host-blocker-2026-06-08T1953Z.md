# BUY-35870 — BUY-31716 fleet keep-alive host blocker

Checked at `2026-06-08T19:53:24Z` in Oracle's workspace.

## What is present in the repo

- `scripts/buy31716-fleet-keep-alive.sh` is the active watchdog for the 8
  BUY-31716 discovery lanes.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` is a `Type=oneshot`
  unit that runs `ExecStart=/bin/bash scripts/buy31716-fleet-keep-alive.sh`.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` schedules the watchdog
  with `OnBootSec=1min` and `OnUnitActiveSec=5min`.
- `scripts/deploy-systemd-units.sh` already includes both BUY-31716 unit names
  in `PLAIN_UNITS`.

## Host checks

Commands run:

```bash
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
bash scripts/deploy-systemd-units.sh
```

Observed results:

```text
Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.
ERROR: This script must be run as root (use sudo).
```

## Conclusion

The 5-minute BUY-31716 fleet restart path is implemented in the workspace but
not installed into the host systemd registry. Oracle cannot complete the live
activation step from this heartbeat because the only deploy path is root-only.

## Required operator action

Run the root-owned deploy step from this repo checkout:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
```
