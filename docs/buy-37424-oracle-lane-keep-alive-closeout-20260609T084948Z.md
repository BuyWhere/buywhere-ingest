# BUY-37424 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T08:49:48Z)

Issue scope: verify the `BUY-30854` 5-minute Oracle lane keep-alive still restarts dead lanes, leave fresh runtime evidence, and dispose the execution issue.

## Verification run

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `tail -n 20 logs/buy30854_keep_alive.log`
- `cat data/buy30854-keep-alive-state.json`
- `cat data/buy30854-keep-alive-escalation.json`
- `pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs'`

## Results

- `scripts/buy30854-lane-keep-alive.sh` still contains the dead-lane restart path for the Oracle lane family.
- `systemd/paperclip-lane-keep-alive.timer` still enforces a 5-minute cadence via `OnUnitActiveSec=5min` and preserves missed ticks with `Persistent=true`.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog as a `Type=oneshot` unit from this workspace.
- `bash -n` passed cleanly.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no errors for the Oracle keep-alive service or timer.
- A fresh manual tick completed at `2026-06-09T08:44:25Z` with:
  - `deep_page_loop OK pid=748760`
  - `sustained_loop OK pid=670904`
  - `woocommerce_discover SKIPPED` because `data/checkpoints/buy30590_woocommerce.completed` is present
  - `lane_supervisor SKIPPED` because `data/buy30727-supervisor.stopped` is present for `BUY-31452`
- `data/buy30854-keep-alive-state.json` is fully reset to zero dead counts:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- The live log still proves the restart path fires when a lane dies. Most recent example in the current log:
  - `2026-06-09T07:10:16Z` `deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)`
  - `2026-06-09T07:10:18Z` `deep_page_loop restarted pid=748760 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=748757`
- `pgrep` confirms the active Oracle lane processes after the verification tick:
  - `670904 node scripts/buy30331-sustained-loop.mjs`
  - `748760 node scripts/buy30590-deep-page-loop.mjs`

## Disposition

`BUY-37424` can close `done`. The 5-minute Oracle lane keep-alive remains wired in repo, executed successfully in this heartbeat, preserved zero dead-count state for the active tracked lanes, and the live log still contains current-day proof that the watchdog restarts dead lanes.
