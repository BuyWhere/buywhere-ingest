# BUY-37289 — Oracle lane keep-alive closeout (2026-06-09T07:44:55Z)

Issue scope: verify the `BUY-30854` 5-minute Oracle lane keep-alive still
restarts dead lanes, confirm the current watchdog/timer path remains healthy,
and leave a durable closeout artifact for this heartbeat.

## What I verified

- `scripts/buy30854-lane-keep-alive.sh` is still the active watchdog for the
  Oracle lanes in this workspace.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog from this
  checkout and `systemd/paperclip-lane-keep-alive.timer` still enforces the
  5-minute cadence.
- The watchdog log already contains a same-day proof that it restarted a dead
  Oracle lane:
  - `2026-06-09T07:10:16Z` — `deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)`
  - `2026-06-09T07:10:18Z` — `deep_page_loop restarted pid=748760 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=748757`
- A fresh manual tick during this heartbeat completed successfully at
  `2026-06-09T07:44:38Z` through `2026-06-09T07:44:39Z`.
- Current live processes after the fresh tick:
  - `748760 node scripts/buy30590-deep-page-loop.mjs`
  - `670904 node scripts/buy30331-sustained-loop.mjs`
- `data/buy30854-keep-alive-state.json` stayed fully reset at zero for all
  tracked lanes after the fresh tick.
- `data/buy30854-keep-alive-escalation.json` gained no new escalation entries in
  this heartbeat.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
bash scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30727-lane-supervisor.mjs'
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
tail -n 20 logs/buy30854_keep_alive.log
```

## Notes

- `systemd-analyze verify` did not report any problem in the keep-alive service
  or timer. It did emit one unrelated environment warning from
  `/etc/systemd/system/hindsight.service:14` about an unknown
  `StartLimitIntervalSec` key in the `Service` section.
- `lane_supervisor` remains intentionally skipped because
  `data/buy30727-supervisor.stopped` is present (`BUY-31452` stop marker).
- `woocommerce_discover` remains intentionally skipped because
  `data/checkpoints/buy30590_woocommerce.completed` is present.

## Conclusion

`BUY-37289` can close `done`: the Oracle keep-alive path is still wired through
the local watchdog and 5-minute timer, a dead `deep_page_loop` lane was
successfully restarted on `2026-06-09`, and the latest manual tick confirmed the
remaining active lanes are healthy with zero outstanding dead-count state.
