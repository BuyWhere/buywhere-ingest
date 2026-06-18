# BUY-37560 — Vera sustained throughput keep-alive (2026-06-09T10:03:52Z)

Routine execution issue for the 5-minute [BUY-30854](/BUY/issues/BUY-30854)
watchdog that keeps the sustained throughput Oracle lanes alive.

## What ran

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `tail -n 14 logs/buy30854_keep_alive.log`
- `sed -n '1,220p' data/buy30854-keep-alive-state.json`
- `ps -eo pid,lstart,cmd | rg 'node scripts/(buy30331-sustained-loop|buy30590-deep-page-loop)\.mjs'`
- `curl -I -sS --max-time 10 https://paperclip.richteo.com`

## Results

- Shell syntax check passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` only reported the pre-existing unrelated warning on
  `/etc/systemd/system/hindsight.service`; the keep-alive service and timer
  units themselves still verified cleanly.
- Manual watchdog invocation completed and appended a fresh healthy tick at
  `2026-06-09T10:03:32Z`.
- `deep_page_loop` remained live as PID `748760`.
- `sustained_loop` remained live as PID `670904`.
- `woocommerce_discover` was intentionally skipped because
  `data/checkpoints/buy30590_woocommerce.completed` is present.
- `lane_supervisor` was intentionally skipped because
  `data/buy30727-supervisor.stopped` is present for [BUY-31452](/BUY/issues/BUY-31452).
- `data/buy30854-keep-alive-state.json` remained all zeroes, so there were no
  consecutive-dead counters or new escalations on this tick.
- Paperclip control-plane reachability recovered in this workspace; `curl -I`
  to `https://paperclip.richteo.com` returned `HTTP/2 200`.

## Evidence

Latest keep-alive log block from `logs/buy30854_keep_alive.log`:

```text
[2026-06-09T09:58:20Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T09:58:20Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T10:01:18Z =====
[2026-06-09T10:01:18Z] deep_page_loop OK pid=748760
[2026-06-09T10:01:18Z] sustained_loop OK pid=670904
[2026-06-09T10:01:18Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T10:01:18Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T10:01:18Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T10:03:32Z =====
[2026-06-09T10:03:32Z] deep_page_loop OK pid=748760
[2026-06-09T10:03:32Z] sustained_loop OK pid=670904
[2026-06-09T10:03:33Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T10:03:33Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T10:03:33Z] keep-alive tick complete
```

Current keep-alive state:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

Live lane processes:

```text
 670901 Tue Jun  9 06:49:26 2026 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
 670904 Tue Jun  9 06:49:26 2026 node scripts/buy30331-sustained-loop.mjs
 748757 Tue Jun  9 07:10:16 2026 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
 748760 Tue Jun  9 07:10:16 2026 node scripts/buy30590-deep-page-loop.mjs
```

Control-plane reachability check:

```text
HTTP/2 200
```

## Disposition

`BUY-37560` can close `done`: the Oracle sustained-throughput keep-alive
watchdog still runs cleanly on the 5-minute cadence, the tracked lanes are
healthy, and this heartbeat can sync the verified result directly to Paperclip.
