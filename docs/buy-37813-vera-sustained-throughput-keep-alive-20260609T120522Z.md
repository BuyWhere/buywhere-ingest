# BUY-37813 — Vera sustained throughput keep-alive (2026-06-09T12:05:22Z)

Routine execution issue for the 5-minute [BUY-30854](/BUY/issues/BUY-30854)
watchdog that keeps the sustained-throughput Oracle lanes alive.

## What ran

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `tail -n 18 logs/buy30854_keep_alive.log`
- `sed -n '1,120p' data/buy30854-keep-alive-state.json`
- `pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs'`
- `ps -eo pid,lstart,cmd | rg 'node scripts/(buy30331-sustained-loop|buy30590-deep-page-loop)\\.mjs'`
- `curl -sfS -H "Authorization: Bearer $PAPERCLIP_API_KEY" "$PAPERCLIP_API_URL/api/issues/$PAPERCLIP_TASK_ID/heartbeat-context"`

## Results

- Shell syntax check passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` only reported the pre-existing unrelated warning on
  `/etc/systemd/system/hindsight.service`; the keep-alive service and timer
  units themselves still verified.
- Manual watchdog invocation completed successfully and appended a fresh healthy
  tick at `2026-06-09T12:04:55Z`.
- `deep_page_loop` remained live as PID `2138816`.
- `sustained_loop` remained live as PID `2139271`.
- `woocommerce_discover` was intentionally skipped because
  `data/checkpoints/buy30590_woocommerce.completed` is present.
- `lane_supervisor` was intentionally skipped because
  `data/buy30727-supervisor.stopped` is present for [BUY-31452](/BUY/issues/BUY-31452).
- `data/buy30854-keep-alive-state.json` remained all zeroes, so there were no
  consecutive-dead counters or new escalations on this tick.
- Paperclip `heartbeat-context` read succeeded during this heartbeat.

## Evidence

Latest keep-alive log block from `logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-09T11:56:29Z =====
[2026-06-09T11:56:29Z] deep_page_loop OK pid=2138816
[2026-06-09T11:56:29Z] sustained_loop OK pid=2139271
[2026-06-09T11:56:29Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T11:56:30Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T11:56:30Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T11:58:17Z =====
[2026-06-09T11:58:17Z] deep_page_loop OK pid=2138816
[2026-06-09T11:58:17Z] sustained_loop OK pid=2139271
[2026-06-09T11:58:17Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T11:58:17Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T11:58:17Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T12:04:55Z =====
[2026-06-09T12:04:55Z] deep_page_loop OK pid=2138816
[2026-06-09T12:04:55Z] sustained_loop OK pid=2139271
[2026-06-09T12:04:55Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T12:04:55Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T12:04:55Z] keep-alive tick complete
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
2138813 Tue Jun  9 10:12:56 2026 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
2138816 Tue Jun  9 10:12:56 2026 node scripts/buy30590-deep-page-loop.mjs
2139268 Tue Jun  9 10:12:58 2026 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
2139271 Tue Jun  9 10:12:58 2026 node scripts/buy30331-sustained-loop.mjs
```

Unit verification output:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

## Disposition

`BUY-37813` can close `done`. This heartbeat executed the 5-minute keep-alive
watchdog successfully, confirmed the sustained-throughput lanes are still live,
and recorded the expected skip markers for the completed and stopped side
lanes.
