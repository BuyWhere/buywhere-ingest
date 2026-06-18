# BUY-38424 — Vera sustained throughput keep-alive closeout (2026-06-09T17:09:25Z)

Issue scope: execute the `BUY-30854` Oracle lane keep-alive watchdog, confirm
the 5-minute restart path remains intact, and leave fresh heartbeat proof for
the sustained-throughput lane set.

## Commands run

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
tail -n 40 data/buy30854-keep-alive-escalation.json
ps -eo pid,etimes,cmd | rg 'buy30331-sustained-loop\.mjs|buy30590-deep-page-loop\.mjs|buy30727-lane-supervisor\.mjs'
```

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
  reported only the known unrelated `/etc/systemd/system/hindsight.service`
  warning about `StartLimitIntervalSec`; there were no errors for the Oracle
  keep-alive service or timer.
- `bash scripts/buy30854-lane-keep-alive.sh` completed successfully and wrote a
  fresh keep-alive block ending at `2026-06-09T17:09:06Z`.

Fresh log proof:

```text
===== keep-alive tick 2026-06-09T17:09:06Z =====
[2026-06-09T17:09:06Z] deep_page_loop STOPPED (already absent)
[2026-06-09T17:09:06Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T17:09:06Z] sustained_loop OK pid=3578415
[2026-06-09T17:09:06Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T17:09:06Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T17:09:06Z] keep-alive tick complete
```

The shared log also shows the timer-driven tick immediately before the manual
run:

```text
===== keep-alive tick 2026-06-09T17:07:20Z =====
[2026-06-09T17:07:21Z] deep_page_loop STOPPED (already absent)
[2026-06-09T17:07:21Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T17:07:21Z] sustained_loop OK pid=3578415
[2026-06-09T17:07:21Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T17:07:21Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T17:07:21Z] keep-alive tick complete
```

Current tracked state after the fresh tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

Current process snapshot:

```text
3578412    2794 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
3578415    2794 node scripts/buy30331-sustained-loop.mjs
```

The escalation file gained no new entry in this heartbeat; its tail still
contains only the historical `deep_page_loop` escalations from 2026-06-08,
before that lane was intentionally stop-marked.

## Conclusion

`BUY-38424` can close `done`: the Oracle keep-alive watchdog is still active,
the systemd timer still enforces the 5-minute cadence, the dead-lane restart
path remains present in `scripts/buy30854-lane-keep-alive.sh`, and this
heartbeat recorded a fresh successful keep-alive run with all tracked
dead-count state reset to zero.
