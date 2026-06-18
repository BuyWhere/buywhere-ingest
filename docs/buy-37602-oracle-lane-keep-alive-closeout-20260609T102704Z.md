# BUY-37602 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T10:27:04Z)

Issue scope: verify the `BUY-30854` Oracle watchdog still restarts dead lanes on a
5-minute cadence and leaves the lanes healthy after recovery.

## Checks run

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs'
rg -n "restarted pid=|DEAD — restarting|ESCALATED" logs/buy30854_keep_alive.log | tail -n 20
```

## Results

- `scripts/buy30854-lane-keep-alive.sh` passed `bash -n`.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; the keep-alive service and timer
  units passed verification.
- A manual watchdog tick completed at `2026-06-09T10:26:38Z` with:
  - `deep_page_loop OK pid=2138816`
  - `sustained_loop OK pid=2139271`
  - `woocommerce_discover SKIPPED` because
    `data/checkpoints/buy30590_woocommerce.completed` exists
  - `lane_supervisor SKIPPED` because `data/buy30727-supervisor.stopped` exists
- `data/buy30854-keep-alive-state.json` reset all tracked dead counters to `0`
  after the tick.
- The active service timer still enforces the 5-minute cadence via
  `OnUnitActiveSec=5min` and `Persistent=true` in
  `systemd/paperclip-lane-keep-alive.timer`.

## Restart-path proof

The current log shows the dead-lane restart path firing successfully earlier in
this same runtime window:

- `2026-06-09T10:09:25Z` `deep_page_loop DEAD — restarting`
- `2026-06-09T10:09:27Z` `deep_page_loop restarted pid=2119031`
- `2026-06-09T10:09:27Z` `sustained_loop DEAD — restarting`
- `2026-06-09T10:09:29Z` `sustained_loop restarted pid=2119205`
- `2026-06-09T10:12:57Z` `deep_page_loop DEAD — restarting`
- `2026-06-09T10:12:59Z` `deep_page_loop restarted pid=2138816`
- `2026-06-09T10:12:59Z` `sustained_loop DEAD — restarting`
- `2026-06-09T10:13:01Z` `sustained_loop restarted pid=2139271`

Those restarts match the watchdog implementation in
`scripts/buy30854-lane-keep-alive.sh`, which detects missing lane processes and
relaunches them detached with `nohup setsid`.

## Conclusion

`BUY-37602` is complete. The Oracle lane keep-alive remains active on a
5-minute cadence, the dead-lane restart path is proven by live log evidence on
June 9, 2026, and the latest manual tick left the tracked Oracle lanes healthy.
