# BUY-36688 — Oracle lane keep-alive closeout (2026-06-09T02:19:57Z)

Wake scope: `BUY-30854` lane keep-alive, specifically the 5-minute restart path
for dead Oracle lanes.

## What this heartbeat verified

- `scripts/buy30854-lane-keep-alive.sh` still contains the watchdog restart
  paths for `deep_page_loop`, `sustained_loop`, optional
  `woocommerce_discover`, and `lane_supervisor`.
- `systemd/paperclip-lane-keep-alive.timer` still preserves the 5-minute
  cadence with `OnUnitActiveSec=5min`.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog as a
  oneshot from this checkout.

## Commands run

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `tail -n 40 logs/buy30854_keep_alive.log`
- `cat data/buy30854-keep-alive-state.json`
- `ps -eo pid,etime,args | grep -E "buy30590-deep-page-loop|buy30331-sustained-loop|buy30590-woocommerce-discover|buy30727-lane-supervisor" | grep -v grep`

## Result

The manual tick was a real recovery event, not just a clean no-op check.
`logs/buy30854_keep_alive.log` recorded:

```text
===== keep-alive tick 2026-06-09T02:19:31Z =====
[2026-06-09T02:19:31Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T02:19:33Z] deep_page_loop restarted pid=3907026 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3907023
[2026-06-09T02:19:33Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T02:19:35Z] sustained_loop restarted pid=3907215 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3907212
[2026-06-09T02:19:35Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T02:19:35Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T02:19:35Z] keep-alive tick complete
```

Post-run process table confirmed the restarted Oracle lanes alive:

```text
3907026 node scripts/buy30590-deep-page-loop.mjs
3907215 node scripts/buy30331-sustained-loop.mjs
```

`data/buy30854-keep-alive-state.json` now shows:

```json
{
  "deep_page_loop": 1,
  "sustained_loop": 1,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

That `1` state means this tick was the first dead observation before each
restart, so no new 4+-tick escalation was required.

## Disposition

`BUY-36688` can close `done`: the 5-minute Oracle keep-alive watchdog is still
wired correctly in this checkout and this heartbeat directly proved the dead-lane
restart path by recovering both tracked Oracle loops in the live workspace.
