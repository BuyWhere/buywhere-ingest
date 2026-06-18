# BUY-36875 — BUY-30854 lane keep-alive verification (2026-06-09)

Issue scope: confirm the Oracle lane keep-alive path restarts dead Oracle lanes
on a 5-minute cadence and leaves healthy lanes alone.

## Current implementation

- `scripts/buy30854-lane-keep-alive.sh` is the active watchdog and checks
  `deep_page_loop`, `sustained_loop`, `woocommerce_discover`, and
  `lane_supervisor`.
- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a
  `Type=oneshot` unit in the Oracle workspace.
- `systemd/paperclip-lane-keep-alive.timer` schedules the watchdog with
  `OnUnitActiveSec=5min` and `Persistent=true`.
- `scripts/deploy-systemd-units.sh` installs both the service and timer.

## Verification

Commands run on 2026-06-09:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default \
  bash scripts/buy30854-lane-keep-alive.sh
```

`systemd-analyze verify` only emitted the known unrelated host warning for
`/etc/systemd/system/hindsight.service`; the Oracle keep-alive service and
timer validated successfully.

## Live tick evidence

From `logs/buy30854_keep_alive.log` after the manual watchdog tick:

```text
===== keep-alive tick 2026-06-09T04:09:24Z =====
[2026-06-09T04:09:24Z] deep_page_loop OK pid=3907026
[2026-06-09T04:09:24Z] sustained_loop OK pid=3907215
[2026-06-09T04:09:24Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T04:09:24Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T04:09:24Z] keep-alive tick complete
```

Current state file:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Result

The requested 5-minute restart path is in place and healthy:

- the watchdog is wired to a 5-minute systemd timer
- the watchdog can be executed directly in the Oracle workspace
- the current tick observed live Oracle lanes as healthy and reset dead counts
  to zero
- intentionally paused/completed lanes were skipped instead of being restarted
