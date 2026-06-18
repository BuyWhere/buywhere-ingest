# BUY-38333 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T16:22:43Z)

This execution issue verified the Oracle 5-minute lane keep-alive watchdog in the
active workspace and captured fresh live restart proof for a dead lane.

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `kill 3131982`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `ps -eo pid,etime,cmd | grep -E 'buy30331-sustained-loop.mjs' | grep -v grep`
- `cat data/buy30854-keep-alive-state.json`
- `tail -n 20 logs/buy30854_keep_alive.log`

## Results

- `scripts/buy30854-lane-keep-alive.sh` remains syntactically valid.
- `systemd/paperclip-lane-keep-alive.service` is still a `Type=oneshot` watchdog
  and `systemd/paperclip-lane-keep-alive.timer` still enforces the 5-minute
  cadence with `Persistent=true`.
- `systemd-analyze verify` reported only the known unrelated
  `/etc/systemd/system/hindsight.service` warning and no Oracle keep-alive unit
  or timer errors.
- A controlled failure test provided fresh restart proof: after killing
  `sustained_loop` pid `3131982`, the next watchdog tick detected it dead at
  `2026-06-09T16:22:41Z` and relaunched it as pid `3578415` from the active
  Oracle workspace at `2026-06-09T16:22:43Z`.
- `deep_page_loop` remained intentionally absent because
  `data/buy30590-deep-page-loop.stopped` is present.
- `woocommerce_discover` remained intentionally skipped because
  `data/checkpoints/buy30590_woocommerce.completed` is present.
- `lane_supervisor` remained intentionally skipped because
  `data/buy30727-supervisor.stopped` is present.
- `data/buy30854-keep-alive-state.json` reset all tracked dead counters to `0`
  after the successful restart, and `data/buy30854-keep-alive-escalation.json`
  did not gain a new entry in this heartbeat.

## Evidence

Recent keep-alive log tail:

```text
===== keep-alive tick 2026-06-09T16:21:48Z =====
[2026-06-09T16:21:48Z] deep_page_loop STOPPED (already absent)
[2026-06-09T16:21:48Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T16:21:48Z] sustained_loop OK pid=3131982
[2026-06-09T16:21:49Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T16:21:49Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T16:21:49Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T16:22:41Z =====
[2026-06-09T16:22:41Z] deep_page_loop STOPPED (already absent)
[2026-06-09T16:22:41Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T16:22:41Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T16:22:43Z] sustained_loop restarted pid=3578415 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3578412
[2026-06-09T16:22:43Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T16:22:43Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T16:22:43Z] keep-alive tick complete
```

Tracked lane state after the restart tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```
