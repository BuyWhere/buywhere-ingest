# BUY-36341 — BUY-30854 Oracle lane keep-alive closeout (2026-06-08T23:29Z)

Issue scope: confirm the Oracle keep-alive path is still enforcing 5-minute
restarts for dead Oracle lanes and close the stale execution issue with fresh
runtime evidence from the current workspace.

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `tail -n 80 logs/buy30854_keep_alive.log`

## Runtime evidence

The current watchdog log shows automatic ticks continuing well after the earlier
closeout, including:

```text
===== keep-alive tick 2026-06-08T23:24:57Z =====
[2026-06-08T23:24:58Z] deep_page_loop OK pid=2778633
[2026-06-08T23:24:58Z] sustained_loop OK pid=2691392
[2026-06-08T23:24:58Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T23:24:58Z] keep-alive tick complete
===== keep-alive tick 2026-06-08T23:26:43Z =====
[2026-06-08T23:26:43Z] deep_page_loop OK pid=2778633
[2026-06-08T23:26:43Z] sustained_loop OK pid=2691392
[2026-06-08T23:26:43Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T23:26:43Z] keep-alive tick complete
```

A fresh manual invocation in this heartbeat appended:

```text
===== keep-alive tick 2026-06-08T23:29:41Z =====
[2026-06-08T23:29:41Z] deep_page_loop OK pid=2778633
[2026-06-08T23:29:41Z] sustained_loop OK pid=2691392
[2026-06-08T23:29:41Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T23:29:41Z] keep-alive tick complete
```

`data/buy30854-keep-alive-state.json` after the fresh tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

## Deployment wiring

- `systemd/paperclip-lane-keep-alive.service` runs the watchdog from this
  workspace as a oneshot unit.
- `systemd/paperclip-lane-keep-alive.timer` defines the 5-minute cadence with
  `OnUnitActiveSec=5min`.

## Note on unit verification

`systemd-analyze verify` reported one unrelated host warning only:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

No Oracle keep-alive unit errors were reported.

## Disposition

This issue can close `done`. The Oracle lane keep-alive implementation is
present, the 5-minute systemd timer is defined in-repo, automatic ticks are
continuing in the live log, and a fresh invocation in this heartbeat confirmed
the tracked Oracle lanes remain healthy.
