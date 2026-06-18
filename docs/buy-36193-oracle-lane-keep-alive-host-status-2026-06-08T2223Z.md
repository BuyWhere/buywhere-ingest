# BUY-36193 — BUY-30854 Oracle lane keep-alive host status (2026-06-08T22:23Z)

Issue scope: confirm whether the `BUY-30854` Oracle lane keep-alive is fully
live as a host-level 5-minute restart path for dead Oracle lanes.

## What this heartbeat verified

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash -n scripts/deploy-systemd-units.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `systemctl status paperclip-lane-keep-alive.timer --no-pager`
- `systemctl list-timers --all paperclip-lane-keep-alive.timer --no-pager`

## Runtime result

The manual watchdog fire from this heartbeat appended a clean tick at
`2026-06-08T22:23:44Z`:

```text
===== keep-alive tick 2026-06-08T22:23:44Z =====
[2026-06-08T22:23:44Z] deep_page_loop OK pid=2778633
[2026-06-08T22:23:44Z] sustained_loop OK pid=2691392
[2026-06-08T22:23:44Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T22:23:44Z] keep-alive tick complete
```

`data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

The active Oracle loop processes immediately after the tick were:

```text
2691392 node scripts/buy30331-sustained-loop.mjs
2778633 node scripts/buy30590-deep-page-loop.mjs
```

## Repo wiring status

The checked-out repo is ready for the intended cadence:

- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a
  `Type=oneshot` unit with
  `ExecStart=/bin/bash scripts/buy30854-lane-keep-alive.sh`
- `systemd/paperclip-lane-keep-alive.timer` defines the cadence with
  `OnBootSec=1min`, `OnUnitActiveSec=5min`, and `Persistent=true`
- `scripts/deploy-systemd-units.sh` includes both
  `paperclip-lane-keep-alive.service` and `paperclip-lane-keep-alive.timer`

`systemd-analyze verify` returned no Oracle-unit errors. The only output was the
known unrelated host warning from `hindsight.service`.

## Host blocker

The host still does not have the timer installed:

```text
$ systemctl status paperclip-lane-keep-alive.timer --no-pager
Unit paperclip-lane-keep-alive.timer could not be found.

$ systemctl list-timers --all paperclip-lane-keep-alive.timer --no-pager
NEXT LEFT LAST PASSED UNIT ACTIVATES

0 timers listed.
```

## Disposition

`BUY-30854` is functionally correct in the repo and the watchdog restart path
works when fired manually, but `BUY-36193` cannot close because the host-level
5-minute continuation path is still missing.

Required unblock owner/action:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-lane-keep-alive.timer --no-pager
systemctl list-timers --all paperclip-lane-keep-alive.timer --no-pager
```
