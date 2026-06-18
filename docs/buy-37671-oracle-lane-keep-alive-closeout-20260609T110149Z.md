# BUY-37671 — Oracle lane keep-alive closeout (2026-06-09T11:01:49Z)

Issue scope: execute the `BUY-30854` 5-minute Oracle lane keep-alive watchdog in
the current workspace, verify the dead-lane restart path remains live, and leave
fresh runtime evidence for the Oracle lane fleet.

## What I verified

- `scripts/buy30854-lane-keep-alive.sh` is still the active watchdog and keeps
  the dead-lane restart path for `deep_page_loop`, `sustained_loop`,
  `woocommerce_discover`, and `lane_supervisor`.
- `systemd/paperclip-lane-keep-alive.timer` still defines a 5-minute cadence via
  `OnUnitActiveSec=5min` with `Persistent=true`.
- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
  reported only the known unrelated `/etc/systemd/system/hindsight.service`
  warning and no watchdog unit or timer errors.
- A fresh manual watchdog tick completed at `2026-06-09T11:01:41Z`.

## Current live results

- The keep-alive log at `logs/buy30854_keep_alive.log` shows the fresh tick:

```text
===== keep-alive tick 2026-06-09T11:01:40Z =====
[2026-06-09T11:01:40Z] deep_page_loop OK pid=2138816
[2026-06-09T11:01:41Z] sustained_loop OK pid=2139271
[2026-06-09T11:01:41Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T11:01:41Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T11:01:41Z] keep-alive tick complete
```

- `pgrep -af` after the manual tick confirmed the active Oracle lane processes:

```text
2138813 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
2138816 node scripts/buy30590-deep-page-loop.mjs
2139268 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
2139271 node scripts/buy30331-sustained-loop.mjs
```

- `data/buy30854-keep-alive-state.json` reset all tracked counters to zero:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Restart-path evidence

- The same live log shows the restart path firing during this operating window:

```text
===== keep-alive tick 2026-06-09T10:09:25Z =====
[2026-06-09T10:09:25Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:09:27Z] deep_page_loop restarted pid=2119031 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2119028
[2026-06-09T10:09:27Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:09:29Z] sustained_loop restarted pid=2119205 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2119202
```

- Follow-up ticks stabilized those lanes, and by `2026-06-09T10:13:31Z` both
  lanes were healthy again with dead counts reset back to zero.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
pgrep -af "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs"
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
```

`BUY-37671` can close `done`: the 5-minute watchdog is still wired, the restart
path demonstrably fired on `2026-06-09T10:09:25Z` and recovered the dead lanes,
and a fresh manual tick at `2026-06-09T11:01:41Z` confirmed the Oracle lanes are
currently healthy.
