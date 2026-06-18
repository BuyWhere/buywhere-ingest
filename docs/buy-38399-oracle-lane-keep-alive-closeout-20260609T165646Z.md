# BUY-38399 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T16:56:46Z)

Issue scope: confirm the Oracle keep-alive path still restarts dead Oracle lanes
on a 5-minute cadence and capture fresh runtime evidence before closing the
execution issue.

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`

## Fresh runtime evidence

The manual tick at `2026-06-09T16:56:46Z` appended this result to
`logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-09T16:56:46Z =====
[2026-06-09T16:56:46Z] deep_page_loop STOPPED (already absent)
[2026-06-09T16:56:46Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T16:56:46Z] sustained_loop OK pid=3578415
[2026-06-09T16:56:46Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T16:56:46Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T16:56:46Z] keep-alive tick complete
```

`data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Implementation status

- `scripts/buy30854-lane-keep-alive.sh` remains the active watchdog and still
  contains the dead-lane restart path for Oracle lanes.
- `systemd/paperclip-lane-keep-alive.service` remains the oneshot systemd unit
  that runs the watchdog.
- `systemd/paperclip-lane-keep-alive.timer` still defines the 5-minute cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.

## Note on `systemd-analyze verify`

The verify command still emits one unrelated host warning for
`/etc/systemd/system/hindsight.service`:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

That warning is outside the Oracle keep-alive units. No Oracle-unit-specific
errors were reported.

## Disposition

BUY-38399 can close `done`. The Oracle keep-alive watchdog remains wired to a
5-minute timer, the watchdog still records healthy-or-skipped status for each
tracked lane, and all current dead-count state is zero after the fresh manual
tick.
