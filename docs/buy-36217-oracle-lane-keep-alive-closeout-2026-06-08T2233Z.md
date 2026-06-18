# BUY-36217 — BUY-30854 Oracle lane keep-alive closeout (2026-06-08T22:33Z)

Issue scope: confirm that the Oracle keep-alive watchdog still performs the
5-minute dead-lane restart check and that the current workspace wiring matches
that expectation.

## Commands run

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `tail -n 12 logs/buy30854_keep_alive.log`
- `cat data/buy30854-keep-alive-state.json`
- `rg -n "paperclip-lane-keep-alive\\.(service|timer)|buy30854-lane-keep-alive" scripts/deploy-systemd-units.sh systemd`

## Current heartbeat evidence

The direct watchdog invocation appended a clean tick at `2026-06-08T22:33:05Z`:

```text
===== keep-alive tick 2026-06-08T22:33:05Z =====
[2026-06-08T22:33:05Z] deep_page_loop OK pid=2778633
[2026-06-08T22:33:05Z] sustained_loop OK pid=2691392
[2026-06-08T22:33:05Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T22:33:05Z] keep-alive tick complete
```

`data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

## Wiring still present

- `systemd/paperclip-lane-keep-alive.service` runs
  `scripts/buy30854-lane-keep-alive.sh` as a oneshot watchdog.
- `systemd/paperclip-lane-keep-alive.timer` keeps the 5-minute cadence with
  `OnUnitActiveSec=5min`.
- `scripts/deploy-systemd-units.sh` still deploys both
  `paperclip-lane-keep-alive.service` and `paperclip-lane-keep-alive.timer`.

## Disposition

`BUY-36217` can close `done`: this heartbeat verified a fresh successful
watchdog tick, zero consecutive dead ticks for the live Oracle lanes, and the
expected 5-minute systemd wiring in the current workspace.
