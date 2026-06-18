# BUY-38128 — Oracle lane keep-alive closeout (2026-06-09T14:37:02Z)

Issue scope: verify the `BUY-30854` 5-minute Oracle lane keep-alive watchdog
still restarts dead Oracle lanes and remains healthy in the current workspace.

## What I verified

- `scripts/buy30854-lane-keep-alive.sh` is still the active watchdog entrypoint.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog as a
  `Type=oneshot` service from this checkout.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the 5-minute cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 40 logs/buy30854_keep_alive.log
sed -n '1,120p' data/buy30854-keep-alive-state.json
pgrep -af "buy30331-sustained-loop.mjs|buy30590-deep-page-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs"
stat -c '%y %n' data/buy30590-deep-page-loop.stopped
stat -c '%y %n' data/checkpoints/buy30590_woocommerce.completed
stat -c '%y %n' data/buy30727-supervisor.stopped
```

## Findings

- `bash -n` passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning from
  `/etc/systemd/system/hindsight.service:14`; there were no errors for
  `paperclip-lane-keep-alive.service` or `.timer`.
- The live keep-alive log captured a real dead-lane recovery in this runtime
  window:

```text
===== keep-alive tick 2026-06-09T14:12:22Z =====
[2026-06-09T14:12:22Z] deep_page_loop STOPPED (already absent)
[2026-06-09T14:12:22Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T14:12:22Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T14:12:24Z] sustained_loop restarted pid=3131982 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3131979
```

- A fresh manual watchdog run in this heartbeat completed cleanly, and the log
  continued through healthy ticks at `2026-06-09T14:31:29Z` and
  `2026-06-09T14:36:29Z` with `sustained_loop OK pid=3131982`.
- `pgrep -af` after the manual run confirmed the relaunched sustained loop was
  still live:

```text
3131979 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
3131982 node scripts/buy30331-sustained-loop.mjs
```

- `deep_page_loop` remained intentionally stopped because
  `data/buy30590-deep-page-loop.stopped` is present with timestamp
  `2026-06-09 12:32:23 +0000`.
- `woocommerce_discover` remained intentionally skipped by completion marker
  `data/checkpoints/buy30590_woocommerce.completed` dated
  `2026-06-06 02:26:34 +0000`.
- `lane_supervisor` remained intentionally skipped by stop marker
  `data/buy30727-supervisor.stopped` dated `2026-06-05 20:44:24 +0000`.
- `data/buy30854-keep-alive-state.json` stayed fully reset after the recovery
  and fresh manual run:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Conclusion

`BUY-38128` can close `done`: the Oracle keep-alive watchdog is still wired to a
5-minute systemd cadence, it proved live dead-lane restart behavior for
`sustained_loop` at `2026-06-09T14:12:24Z`, and the subsequent manual and timer
driven ticks left the active Oracle lane healthy with all dead counters reset.
