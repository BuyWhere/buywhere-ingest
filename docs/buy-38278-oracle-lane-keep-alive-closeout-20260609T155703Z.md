## BUY-38278 closeout

Verified the Oracle lane keep-alive implementation currently present in the
workspace for [BUY-30854](/BUY/issues/BUY-30854) and confirmed the 5-minute
dead-lane restart watchdog remains healthy on June 9, 2026.

### What changed in the checked-out worktree

- `scripts/buy30854-lane-keep-alive.sh` is no longer the original one-shot
  `pgrep` wrapper. The current implementation adds:
  - non-blocking `flock` locking via `data/buy30854-keep-alive.lock`
  - per-lane consecutive-dead counters in
    `data/buy30854-keep-alive-state.json`
  - escalation persistence in `data/buy30854-keep-alive-escalation.json`
  - stop-marker handling for intentionally stopped lanes
  - lane-root discovery before relaunch
  - detached restarts that explicitly close FD 9 before spawning the child
- `systemd/paperclip-lane-keep-alive.service` is `Type=oneshot` and runs the
  watchdog script from this workspace.
- `systemd/paperclip-lane-keep-alive.timer` enforces the intended cadence with:
  - `OnBootSec=1min`
  - `OnUnitActiveSec=5min`
  - `Persistent=true`

### Verification run

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 16 logs/buy30854_keep_alive.log
sed -n '1,120p' data/buy30854-keep-alive-state.json
stat -c '%y %n' data/buy30590-deep-page-loop.stopped data/checkpoints/buy30590_woocommerce.completed data/buy30727-supervisor.stopped
```

Results:

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated host warning:
  `/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.`
- A fresh manual watchdog tick completed at `2026-06-09T15:57:03Z`.
- Latest keep-alive log block:

```text
===== keep-alive tick 2026-06-09T15:57:03Z =====
[2026-06-09T15:57:03Z] deep_page_loop STOPPED (already absent)
[2026-06-09T15:57:03Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T15:57:03Z] sustained_loop OK pid=3131982
[2026-06-09T15:57:03Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T15:57:03Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T15:57:03Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` remained fully reset:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- Intentional skip markers were present and current:
  - `data/buy30590-deep-page-loop.stopped` last updated `2026-06-09 12:32:23 +0000`
  - `data/checkpoints/buy30590_woocommerce.completed` last updated `2026-06-06 02:26:34 +0000`
  - `data/buy30727-supervisor.stopped` last updated `2026-06-05 20:44:24 +0000`

### Conclusion

`BUY-38278` can close `done`: the checked-out Oracle watchdog implementation
does provide the 5-minute restart path for dead lanes, current verification
passed, and the active runtime behaved correctly by keeping the live sustained
lane up while intentionally skipped lanes remained suppressed by their markers.
