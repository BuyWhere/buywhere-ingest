# BUY-36367 — Oracle lane keep-alive host blocker (2026-06-08T23:41Z)

Issue scope: confirm whether the `BUY-30854` Oracle lane keep-alive is now a
live 5-minute host restart path for dead Oracle lanes, and leave a final
disposition for the current heartbeat.

## Verification run

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash -n scripts/deploy-systemd-units.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `systemctl status paperclip-lane-keep-alive.timer --no-pager`
- `systemctl list-timers --all paperclip-lane-keep-alive.timer --no-pager`
- `id -u`
- `sudo -n true`

## What passed

- Repo-side syntax checks passed for the watchdog and deploy helper.
- `systemd-analyze verify` reported no Oracle-unit-specific errors; the only
  output remains the unrelated host warning from `/etc/systemd/system/hindsight.service`.
- A fresh manual watchdog tick completed at `2026-06-08T23:41:35Z` and logged:

```text
===== keep-alive tick 2026-06-08T23:41:35Z =====
[2026-06-08T23:41:35Z] deep_page_loop OK pid=2778633
[2026-06-08T23:41:35Z] sustained_loop OK pid=2691392
[2026-06-08T23:41:35Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T23:41:35Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

## Remaining blocker

The host-level timer is still absent:

```text
$ systemctl status paperclip-lane-keep-alive.timer --no-pager
Unit paperclip-lane-keep-alive.timer could not be found.
```

This agent also cannot install it directly in the current heartbeat:

```text
$ id -u
997

$ sudo -n true
sudo: a password is required
```

## Disposition

`BUY-36367` should be `blocked`, not `in_progress`. The code path is present and
manual watchdog execution is healthy, but the actual 5-minute continuation path
is still missing on the host until someone with root installs the unit.

Required unblock owner/action:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-lane-keep-alive.timer --no-pager
systemctl list-timers --all paperclip-lane-keep-alive.timer --no-pager
```
