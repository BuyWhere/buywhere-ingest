# BUY-37862 Vera sustained throughput keep-alive

Verified on `2026-06-09T12:31:06Z` for the `BUY-30854` 5-minute Oracle lane watchdog.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
pgrep -af "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs|buy30854-lane-keep-alive.sh"
bash scripts/buy30854-lane-keep-alive.sh
tail -n 40 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
```

## Findings

- `bash -n` passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning and no error for `paperclip-lane-keep-alive.service` or `.timer`.
- The timer still provides the intended 5-minute cadence through `OnUnitActiveSec=5min` with `Persistent=true`.
- The manual keep-alive tick appended a fresh run ending at `2026-06-09T12:30:40Z`.
- During that tick, `deep_page_loop` was detected dead and successfully restarted as pid `2776061`; `sustained_loop` remained healthy as pid `2775043`.
- `woocommerce_discover` remained intentionally skipped by `data/checkpoints/buy30590_woocommerce.completed`.
- `lane_supervisor` remained intentionally skipped by `data/buy30727-supervisor.stopped`.
- `data/buy30854-keep-alive-state.json` reset all tracked dead counters to zero after the successful relaunch.
- `data/buy30854-keep-alive-escalation.json` did not gain a new entry in this heartbeat; it still contains only historical `2026-06-08` deep-page escalations.

## Log excerpt

```text
===== keep-alive tick 2026-06-09T12:30:38Z =====
[2026-06-09T12:30:38Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T12:30:40Z] deep_page_loop restarted pid=2776061 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2776058
[2026-06-09T12:30:40Z] sustained_loop OK pid=2775043
[2026-06-09T12:30:40Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T12:30:40Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T12:30:40Z] keep-alive tick complete
```

## Conclusion

`BUY-37862` can close `done`: the 5-minute keep-alive watchdog is still configured correctly and, in this heartbeat, it proved the restart path by detecting and relaunching a dead `deep_page_loop` lane while leaving the tracked state healthy afterward.
