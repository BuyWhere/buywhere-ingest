# BUY-37594 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T10:21:35Z)

Issue scope: verify that the BUY-30854 Oracle lane keep-alive still runs on a
5-minute cadence and still restarts dead Oracle lanes.

## What was verified

- `scripts/buy30854-lane-keep-alive.sh` remains the active watchdog and still
  contains the `restart_if_dead` path for `deep_page_loop`, `sustained_loop`,
  optional `woocommerce_discover`, and `lane_supervisor`.
- `systemd/paperclip-lane-keep-alive.timer` still defines the watchdog cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- `systemd/paperclip-lane-keep-alive.service` still executes
  `scripts/buy30854-lane-keep-alive.sh` as the watchdog entrypoint.
- `data/buy30854-keep-alive-state.json` ended this heartbeat with all tracked
  dead counters reset to `0`.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
tail -n 80 logs/buy30854_keep_alive.log
pgrep -af "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs"
```

## Evidence

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; it did not report an error for the
  lane keep-alive unit or timer.
- The keep-alive log shows live restart events during this heartbeat:

```text
===== keep-alive tick 2026-06-09T10:09:25Z =====
[2026-06-09T10:09:25Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:09:27Z] deep_page_loop restarted pid=2119031 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2119028
[2026-06-09T10:09:27Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:09:29Z] sustained_loop restarted pid=2119205 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2119202
...
===== keep-alive tick 2026-06-09T10:12:57Z =====
[2026-06-09T10:12:57Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=2)
[2026-06-09T10:12:59Z] deep_page_loop restarted pid=2138816 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2138813
[2026-06-09T10:12:59Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=2)
[2026-06-09T10:13:01Z] sustained_loop restarted pid=2139271 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2139268
```

- Later ticks in the same log show both lanes recovered cleanly:

```text
===== keep-alive tick 2026-06-09T10:18:48Z =====
[2026-06-09T10:18:48Z] deep_page_loop OK pid=2138816
[2026-06-09T10:18:48Z] sustained_loop OK pid=2139271
[2026-06-09T10:18:48Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T10:18:48Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T10:18:48Z] keep-alive tick complete
```

- Live processes at closeout:

```text
2138813 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
2138816 node scripts/buy30590-deep-page-loop.mjs
2139268 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
2139271 node scripts/buy30331-sustained-loop.mjs
```

## Conclusion

`BUY-37594` can close `done`. The Oracle keep-alive remains active on the
5-minute timer, and this heartbeat captured real dead-lane restart behavior plus
subsequent healthy ticks in the live workspace.
