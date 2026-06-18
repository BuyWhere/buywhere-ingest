# BUY-37400 — Vera sustained throughput keep-alive (2026-06-09T08:36:49Z)

Routine execution issue for the 5-minute [BUY-30854](/BUY/issues/BUY-30854)
watchdog that keeps the sustained throughput Oracle lanes alive.

## What ran

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `tail -n 12 logs/buy30854_keep_alive.log`
- `sed -n '1,220p' data/buy30854-keep-alive-state.json`
- `ps -eo pid,lstart,cmd | rg 'buy30331-sustained-loop.mjs|buy30590-deep-page-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs'`
- `curl -I -sS --max-time 10 https://paperclip.richteo.com`

## Results

- Shell syntax check passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` only reported the pre-existing unrelated warning on
  `/etc/systemd/system/hindsight.service`; the keep-alive service and timer
  units themselves still verified cleanly.
- Manual watchdog invocation completed and appended a fresh healthy tick at
  `2026-06-09T08:36:38Z`.
- `deep_page_loop` remained live as PID `748760`.
- `sustained_loop` remained live as PID `670904`.
- `woocommerce_discover` was intentionally skipped because
  `data/checkpoints/buy30590_woocommerce.completed` is present.
- `lane_supervisor` was intentionally skipped because
  `data/buy30727-supervisor.stopped` is present for [BUY-31452](/BUY/issues/BUY-31452).
- `data/buy30854-keep-alive-state.json` remained all zeroes, so there were no
  consecutive-dead counters or new escalations on this tick.
- Direct Paperclip control-plane sync is still blocked in this workspace because
  `curl` to `https://paperclip.richteo.com` failed with `Could not resolve host`.

## Evidence

Latest keep-alive log block from `logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-09T08:34:39Z =====
[2026-06-09T08:34:39Z] deep_page_loop OK pid=748760
[2026-06-09T08:34:40Z] sustained_loop OK pid=670904
[2026-06-09T08:34:40Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T08:34:40Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T08:34:40Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T08:36:38Z =====
[2026-06-09T08:36:38Z] deep_page_loop OK pid=748760
[2026-06-09T08:36:38Z] sustained_loop OK pid=670904
[2026-06-09T08:36:38Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T08:36:38Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T08:36:38Z] keep-alive tick complete
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
 670904 Tue Jun  9 06:49:26 2026 node scripts/buy30331-sustained-loop.mjs
 748760 Tue Jun  9 07:10:16 2026 node scripts/buy30590-deep-page-loop.mjs
```

Control-plane reachability check:

```text
curl: (6) Could not resolve host: paperclip.richteo.com
```

## Disposition

`BUY-37400` is ready to close `done` once the control plane is reachable again.
The requested watchdog work is complete and verified locally; only the Paperclip
status/comment sync is blocked by the current DNS failure.
