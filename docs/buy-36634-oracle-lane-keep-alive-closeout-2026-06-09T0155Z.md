# BUY-36634 — Oracle lane keep-alive closeout (2026-06-09T01:55Z)

Wake scope: `BUY-30854` lane keep-alive, specifically the 5-minute restart path
for dead Oracle lanes.

## Current implementation

- `scripts/buy30854-lane-keep-alive.sh` is the active watchdog and now carries
  the dead-lane restart logic, duplicate-process suppression, a non-blocking
  flock lock, per-lane dead-tick state, and escalation recording after 4
  consecutive dead ticks.
- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a
  `Type=oneshot` unit.
- `systemd/paperclip-lane-keep-alive.timer` preserves the 5-minute cadence with
  `OnUnitActiveSec=5min`.

## Verification

Commands run from the checked-out workspace:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
```

`systemd-analyze verify` emitted only the known unrelated host warning for
`/etc/systemd/system/hindsight.service`; the Oracle keep-alive units validated.

Fresh watchdog log tail after the manual tick:

```text
===== keep-alive tick 2026-06-09T01:54:51Z =====
[2026-06-09T01:54:51Z] deep_page_loop OK pid=2778633
[2026-06-09T01:54:51Z] sustained_loop OK pid=2691392
[2026-06-09T01:54:51Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T01:54:51Z] keep-alive tick complete
```

State files after the verification tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

`data/buy30854-keep-alive-escalation.json` still contains only historical
entries from 2026-06-08 when `deep_page_loop` remained dead across multiple
ticks. No new escalation was recorded during this wake.

## Conclusion

`BUY-36634` can close `done`: the Oracle keep-alive watchdog and 5-minute timer
remain in place, the watchdog script validates, and a fresh manual tick confirms
the live Oracle lanes are being observed correctly without duplicating processes.
