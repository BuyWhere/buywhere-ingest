# BUY-37035 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T05:29:40Z)

Issue scope: confirm the 5-minute Oracle lane keep-alive still restarts dead
Oracle lanes and is healthy in the current workspace.

## What was verified

- `scripts/buy30854-lane-keep-alive.sh` remains the active watchdog
  implementation for BUY-30854.
- `systemd/paperclip-lane-keep-alive.timer` still preserves the 5-minute cadence
  via `OnUnitActiveSec=5min`.
- `systemd/paperclip-lane-keep-alive.service` still executes the watchdog as a
  oneshot in the issue workspace.
- The live keep-alive log contains a real dead-lane recovery at
  `2026-06-09T05:26:32Z` followed by a clean succeeding tick at
  `2026-06-09T05:29:39Z`.

## Verification

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
cat data/buy30854-keep-alive-state.json
tail -n 20 logs/buy30854_keep_alive.log
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30727-lane-supervisor.mjs|buy30590-woocommerce-discover.mjs'
```

Observed results:

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; it reported no errors for the Oracle
  keep-alive service or timer.
- The manual watchdog tick completed cleanly and left
  `data/buy30854-keep-alive-state.json` at:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `pgrep` confirmed the live Oracle lane processes after the manual tick:

```text
375926 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
375929 node scripts/buy30590-deep-page-loop.mjs
3907212 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
3907215 node scripts/buy30331-sustained-loop.mjs
```

## Log evidence

Latest keep-alive log tail:

```text
===== keep-alive tick 2026-06-09T05:26:04Z =====
[2026-06-09T05:26:04Z] duplicate buy30590-deep-page-loop.mjs killed pid=3907026 (kept 374655)
[2026-06-09T05:26:04Z] deep_page_loop OK pid=374655
[2026-06-09T05:26:04Z] sustained_loop OK pid=3907215
[2026-06-09T05:26:04Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T05:26:04Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T05:26:04Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T05:26:32Z =====
[2026-06-09T05:26:32Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T05:26:34Z] deep_page_loop restarted pid=375929 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=375926
[2026-06-09T05:26:35Z] sustained_loop OK pid=3907215
[2026-06-09T05:26:35Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T05:26:35Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T05:26:35Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T05:29:39Z =====
[2026-06-09T05:29:40Z] deep_page_loop OK pid=375929
[2026-06-09T05:29:40Z] sustained_loop OK pid=3907215
[2026-06-09T05:29:40Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T05:29:40Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T05:29:40Z] keep-alive tick complete
```

## Conclusion

`BUY-37035` can close `done`: the Oracle keep-alive remains live, preserved the
5-minute restart path for dead lanes, and produced fresh on-host evidence of both
an actual restart and a clean follow-up recovery tick in this heartbeat.
