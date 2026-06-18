# BUY-36162 — BUY-30854 Oracle lane keep-alive closeout (2026-06-08T22:08Z)

Issue scope: confirm the Oracle keep-alive path now restarts dead Oracle lanes
on a 5-minute cadence and that the current workspace is healthy enough to close
the implementation issue.

## Current verification

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`

## Fresh runtime evidence

The manual tick at `2026-06-08T22:08:26Z` appended this block to
`logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-08T22:08:26Z =====
[2026-06-08T22:08:26Z] deep_page_loop OK pid=2778633
[2026-06-08T22:08:26Z] sustained_loop OK pid=2691392
[2026-06-08T22:08:26Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T22:08:26Z] keep-alive tick complete
```

`data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

## Implementation status

- `scripts/buy30854-lane-keep-alive.sh` is the live watchdog.
- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a oneshot
  service.
- `systemd/paperclip-lane-keep-alive.timer` defines the 5-minute cadence with
  `OnUnitActiveSec=5min`.
- `scripts/deploy-systemd-units.sh` installs both the service and timer.

## Note on `systemd-analyze verify`

The verify command still emits one unrelated host warning for
`/etc/systemd/system/hindsight.service`:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

That warning is outside the Oracle keep-alive units. No Oracle-unit-specific
errors were reported.

## Disposition

This issue can close `done`. The code path for 5-minute Oracle lane restarts is
implemented, deployment wiring is present in-repo, and the current workspace
produced a clean verification tick with both primary Oracle lanes healthy.
