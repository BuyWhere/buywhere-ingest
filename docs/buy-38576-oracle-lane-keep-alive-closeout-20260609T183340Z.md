# BUY-38576 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T18:33:40Z)

Issue scope: verify that the Oracle lane keep-alive watchdog in this checkout still
enforces the intended 5-minute restart cadence for dead Oracle lanes, then leave
fresh runtime evidence for the current heartbeat.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
stat -c '%y %n' data/buy30590-deep-page-loop.stopped data/checkpoints/buy30590_woocommerce.completed data/buy30727-supervisor.stopped
```

## Results

- `scripts/buy30854-lane-keep-alive.sh` passed `bash -n`.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog as a `Type=oneshot` service from this workspace.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the 5-minute cadence via `OnUnitActiveSec=5min` with `Persistent=true`.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning and no keep-alive unit errors.
- A fresh manual keep-alive tick completed at `2026-06-09T18:33:40Z`.
- `sustained_loop` remained healthy at pid `3782962`.
- `deep_page_loop` was intentionally skipped because `data/buy30590-deep-page-loop.stopped` exists and was last updated at `2026-06-09 12:32:23 +0000`; the watchdog correctly treated that lane as intentionally stopped rather than dead.
- `woocommerce_discover` was intentionally skipped because `data/checkpoints/buy30590_woocommerce.completed` exists.
- `lane_supervisor` was intentionally skipped because `data/buy30727-supervisor.stopped` exists for the BUY-31452 stop path.
- `data/buy30854-keep-alive-state.json` reset all tracked dead counters to zero after the tick.
- `data/buy30854-keep-alive-escalation.json` contains only the older 2026-06-08 deep-page escalation history and gained no new entry in this heartbeat.

## Log excerpt

```text
===== keep-alive tick 2026-06-09T18:28:48Z =====
[2026-06-09T18:28:48Z] deep_page_loop STOPPED (already absent)
[2026-06-09T18:28:48Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T18:28:48Z] sustained_loop OK pid=3782962
[2026-06-09T18:28:48Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T18:28:48Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T18:28:48Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T18:33:40Z =====
[2026-06-09T18:33:40Z] deep_page_loop STOPPED (already absent)
[2026-06-09T18:33:40Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T18:33:40Z] sustained_loop OK pid=3782962
[2026-06-09T18:33:40Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T18:33:40Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T18:33:40Z] keep-alive tick complete
```

## Current state

`data/buy30854-keep-alive-state.json`:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

Conclusion: the `BUY-30854` Oracle keep-alive remains active on the intended
5-minute cadence. In this heartbeat there was no dead-lane restart because the
only non-running tracked lane was intentionally stop-marked, and the watchdog
correctly avoided treating that state as a failure.
