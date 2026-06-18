# BUY-38436 — Vera sustained throughput keep-alive closeout (2026-06-09T17:14:50Z)

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
ps -eo pid,ppid,pgid,sid,etimes,cmd | rg 'buy30331-sustained-loop|buy30590-deep-page-loop|buy30727-lane-supervisor|buy30590-woocommerce-discover'
sed -n '1,160p' systemd/paperclip-lane-keep-alive.timer
```

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
  reported only the known unrelated `/etc/systemd/system/hindsight.service`
  warning about `StartLimitIntervalSec`; there were no errors for the Oracle
  keep-alive service or timer.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the watchdog cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- `bash scripts/buy30854-lane-keep-alive.sh` completed successfully and wrote a
  fresh keep-alive block ending at `2026-06-09T17:14:51Z`.

Fresh log proof:

```text
===== keep-alive tick 2026-06-09T17:14:50Z =====
[2026-06-09T17:14:50Z] deep_page_loop STOPPED (already absent)
[2026-06-09T17:14:50Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T17:14:50Z] sustained_loop OK pid=3578415
[2026-06-09T17:14:51Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T17:14:51Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T17:14:51Z] keep-alive tick complete
```

The shared log also shows the timer-driven tick immediately before the manual
run:

```text
===== keep-alive tick 2026-06-09T17:11:44Z =====
[2026-06-09T17:11:44Z] deep_page_loop STOPPED (already absent)
[2026-06-09T17:11:44Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T17:11:44Z] sustained_loop OK pid=3578415
[2026-06-09T17:11:44Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T17:11:44Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T17:11:44Z] keep-alive tick complete
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
3578412       1 3578412 3578412    3142 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
3578415 3578412 3578412 3578412    3142 node scripts/buy30331-sustained-loop.mjs
```

The escalation file gained no new entry in this heartbeat; its tail still
contains only the historical `deep_page_loop` escalations from 2026-06-08,
before that lane was intentionally stop-marked.

## Conclusion

`BUY-38436` can close `done`: the Oracle keep-alive watchdog is still active,
the systemd timer still enforces the 5-minute cadence, the dead-lane restart
path remains present in `scripts/buy30854-lane-keep-alive.sh`, and this
heartbeat recorded a fresh successful keep-alive run with all tracked
dead-count state reset to zero.
