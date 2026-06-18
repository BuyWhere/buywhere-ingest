# BUY-37396 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T08:30Z)

Wake scope: `BUY-30854` lane keep-alive, specifically the 5-minute restart path
for dead Oracle lanes. This wake arrived as `issue_assigned` with no pending
comments, so the heartbeat validated the active watchdog implementation and ran a
fresh manual tick in the current workspace.

## Current implementation

- `scripts/buy30854-lane-keep-alive.sh` remains the active watchdog. It checks
  the Oracle lane processes, restarts a lane when no matching process is live,
  records consecutive dead ticks in `data/buy30854-keep-alive-state.json`, and
  records repeated failures in `data/buy30854-keep-alive-escalation.json`.
- `systemd/paperclip-lane-keep-alive.timer` still preserves the intended cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- `systemd/paperclip-lane-keep-alive.service` still executes the watchdog as a
  oneshot unit rooted in this checkout.

## Verification

Commands executed:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 40 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
ps -eo pid,etimes,cmd | grep -E 'buy30590-deep-page-loop|buy30331-sustained-loop|buy30590-woocommerce-discover|buy30727-lane-supervisor' | grep -v grep
```

Results:

- `bash -n` passed.
- `systemd-analyze verify` only emitted the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; it did not report an error against
  `paperclip-lane-keep-alive.service` or `.timer`.
- The fresh manual tick completed at `2026-06-09T08:29:41Z`.
- The appended log block shows both active Oracle lanes healthy and the two
  intentionally disabled lanes skipped for their existing markers:

```text
===== keep-alive tick 2026-06-09T08:29:41Z =====
[2026-06-09T08:29:41Z] deep_page_loop OK pid=748760
[2026-06-09T08:29:41Z] sustained_loop OK pid=670904
[2026-06-09T08:29:41Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T08:29:41Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T08:29:41Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` is reset to zero for every tracked lane:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `data/buy30854-keep-alive-escalation.json` still only contains earlier
  `2026-06-08` escalations for `deep_page_loop`; this heartbeat did not trigger
  a new restart or escalation.

- Current process state at verification time:

```text
670901 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
670904 node scripts/buy30331-sustained-loop.mjs
748757 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
748760 node scripts/buy30590-deep-page-loop.mjs
```

## Disposition

`BUY-37396` can close `done`: the Oracle lane keep-alive remains wired to the
5-minute systemd timer, the dead-lane restart path is still present in the
watchdog, and the latest manual tick completed with both active Oracle lanes
healthy and zero outstanding dead counts.
