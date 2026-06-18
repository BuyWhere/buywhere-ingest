# BUY-35816 — BUY-30854 lane keep-alive verification (2026-06-08)

Issue scope: confirm the Oracle lane keep-alive path restarts dead Oracle lanes
on a 5-minute cadence and leaves healthy lanes alone.

## What was verified

- `scripts/buy30854-lane-keep-alive.sh` is the active watchdog implementation
  for the Oracle lane family.
- the watchdog now takes an exclusive lock before each tick and writes both
  state files via atomic rename, so overlapping invocations cannot clobber the
  dead-tick counters.
- `systemd/paperclip-lane-keep-alive.service` is wired as `Type=oneshot`.
- `systemd/paperclip-lane-keep-alive.timer` schedules the watchdog with
  `OnUnitActiveSec=5min` and `Persistent=true`.
- `scripts/deploy-systemd-units.sh` installs both the service and timer.

## Verification commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default \
  bash scripts/buy30854-lane-keep-alive.sh
WORKSPACE_ROOT=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default \
  bash scripts/buy30854-lane-keep-alive.sh
flock data/buy30854-keep-alive.lock -c 'sleep 3' &
WORKSPACE_ROOT=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default \
  bash scripts/buy30854-lane-keep-alive.sh
```

## Live restart evidence

From `logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-08T19:22:54Z =====
[2026-06-08T19:22:54Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-08T19:22:56Z] deep_page_loop restarted pid=2365475 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
[2026-06-08T19:22:56Z] sustained_loop OK pid=2350985
[2026-06-08T19:22:56Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T19:22:56Z] keep-alive tick complete
===== keep-alive tick 2026-06-08T19:23:07Z =====
[2026-06-08T19:23:07Z] deep_page_loop OK pid=2365475
[2026-06-08T19:23:07Z] sustained_loop OK pid=2350985
[2026-06-08T19:23:07Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T19:23:07Z] keep-alive tick complete
===== keep-alive tick 2026-06-08T20:08:55Z =====
[2026-06-08T20:08:55Z] deep_page_loop OK pid=2511568
[2026-06-08T20:08:55Z] sustained_loop OK pid=2350985
[2026-06-08T20:08:55Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T20:08:55Z] keep-alive tick complete
[2026-06-08T20:08:56Z] keep-alive tick skipped — another instance already holds /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive.lock
```

## Result

The issue contract is satisfied:

- a dead Oracle lane was detected and restarted within the watchdog tick
- the next tick observed the restarted lane as healthy
- overlapping invocations now skip cleanly instead of racing the dead-tick
  state file
- `data/buy30854-keep-alive-state.json` returned to:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

Notes:

- `lane_supervisor` remains intentionally skipped because
  `data/buy30727-supervisor.stopped` is present under BUY-31452.
- `systemd-analyze verify` emitted one warning for unrelated installed unit
  `hindsight.service`; the Oracle keep-alive service and timer validated.
