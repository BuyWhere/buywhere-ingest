# BUY-37370 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T08:19:25Z)

Wake scope: `BUY-30854` lane keep-alive, specifically the 5-minute restart path
for dead Oracle lanes. This wake arrived as `issue_assigned` with no pending
comments, so the heartbeat validated the active watchdog implementation and ran a
fresh tick rather than refetching broader thread history.

## Current implementation

- `scripts/buy30854-lane-keep-alive.sh` remains the active watchdog. It checks
  `deep_page_loop` and `sustained_loop`, restarts a lane when `pgrep` finds no
  live process, records consecutive dead ticks in
  `data/buy30854-keep-alive-state.json`, and escalates after 4 dead ticks into
  `data/buy30854-keep-alive-escalation.json`.
- `systemd/paperclip-lane-keep-alive.timer` still preserves the 5-minute cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog as a
  oneshot under the workspace root.

## Verification

Commands executed:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs'
tail -n 60 logs/buy30854_keep_alive.log
```

Results:

- `bash -n` passed.
- `systemd-analyze verify` reported the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`, but no errors for
  `paperclip-lane-keep-alive.service` or `.timer`.
- A fresh manual keep-alive tick completed at `2026-06-09T08:19:25Z`.
- The log block for that tick shows both active Oracle lanes healthy:

```text
===== keep-alive tick 2026-06-09T08:19:24Z =====
[2026-06-09T08:19:24Z] deep_page_loop OK pid=748760
[2026-06-09T08:19:25Z] sustained_loop OK pid=670904
[2026-06-09T08:19:25Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T08:19:25Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T08:19:25Z] keep-alive tick complete
```

- `pgrep -af` confirmed the live Oracle lane processes after the tick:

```text
670904 node scripts/buy30331-sustained-loop.mjs
748760 node scripts/buy30590-deep-page-loop.mjs
```

- `data/buy30854-keep-alive-state.json` is fully reset:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `data/buy30854-keep-alive-escalation.json` still only contains the earlier
  `2026-06-08` dead-lane escalations; this heartbeat did not need a new restart
  or escalation.

## Disposition

`BUY-37370` can close `done`: the Oracle lane keep-alive remains wired to a
5-minute timer, the dead-lane restart path is still present in the watchdog, and
the latest heartbeat completed a clean tick with both active Oracle lanes alive
and zero outstanding dead counts.
