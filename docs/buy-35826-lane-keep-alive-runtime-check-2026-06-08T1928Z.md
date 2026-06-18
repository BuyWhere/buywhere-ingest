# BUY-35826 — Oracle lane keep-alive runtime check (2026-06-08T19:28Z)

Issue scope: verify the BUY-30854 Oracle lane keep-alive still restarts dead
lanes and confirm whether the 5-minute systemd cadence is installed on the
host.

## What I verified in this heartbeat

- `scripts/buy30854-lane-keep-alive.sh` still performs dead-lane detection and
  restart logic for the Oracle lane family.
- `systemd/paperclip-lane-keep-alive.service` is a `Type=oneshot` unit.
- `systemd/paperclip-lane-keep-alive.timer` is configured with
  `OnBootSec=1min`, `OnUnitActiveSec=5min`, and `Persistent=true`.
- `scripts/deploy-systemd-units.sh` includes both
  `paperclip-lane-keep-alive.service` and `paperclip-lane-keep-alive.timer` in
  the deploy list.

## Verification commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default \
  bash scripts/buy30854-lane-keep-alive.sh
WORKSPACE_ROOT=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default \
  bash scripts/buy30854-lane-keep-alive.sh
systemctl status paperclip-lane-keep-alive.timer --no-pager
systemctl list-timers paperclip-lane-keep-alive.timer --no-pager
```

## Fresh live restart evidence

From `logs/buy30854_keep_alive.log` after the manual watchdog tick in this
heartbeat:

```text
===== keep-alive tick 2026-06-08T19:28:07Z =====
[2026-06-08T19:28:07Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-08T19:28:09Z] deep_page_loop restarted pid=2384091 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
[2026-06-08T19:28:09Z] sustained_loop OK pid=2350985
[2026-06-08T19:28:09Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T19:28:09Z] keep-alive tick complete
===== keep-alive tick 2026-06-08T19:28:26Z =====
[2026-06-08T19:28:26Z] deep_page_loop OK pid=2384091
[2026-06-08T19:28:26Z] sustained_loop OK pid=2350985
[2026-06-08T19:28:26Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T19:28:26Z] keep-alive tick complete
```

State file after the healthy follow-up tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

## Runtime blocker

The repository wiring is ready, but the host-level 5-minute timer is not
currently installed here:

```text
Unit paperclip-lane-keep-alive.timer could not be found.
NEXT LEFT LAST PASSED UNIT ACTIVATES

0 timers listed.
```

That means the keep-alive logic itself is working, but the promised automatic
5-minute cadence still depends on a root-capable operator deploying the updated
systemd units on the host.

## Required unblock action

Run:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-lane-keep-alive.timer --no-pager
systemctl list-timers paperclip-lane-keep-alive.timer --no-pager
```

After that succeeds, BUY-35826 can be closed as fully live.
