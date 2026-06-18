# BUY-36353 — BUY-30854 Oracle lane keep-alive closeout (2026-06-08T23:36Z)

Scope: confirm the current checkout still provides the intended 5-minute
restart path for dead Oracle lanes and that a fresh watchdog tick succeeds in
the live Oracle workspace.

## Verification run

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`

## What this heartbeat confirmed

- `scripts/buy30854-lane-keep-alive.sh` is the active watchdog implementation.
- `systemd/paperclip-lane-keep-alive.service` runs it as a oneshot service.
- `systemd/paperclip-lane-keep-alive.timer` keeps the cadence at
  `OnUnitActiveSec=5min`.
- `scripts/deploy-systemd-units.sh` includes both
  `paperclip-lane-keep-alive.service` and `paperclip-lane-keep-alive.timer` in
  the root deployment path.

## Fresh runtime evidence

The manual watchdog run at `2026-06-08T23:36:58Z` appended this block to
`logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-08T23:36:58Z =====
[2026-06-08T23:36:58Z] deep_page_loop OK pid=2778633
[2026-06-08T23:36:58Z] sustained_loop OK pid=2691392
[2026-06-08T23:36:58Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T23:36:58Z] keep-alive tick complete
```

`data/buy30854-keep-alive-state.json` after the run:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

## Note on systemd verification

`systemd-analyze verify` still emits one unrelated host warning for
`/etc/systemd/system/hindsight.service`:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

That warning is outside the Oracle keep-alive units. No
`paperclip-lane-keep-alive` unit errors were reported.

## Disposition

This issue can close `done`. The current checkout contains the 5-minute Oracle
keep-alive/restart wiring, deployment includes the service and timer units, and
the latest watchdog tick completed successfully with both primary Oracle lanes
healthy.
