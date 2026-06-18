# BUY-36182 — BUY-30854 lane keep-alive closeout (2026-06-08T22:18Z)

Issue scope: verify that the Oracle lane keep-alive path still restarts dead
Oracle lanes on a 5-minute cadence and that the current workspace still
contains the deployment wiring for that path.

## Verification run

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `rg -n "paperclip-lane-keep-alive\.(service|timer)|buy30854-lane-keep-alive" scripts/deploy-systemd-units.sh systemd`

## Runtime evidence

The manual tick at `2026-06-08T22:18:02Z` appended this block to
`logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-08T22:18:02Z =====
[2026-06-08T22:18:02Z] deep_page_loop OK pid=2778633
[2026-06-08T22:18:02Z] sustained_loop OK pid=2691392
[2026-06-08T22:18:02Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T22:18:02Z] keep-alive tick complete
```

`data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

The escalation file still contains older `deep_page_loop` incidents through
`2026-06-08T21:21:49Z`, but this heartbeat added no new escalation entry.

## Deployment wiring present

- `systemd/paperclip-lane-keep-alive.service` runs the watchdog with
  `ExecStart=/bin/bash scripts/buy30854-lane-keep-alive.sh`.
- `systemd/paperclip-lane-keep-alive.timer` sets the 5-minute cadence with
  `OnUnitActiveSec=5min`.
- `scripts/deploy-systemd-units.sh` includes both
  `paperclip-lane-keep-alive.service` and `paperclip-lane-keep-alive.timer` in
  `PLAIN_UNITS`.

## Note on unit verification

`systemd-analyze verify` emitted one unrelated host warning:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

No Oracle keep-alive unit errors were reported.

## Disposition

This issue can close `done`. The Oracle lane keep-alive watchdog and 5-minute
systemd timer are present in the current workspace, and the live watchdog path
produced a clean tick during this heartbeat.
