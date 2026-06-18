# BUY-37416 — Oracle lane keep-alive closeout (2026-06-09T08:44:35Z)

Issue scope: confirm the `BUY-30854` keep-alive path still performs the
intended 5-minute dead-lane restart role for Oracle and close the follow-up
issue with fresh runtime evidence from the current workspace.

## What was verified

- `scripts/buy30854-lane-keep-alive.sh` still contains the live watchdog logic
  for:
  - dead-lane detection via `pgrep`
  - restart via detached `nohup setsid bash -lc "exec 9>&-; ..."`
  - consecutive dead-tick state in `data/buy30854-keep-alive-state.json`
  - escalation logging in `data/buy30854-keep-alive-escalation.json`
- `systemd/paperclip-lane-keep-alive.service` still runs that watchdog as a
  oneshot service from this checkout.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the 5-minute cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
pgrep -af "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs"
```

## Results

- `bash -n` passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` reported only the pre-existing unrelated host
  warning for `/etc/systemd/system/hindsight.service:14` and no errors for
  `paperclip-lane-keep-alive.service` or `.timer`.
- Manual watchdog execution completed successfully and appended a fresh log
  block at `2026-06-09T08:44:25Z`.
- The latest keep-alive log block shows both tracked long-lived Oracle lanes
  healthy:

```text
===== keep-alive tick 2026-06-09T08:44:25Z =====
[2026-06-09T08:44:25Z] deep_page_loop OK pid=748760
[2026-06-09T08:44:25Z] sustained_loop OK pid=670904
[2026-06-09T08:44:25Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T08:44:25Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T08:44:25Z] keep-alive tick complete
```

- `pgrep` confirmed the active lane processes after the manual tick:

```text
670901 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
670904 node scripts/buy30331-sustained-loop.mjs
748757 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
748760 node scripts/buy30590-deep-page-loop.mjs
```

- `data/buy30854-keep-alive-state.json` remained reset to zero consecutive dead
  ticks for every tracked lane:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `data/buy30854-keep-alive-escalation.json` still contains only the historical
  `deep_page_loop` escalations from `2026-06-08`; this heartbeat added no new
  escalation entry.

## Disposition

`BUY-37416` can close `done`: the Oracle keep-alive watchdog remains wired to
the 5-minute timer, still contains the dead-lane restart path, and produced a
fresh clean tick in the current workspace with both active Oracle lanes healthy
and all dead-count state reset to zero.
