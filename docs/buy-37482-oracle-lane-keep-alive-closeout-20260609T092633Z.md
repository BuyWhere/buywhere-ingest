# BUY-37482 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T09:26:33Z)

Issue scope: confirm the `BUY-30854` 5-minute Oracle lane keep-alive still
restarts dead Oracle lanes in the current workspace and leave fresh proof in
this heartbeat.

## Current implementation

- `scripts/buy30854-lane-keep-alive.sh` is still the active watchdog.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the watchdog cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog as a
  oneshot unit from this workspace via `ExecStart=/bin/bash
  scripts/buy30854-lane-keep-alive.sh`.

## Fresh runtime verification

Manual run from this heartbeat:

```bash
bash scripts/buy30854-lane-keep-alive.sh
```

Latest successful tick from `logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-09T09:26:22Z =====
[2026-06-09T09:26:22Z] deep_page_loop OK pid=748760
[2026-06-09T09:26:22Z] sustained_loop OK pid=670904
[2026-06-09T09:26:22Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T09:26:22Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T09:26:22Z] keep-alive tick complete
```

Live process table immediately after the tick:

```text
deep_page_loop: 748760 node scripts/buy30590-deep-page-loop.mjs
sustained_loop: 670904 node scripts/buy30331-sustained-loop.mjs
```

State file after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Proof that the restart path fired

Recent watchdog log entries show real dead-lane recovery:

```text
[2026-06-09T02:19:31Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T02:19:33Z] deep_page_loop restarted pid=3907026
[2026-06-09T02:19:33Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T02:19:35Z] sustained_loop restarted pid=3907215
[2026-06-09T07:10:16Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T07:10:18Z] deep_page_loop restarted pid=748760
```

This is direct evidence that the 5-minute watchdog is not just configured; it
has recently detected dead Oracle lanes and relaunched them.

## Unit verification

Command:

```bash
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
```

Result:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

The only output was the known unrelated `hindsight.service` warning. No errors
were reported for the lane keep-alive unit or timer.

## Conclusion

`BUY-30854` remains implemented and live in this workspace. The Oracle lane
watchdog still runs on a 5-minute cadence, successfully completed a fresh manual
tick in this heartbeat, and the log proves it has recently restarted dead
Oracle lanes.
