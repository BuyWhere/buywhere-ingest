# BUY-37224 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T07:10:34Z)

Issue scope: verify in the current workspace that the Oracle lane keep-alive
still runs on a 5-minute cadence and still restarts a dead Oracle lane.

## What was verified

- `scripts/buy30854-lane-keep-alive.sh` remains the active watchdog.
- `systemd/paperclip-lane-keep-alive.timer` still uses
  `OnUnitActiveSec=5min`.
- `systemd/paperclip-lane-keep-alive.service` still launches the watchdog from
  this workspace as a `oneshot`.
- A forced runtime probe killed the live `deep_page_loop` node process, then a
  watchdog tick restarted it and the following tick reset its dead-count state
  back to `0`.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
kill <deep_page_loop node pid>
bash scripts/buy30854-lane-keep-alive.sh
bash scripts/buy30854-lane-keep-alive.sh
cat data/buy30854-keep-alive-state.json
pgrep -af "buy30590-deep-page-loop\\.mjs|buy30331-sustained-loop\\.mjs"
tail -n 12 logs/buy30854_keep_alive.log
```

## Results

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify ...` reported the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`, but no errors for
  `paperclip-lane-keep-alive.service` or `.timer`.
- A healthy pre-probe tick completed at `2026-06-09T07:09:54Z` with
  `deep_page_loop OK pid=375929` and `sustained_loop OK pid=670904`.
- After killing the live `deep_page_loop` node PID `375929`, the watchdog
  logged:

```text
===== keep-alive tick 2026-06-09T07:10:16Z =====
[2026-06-09T07:10:16Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T07:10:18Z] deep_page_loop restarted pid=748760 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=748757
[2026-06-09T07:10:18Z] sustained_loop OK pid=670904
[2026-06-09T07:10:18Z] keep-alive tick complete
```

- The follow-up tick at `2026-06-09T07:10:34Z` confirmed the relaunched lane was
  healthy again:

```text
[2026-06-09T07:10:34Z] deep_page_loop OK pid=748760
[2026-06-09T07:10:34Z] sustained_loop OK pid=670904
```

- `data/buy30854-keep-alive-state.json` finished fully reset:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `pgrep -af` after recovery showed both live Oracle lanes under the keep-alive
  launcher:

```text
670901 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
670904 node scripts/buy30331-sustained-loop.mjs
748757 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
748760 node scripts/buy30590-deep-page-loop.mjs
```

## Disposition

`BUY-37224` can close `done`: the Oracle keep-alive remains wired to a
5-minute systemd timer, a real dead-lane event in this heartbeat triggered the
expected restart path, and the next tick returned the lane-health state to
steady-state `0`.
