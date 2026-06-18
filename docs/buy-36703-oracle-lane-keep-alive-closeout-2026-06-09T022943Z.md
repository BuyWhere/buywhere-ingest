# BUY-36703 — Oracle lane keep-alive closeout (2026-06-09T02:29:43Z)

Wake scope: `BUY-30854` lane keep-alive, specifically the 5-minute restart path
for dead Oracle lanes.

## What this heartbeat verified

- `scripts/buy30854-lane-keep-alive.sh` still implements restart checks for the
  Oracle `deep_page_loop` and `sustained_loop` lanes.
- `systemd/paperclip-lane-keep-alive.timer` still preserves the intended
  5-minute cadence with `OnUnitActiveSec=5min`.
- The live runtime produced a real dead-lane recovery immediately before this
  closeout, and the following tick showed both Oracle lanes healthy again.

## Commands run

- `sed -n '1,220p' scripts/buy30854-lane-keep-alive.sh`
- `sed -n '1,200p' systemd/paperclip-lane-keep-alive.timer`
- `pgrep -af "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs|buy30854-lane-keep-alive.sh"`
- `tail -n 80 logs/buy30854_keep_alive.log`
- `cat data/buy30854-keep-alive-state.json`

## Result

`logs/buy30854_keep_alive.log` shows a successful live recovery:

```text
===== keep-alive tick 2026-06-09T02:19:31Z =====
[2026-06-09T02:19:31Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T02:19:33Z] deep_page_loop restarted pid=3907026 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3907023
[2026-06-09T02:19:33Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T02:19:35Z] sustained_loop restarted pid=3907215 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3907212
[2026-06-09T02:19:35Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T02:24:39Z =====
[2026-06-09T02:24:39Z] deep_page_loop OK pid=3907026
[2026-06-09T02:24:39Z] sustained_loop OK pid=3907215
[2026-06-09T02:24:39Z] keep-alive tick complete
```

Current process state matches that recovery:

```text
3907026 node scripts/buy30590-deep-page-loop.mjs
3907215 node scripts/buy30331-sustained-loop.mjs
```

`data/buy30854-keep-alive-state.json` is reset back to healthy zero counts:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Disposition

`BUY-36703` can close `done`: this heartbeat confirmed the Oracle watchdog is
still wired to a 5-minute cadence and directly observed it restart both dead
Oracle lanes, then verify them healthy on the next tick.
