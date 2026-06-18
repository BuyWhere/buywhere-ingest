# BUY-36970 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T04:59:36Z)

Issue scope: run the 5-minute Oracle lane keep-alive watchdog in this heartbeat
and confirm the tracked Oracle lanes remain healthy, with evidence that the
dead-lane restart path is still live.

## What this heartbeat verified

- `scripts/buy30854-lane-keep-alive.sh` is still the active watchdog entrypoint.
- `systemd/paperclip-lane-keep-alive.timer` still schedules the watchdog on a
  5-minute cadence with `OnUnitActiveSec=5min`.
- `systemd/paperclip-lane-keep-alive.service` still executes
  `bash scripts/buy30854-lane-keep-alive.sh` from this workspace.
- A fresh manual watchdog tick completed successfully at
  `2026-06-09T04:59:36Z`.
- The live Oracle lanes were present immediately after the tick:
  - `deep_page_loop` pid `3907026`
  - `sustained_loop` pid `3907215`
- The restart path is not theoretical: the same live log shows a real restart on
  `2026-06-09T02:19Z` for both tracked Oracle lanes.

## Commands run

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
bash scripts/buy30854-lane-keep-alive.sh
sed -n '1,180p' systemd/paperclip-lane-keep-alive.timer
sed -n '1,180p' systemd/paperclip-lane-keep-alive.service
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs'
cat data/buy30854-keep-alive-state.json
rg -n 'DEAD — restarting|restarted pid=' logs/buy30854_keep_alive.log | tail -n 20
tail -n 12 logs/buy30854_keep_alive.log
```

## Results

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `data/buy30854-keep-alive-state.json` remained at zero consecutive-dead counts:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- Fresh watchdog tick from this heartbeat:

```text
===== keep-alive tick 2026-06-09T04:59:36Z =====
[2026-06-09T04:59:36Z] deep_page_loop OK pid=3907026
[2026-06-09T04:59:36Z] sustained_loop OK pid=3907215
[2026-06-09T04:59:36Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T04:59:36Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T04:59:36Z] keep-alive tick complete
```

- Latest real dead-lane restart evidence still present in the same live log:

```text
[2026-06-09T02:19:31Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T02:19:33Z] deep_page_loop restarted pid=3907026 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3907023
[2026-06-09T02:19:33Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T02:19:35Z] sustained_loop restarted pid=3907215 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3907212
```

## Disposition

`BUY-36970` can close `done`: this heartbeat executed the Oracle keep-alive
watchdog, verified the current 5-minute timer wiring, confirmed both active
Oracle lanes healthy with zero dead counts, and preserved live-log evidence that
the watchdog does restart dead lanes.
