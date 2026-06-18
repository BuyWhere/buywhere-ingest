# BUY-37636 — Vera sustained throughput keep-alive (2026-06-09T10:43:46Z)

Routine execution issue for the 5-minute [BUY-30854](/BUY/issues/BUY-30854)
watchdog that keeps the sustained-throughput Oracle lanes alive.

## What ran

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `tail -n 8 logs/buy30854_keep_alive.log`
- `sed -n '1,120p' data/buy30854-keep-alive-state.json`
- `pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs'`
- `ps -ef | grep -E 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs' | grep -v grep`
- `test -f data/checkpoints/buy30590_woocommerce.completed && echo completed_marker_present`
- `test -f data/buy30727-supervisor.stopped && echo supervisor_stop_marker_present`

## Results

- Shell syntax check passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` only reported the pre-existing unrelated warning on
  `/etc/systemd/system/hindsight.service`; the keep-alive service/timer units
  themselves still verified.
- Manual watchdog invocation completed successfully.
- The explicit tick at `2026-06-09T10:43:23Z` finished cleanly with both active
  lanes healthy.
- `deep_page_loop` was live as PID `2138816`.
- `sustained_loop` was live as PID `2139271`.
- `woocommerce_discover` remained intentionally skipped because
  `data/checkpoints/buy30590_woocommerce.completed` is present.
- `lane_supervisor` remained intentionally skipped because
  `data/buy30727-supervisor.stopped` is present for BUY-31452.
- `data/buy30854-keep-alive-state.json` remained all zeroes, so there were no
  consecutive-dead counters or new escalations on this tick.

## Evidence

Latest keep-alive log block from `logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-09T10:43:23Z =====
[2026-06-09T10:43:23Z] deep_page_loop OK pid=2138816
[2026-06-09T10:43:24Z] sustained_loop OK pid=2139271
[2026-06-09T10:43:24Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T10:43:24Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T10:43:24Z] keep-alive tick complete
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
2138813 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
2138816 node scripts/buy30590-deep-page-loop.mjs
2139268 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
2139271 node scripts/buy30331-sustained-loop.mjs
```

Process table snapshot:

```text
papercl+ 2138813       1  0 10:12 ?        00:00:00 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
papercl+ 2138816 2138813  3 10:12 ?        00:00:57 node scripts/buy30590-deep-page-loop.mjs
papercl+ 2139268       1  0 10:12 ?        00:00:00 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
papercl+ 2139271 2139268  4 10:12 ?        00:01:22 node scripts/buy30331-sustained-loop.mjs
```

Skip markers:

```text
completed_marker_present
supervisor_stop_marker_present
```

## Disposition

`BUY-37636` can close `done`. This heartbeat executed the 5-minute keep-alive
watchdog successfully, confirmed the sustained-throughput lanes are still live,
and preserved the expected skip markers for the completed/stopped side lanes.
