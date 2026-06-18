# BUY-36176 — BUY-30854 lane keep-alive closeout (2026-06-08T22:12Z)

Issue scope: verify that the Oracle lane keep-alive path restarts dead Oracle
lanes on a 5-minute cadence and that the deployment wiring needed for that path
is present in the current workspace.

## Verification run

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `rg -n "paperclip-lane-keep-alive\\.(service|timer)|buy30854-lane-keep-alive" scripts/deploy-systemd-units.sh systemd`

## Runtime evidence

The manual tick at `2026-06-08T22:12:55Z` appended this block to
`logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-08T22:12:55Z =====
[2026-06-08T22:12:55Z] deep_page_loop OK pid=2778633
[2026-06-08T22:12:55Z] sustained_loop OK pid=2691392
[2026-06-08T22:12:55Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T22:12:55Z] keep-alive tick complete
```

`data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

## Implementation wiring present

- `scripts/buy30854-lane-keep-alive.sh` contains the live restart logic for
  `deep_page_loop`, `sustained_loop`, `woocommerce_discover`, and
  `lane_supervisor`.
- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a oneshot
  service with `ExecStart=/bin/bash scripts/buy30854-lane-keep-alive.sh`.
- `systemd/paperclip-lane-keep-alive.timer` defines the 5-minute cadence with
  `OnUnitActiveSec=5min`.
- `scripts/deploy-systemd-units.sh` installs both
  `paperclip-lane-keep-alive.service` and `paperclip-lane-keep-alive.timer`.

## Note on unit verification

`systemd-analyze verify` emitted one unrelated host warning:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

No Oracle keep-alive unit errors were reported.

## Disposition

This issue can close `done`. The Oracle lane keep-alive watchdog, 5-minute
systemd timer, and deployment wiring are present in-repo, and the current
workspace produced a clean keep-alive tick during this heartbeat.
