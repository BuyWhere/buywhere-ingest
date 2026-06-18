# BUY-36601 — Oracle lane keep-alive closeout (2026-06-09T01:30:59Z)

Wake scope: `BUY-30854` lane keep-alive, specifically the 5-minute restart path
for dead Oracle lanes.

## What I verified

- `scripts/buy30854-lane-keep-alive.sh` already contains restart logic for dead
  Oracle lanes (`deep_page_loop`, `sustained_loop`, optional
  `woocommerce_discover`, and `lane_supervisor` when not stop-marked).
- `systemd/paperclip-lane-keep-alive.timer` is configured with
  `OnUnitActiveSec=5min`.
- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a oneshot in
  this workspace.

## Commands

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`

## Runtime evidence

Fresh keep-alive log tail after the manual tick:

```text
===== keep-alive tick 2026-06-09T01:27:31Z =====
[2026-06-09T01:27:31Z] deep_page_loop OK pid=2778633
[2026-06-09T01:27:31Z] sustained_loop OK pid=2691392
[2026-06-09T01:27:31Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T01:27:31Z] keep-alive tick complete
```

Current state file:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

## Notes

`systemd-analyze verify` emitted one unrelated host warning:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

That warning is outside the Oracle keep-alive units. No watchdog-specific
verify errors were reported.

## Disposition

This wake did not require a new code change. The Oracle lane keep-alive restart
path and 5-minute timer are already present in the checked-out workspace, a
fresh manual tick succeeded, and the issue can close `done`.
