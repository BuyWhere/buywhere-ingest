# BUY-38143 Oracle lane keep-alive closeout

Timestamp: `2026-06-09T14:46:47Z`

## Scope

Fresh verification for [BUY-30854](/BUY/issues/BUY-30854): confirm the Oracle
lane watchdog still restarts dead lanes on a 5-minute cadence and that the
current live state matches intended stop/completion markers.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 80 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
ls -l data/buy30590-deep-page-loop.stopped
```

## Results

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; it reported no errors for
  `systemd/paperclip-lane-keep-alive.service` or
  `systemd/paperclip-lane-keep-alive.timer`.
- A fresh keep-alive tick completed at `2026-06-09T14:42:21Z`.
- The live log also captured a same-day dead-lane recovery at
  `2026-06-09T14:12:22Z`, where `sustained_loop` was detected dead and
  restarted as pid `3131982` by `2026-06-09T14:12:24Z`.
- Subsequent ticks through `2026-06-09T14:42:22Z` kept `sustained_loop`
  healthy at pid `3131982`.
- `deep_page_loop` remained intentionally stopped because
  `data/buy30590-deep-page-loop.stopped` is present and the watchdog logged it
  as `STOPPED`/`SKIPPED` rather than treating it as dead.
- `woocommerce_discover` remained intentionally skipped by
  `data/checkpoints/buy30590_woocommerce.completed`.
- `lane_supervisor` remained intentionally skipped by the BUY-31452 stop marker
  `data/buy30727-supervisor.stopped`.
- `data/buy30854-keep-alive-state.json` still shows zero dead counts for all
  tracked lanes.
- `data/buy30854-keep-alive-escalation.json` still ends at the prior
  `2026-06-08T21:21:49Z` `deep_page_loop` escalation; no new escalation entry
  was added in this heartbeat.

## Timer and service

- `systemd/paperclip-lane-keep-alive.timer` still uses
  `OnUnitActiveSec=5min` with `Persistent=true`.
- `systemd/paperclip-lane-keep-alive.service` still runs
  `ExecStart=/bin/bash scripts/buy30854-lane-keep-alive.sh` as a oneshot
  watchdog from this workspace.

## Conclusion

BUY-30854 remains satisfied in the live Oracle workspace: the watchdog script,
systemd cadence, and current lane state are consistent with the intended
5-minute keep-alive behavior, including a fresh same-day restart of a dead
lane and correct honoring of explicit stop/completion markers.
