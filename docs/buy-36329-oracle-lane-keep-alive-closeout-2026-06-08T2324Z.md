# BUY-36329 — BUY-30854 Oracle lane keep-alive closeout (2026-06-08T23:24Z)

Issue scope: confirm the Oracle lane keep-alive now performs the intended
5-minute restart/watchdog role for dead lanes and that the current checkout
contains the deployment wiring needed to run it durably.

## Code path present in this checkout

- `scripts/buy30854-lane-keep-alive.sh` now implements the lane watchdog with:
  - dead-tick state in `data/buy30854-keep-alive-state.json`
  - escalation logging in `data/buy30854-keep-alive-escalation.json`
  - duplicate-process pruning via `pgrep_pat`
  - detached restarts that explicitly close FD 9 before launching a lane:

```bash
nohup setsid bash -lc "exec 9>&-; $cmd & wait" >> "$logfile" 2>&1 < /dev/null &
```

That lock-release step prevents restarted lanes from inheriting
`data/buy30854-keep-alive.lock` and pinning later watchdog ticks.

- `systemd/paperclip-lane-keep-alive.service` is a `Type=oneshot` unit that
  runs `scripts/buy30854-lane-keep-alive.sh`.
- `systemd/paperclip-lane-keep-alive.timer` sets the 5-minute cadence with:

```ini
OnBootSec=1min
OnUnitActiveSec=5min
Persistent=true
```

- `scripts/deploy-systemd-units.sh` now installs both
  `paperclip-lane-keep-alive.service` and `paperclip-lane-keep-alive.timer`.

## Verification run

Commands run in this workspace:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
```

Results:

- `bash -n` passed.
- `systemd-analyze verify` reported no Oracle keep-alive unit errors. The only
  warning remained the unrelated host unit warning:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

- The manual watchdog tick appended a fresh healthy block at
  `2026-06-08T23:24:57Z`:

```text
===== keep-alive tick 2026-06-08T23:24:57Z =====
[2026-06-08T23:24:57Z] deep_page_loop OK pid=2778633
[2026-06-08T23:24:58Z] sustained_loop OK pid=2691392
[2026-06-08T23:24:58Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T23:24:58Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

- Live process table at verification time:

```text
2691390       1    02:27:24 bash -c node scripts/buy30331-sustained-loop.mjs & wait
2691392 2691390    02:27:24 node scripts/buy30331-sustained-loop.mjs
2778630       1    02:03:20 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
2778633 2778630    02:03:20 node scripts/buy30590-deep-page-loop.mjs
```

## Disposition

BUY-36329 can close `done`.

The keep-alive implementation, the 5-minute timer wiring, and the lock-safe
restart path are present in this checkout, and a fresh verification tick
confirmed the live Oracle deep-page and sustained lanes are being observed
correctly without stale lock inheritance.
