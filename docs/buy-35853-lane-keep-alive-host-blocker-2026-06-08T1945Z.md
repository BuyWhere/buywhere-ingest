# BUY-35853 — Oracle lane keep-alive host blocker (2026-06-08T19:45Z)

Issue scope: confirm whether the BUY-30854 Oracle lane keep-alive is fully live on
the host, not just wired in the repository.

## Repo verification

The checked-out repo is ready for 5-minute cadence:

- `systemd/paperclip-lane-keep-alive.service` is `Type=oneshot`
- `systemd/paperclip-lane-keep-alive.timer` sets `OnBootSec=1min`,
  `OnUnitActiveSec=5min`, `Persistent=true`
- `scripts/deploy-systemd-units.sh` installs both the service and timer
- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash -n scripts/deploy-systemd-units.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`

`systemd-analyze verify` passed for the Oracle units. The only output was
unrelated host noise from `hindsight.service`.

## Host reality

This runner cannot complete the deployment:

```text
$ id
uid=997(paperclip) gid=987(paperclip) groups=987(paperclip)

$ sudo -n true
sudo: a password is required
```

The target timer is also not installed on the host yet:

```text
$ systemctl status paperclip-lane-keep-alive.timer --no-pager
Unit paperclip-lane-keep-alive.timer could not be found.

$ systemctl list-timers paperclip-lane-keep-alive.timer --no-pager
NEXT LEFT LAST PASSED UNIT ACTIVATES

0 timers listed.
Pass --all to see loaded but inactive timers, too.
```

## Disposition

BUY-30854's code path works, but BUY-35853 is not complete because the actual
host-level 5-minute timer is still missing.

Required unblock owner/action:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-lane-keep-alive.timer --no-pager
systemctl list-timers paperclip-lane-keep-alive.timer --no-pager
```
