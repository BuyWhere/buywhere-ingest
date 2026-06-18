# BUY-38684 — Oracle lane keep-alive closeout (2026-06-09T19:39:08Z)

Issue scope: confirm `BUY-30854` still enforces the 5-minute Oracle lane keep-alive and still restarts dead Oracle lanes from the current workspace.

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy30854-lane-keep-alive.sh`
- `tail -n 80 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy30854_keep_alive.log`
- `cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30854-keep-alive-state.json`
- `ps -eo pid,lstart,etime,cmd | rg 'buy30331-sustained-loop\.mjs|buy30590-deep-page-loop\.mjs'`

## Findings

- `scripts/buy30854-lane-keep-alive.sh` still contains the detached dead-lane restart path, including the `exec 9>&-` lock-fd close before relaunch.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog as a `Type=oneshot` service from this checkout.
- `systemd/paperclip-lane-keep-alive.timer` still enforces `OnUnitActiveSec=5min` with `Persistent=true`.
- `bash -n` passed for the watchdog script.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning and no error for the lane keep-alive service or timer.
- A fresh manual watchdog run appended a new log block at `2026-06-09T19:38:42Z`:

```text
===== keep-alive tick 2026-06-09T19:38:42Z =====
[2026-06-09T19:38:42Z] deep_page_loop STOPPED (already absent)
[2026-06-09T19:38:42Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T19:38:42Z] sustained_loop OK pid=3782962
[2026-06-09T19:38:42Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T19:38:42Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T19:38:42Z] keep-alive tick complete
```

- The current state file remains reset for all tracked Oracle lanes:

```json
{
  "deep_page_loop": 0,
  "lane_supervisor": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0
}
```

- Live process inspection confirms `sustained_loop` is still running as PID `3782962`, started at `Tue Jun 9 17:21:36 2026 UTC`, with elapsed time `02:17:19` at capture.
- `deep_page_loop` is intentionally absent because `data/buy30590-deep-page-loop.stopped` remains present, so the watchdog correctly skipped restart instead of treating that lane as dead.
- `tail -n 40` on the escalation file showed no new entry for this heartbeat; the latest entry remains the historical `buy33243_custom_domain_supervisor` escalation at `2026-06-09T10:08:54Z`.

## Conclusion

`BUY-38684` can close `done`: the Oracle keep-alive watchdog still runs from the intended workspace on the intended 5-minute cadence, the dead-lane restart path remains present, and this heartbeat recorded a fresh successful watchdog tick with the live Oracle lane healthy and the intentional stop/completion markers respected.
