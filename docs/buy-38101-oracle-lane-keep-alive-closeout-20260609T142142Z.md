# BUY-38101 — Oracle lane keep-alive closeout (2026-06-09T14:21:42Z)

Issue scope: confirm the `BUY-30854` Oracle lane keep-alive still restarts dead Oracle lanes on the 5-minute watchdog cadence and leave durable proof from this heartbeat.

## What was verified

- `scripts/buy30854-lane-keep-alive.sh` still contains the dead-lane restart path, including the `exec 9>&-` lock-fd close before detached relaunch at lines 245-257.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog as a `Type=oneshot` service from this workspace.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the 5-minute cadence with `OnUnitActiveSec=5min` and `Persistent=true`.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 60 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
tail -n 80 data/buy30854-keep-alive-escalation.json
```

## Results

- `bash -n` passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning and no error for the lane keep-alive unit or timer.
- The watchdog log captured fresh live restart proof during this heartbeat:
  - `2026-06-09T14:12:22Z` `sustained_loop DEAD — restarting (consecutive_dead_ticks=1)`
  - `2026-06-09T14:12:24Z` `sustained_loop restarted pid=3131982 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3131979`
- The following ticks showed the lane recovered and healthy:
  - `2026-06-09T14:13:04Z` `sustained_loop OK pid=3131982`
  - `2026-06-09T14:16:36Z` `sustained_loop OK pid=3131982`
  - `2026-06-09T14:20:15Z` `sustained_loop OK pid=3131982`
- `deep_page_loop` remained intentionally stopped because `data/buy30590-deep-page-loop.stopped` is present, while `woocommerce_discover` and `lane_supervisor` remained intentionally skipped by their completion/stop markers.
- `data/buy30854-keep-alive-state.json` now shows all tracked lane dead counts reset to zero:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `data/buy30854-keep-alive-escalation.json` gained no new escalation entry in this heartbeat.

## Conclusion

`BUY-38101` can close `done`: the Oracle keep-alive watchdog still runs on the intended 5-minute cadence, it retained the dead-lane restart path, and this heartbeat captured a fresh successful restart and recovery of `sustained_loop`.
