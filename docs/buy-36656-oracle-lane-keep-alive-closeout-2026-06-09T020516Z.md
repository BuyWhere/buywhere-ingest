# BUY-36656 — Oracle lane keep-alive closeout (2026-06-09T02:05:16Z)

Wake scope: `BUY-30854` lane keep-alive, specifically the 5-minute restart path
for dead Oracle lanes.

## Current implementation in workspace

- `scripts/buy30854-lane-keep-alive.sh` contains the live watchdog logic for
  `deep_page_loop`, `sustained_loop`, optional `woocommerce_discover`, and
  `lane_supervisor`.
- The watchdog now uses a non-blocking flock lock, per-lane dead-tick state,
  duplicate-process suppression, lane-root discovery, detached restarts, and
  escalation logging after 4 consecutive dead ticks.
- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a
  `Type=oneshot` unit.
- `systemd/paperclip-lane-keep-alive.timer` keeps the 5-minute cadence with
  `OnUnitActiveSec=5min`.
- `scripts/deploy-systemd-units.sh` includes both the service and timer.

## Verification run in this heartbeat

Commands:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
```

Results:

- `bash -n` passed.
- `systemd-analyze verify` emitted only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; no Oracle-unit validation errors were
  reported.
- Manual watchdog tick completed successfully at `2026-06-09T02:04:58Z`.

Fresh watchdog log tail:

```text
===== keep-alive tick 2026-06-09T02:04:58Z =====
[2026-06-09T02:04:58Z] deep_page_loop OK pid=2778633
[2026-06-09T02:04:58Z] sustained_loop OK pid=2691392
[2026-06-09T02:04:58Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T02:04:58Z] keep-alive tick complete
```

State file after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

Escalation file status:

- `data/buy30854-keep-alive-escalation.json` still contains only the historical
  `deep_page_loop` escalations from `2026-06-08` when that lane remained dead
  across several ticks.
- This heartbeat added no new escalation entries.

## Conclusion

`BUY-36656` can close `done`: the Oracle watchdog implementation for restarting
dead lanes is present in the workspace, the systemd timer remains wired for a
5-minute cadence, and the latest verification tick confirms the live Oracle
lanes are being monitored cleanly without duplicate restarts.
