# BUY-38091 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T14:17:00Z)

Issue scope: execute the `BUY-30854` 5-minute Oracle lane keep-alive watchdog in
this checkout, verify the dead-lane restart path still works, and record the
current Oracle lane state.

## What I verified

- `scripts/buy30854-lane-keep-alive.sh` still drives the watchdog and keeps the
  detached restart path that closes FD 9 before relaunch.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the 5-minute cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported only the known unrelated
  `/etc/systemd/system/hindsight.service` warning.

## Runtime evidence

- A fresh manual tick completed successfully at `2026-06-09T14:16:36Z`:

```text
===== keep-alive tick 2026-06-09T14:16:36Z =====
[2026-06-09T14:16:36Z] deep_page_loop STOPPED (already absent)
[2026-06-09T14:16:36Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T14:16:36Z] sustained_loop OK pid=3131982
[2026-06-09T14:16:36Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T14:16:36Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T14:16:36Z] keep-alive tick complete
```

- The same live log contains fresh dead-lane restart proof from this heartbeat:

```text
[2026-06-09T14:12:22Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T14:12:24Z] sustained_loop restarted pid=3131982 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3131979
[2026-06-09T14:13:04Z] sustained_loop OK pid=3131982
```

- `data/buy30854-keep-alive-state.json` now shows zero dead counts for all
  tracked Oracle lanes:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Current lane state

- `deep_page_loop` is intentionally absent because
  `data/buy30590-deep-page-loop.stopped` is present.
- `woocommerce_discover` is intentionally skipped because
  `data/checkpoints/buy30590_woocommerce.completed` is present.
- `lane_supervisor` is intentionally skipped because
  `data/buy30727-supervisor.stopped` is present.
- `sustained_loop` is currently live as pid `3131982`.

## Disposition

`BUY-38091` can close `done`: the Oracle keep-alive watchdog is still wired on a
5-minute cadence, it executed successfully in this heartbeat, and the restart
path fired successfully for `sustained_loop` on `2026-06-09T14:12:22Z`.
