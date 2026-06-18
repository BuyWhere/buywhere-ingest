# BUY-37408 — Oracle lane keep-alive closeout (2026-06-09T08:39:30Z)

Issue scope: execute the `BUY-30854` 5-minute Oracle lane keep-alive watchdog,
verify the dead-lane restart path remains healthy in the live Oracle workspace,
and close this execution issue.

## Current implementation

- `scripts/buy30854-lane-keep-alive.sh` remains the active watchdog for the
  Oracle lanes.
- `systemd/paperclip-lane-keep-alive.service` still runs that watchdog as a
  `Type=oneshot` unit from this workspace.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the 5-minute cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.

## Verification run

Commands executed:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy30854_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30854-keep-alive-state.json
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30854-keep-alive-escalation.json
ps -eo pid,etimes,cmd | rg "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs" -S
```

Observed results:

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; it reported no errors for
  `paperclip-lane-keep-alive.service` or `.timer`.
- The fresh manual keep-alive tick ran at `2026-06-09T08:39:30Z` and completed
  at `2026-06-09T08:39:31Z`.
- That log block shows:
  - `deep_page_loop OK pid=748760`
  - `sustained_loop OK pid=670904`
  - `woocommerce_discover SKIPPED` because
    `data/checkpoints/buy30590_woocommerce.completed` exists
  - `lane_supervisor SKIPPED` because `data/buy30727-supervisor.stopped` exists
- The immediately preceding log block also shows a real dead-lane restart on
  `2026-06-09T06:49:26Z`, where `sustained_loop` was detected dead and relaunched
  as pid `670904`. That confirms the restart path remains active, not just the
  healthy-path check.
- The live process table now includes:
  - `748760 node scripts/buy30590-deep-page-loop.mjs`
  - `670904 node scripts/buy30331-sustained-loop.mjs`
- `data/buy30854-keep-alive-state.json` has the tracked Oracle keys reset:
  - `deep_page_loop: 0`
  - `sustained_loop: 0`
  - `woocommerce_discover: 0`
  - `lane_supervisor: 0`
- `data/buy30854-keep-alive-escalation.json` was unchanged by this heartbeat and
  still contains only historical escalation entries from earlier incidents.

## Disposition

`BUY-37408` can close `done`: the 5-minute Oracle lane keep-alive watchdog ran
successfully in the live workspace, the current tick left both active Oracle
lanes healthy, and the recent log history still demonstrates the dead-lane
restart path working as intended.
