# BUY-37193 — BUY-30854 Oracle lane keep-alive heartbeat (2026-06-09T06:49:57Z)

Issue scope: execute the Oracle 5-minute lane keep-alive watchdog and verify it
still restarts dead Oracle lanes on the live path.

## Verification

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
ps -eo pid,etime,cmd | grep -E 'buy30590-deep-page-loop|buy30331-sustained-loop|buy30590-woocommerce-discover|buy30727-lane-supervisor' | grep -v grep
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy30854_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30854-keep-alive-state.json
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30854-keep-alive-escalation.json
```

## Results

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported no errors for
  `paperclip-lane-keep-alive.service` or `.timer`; the only output was the
  known unrelated host warning for `/etc/systemd/system/hindsight.service`.
- `systemd/paperclip-lane-keep-alive.service` still executes
  `scripts/buy30854-lane-keep-alive.sh` from this checkout as a `Type=oneshot`
  unit.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the 5-minute cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- A fresh watchdog run in the live Oracle workspace appended a new log block at
  `2026-06-09T06:49:26Z`.
- The watchdog found `deep_page_loop` healthy and detected
  `sustained_loop` dead on this tick:

```text
===== keep-alive tick 2026-06-09T06:49:26Z =====
[2026-06-09T06:49:26Z] deep_page_loop OK pid=375929
[2026-06-09T06:49:26Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T06:49:29Z] sustained_loop restarted pid=670904 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=670901
[2026-06-09T06:49:29Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T06:49:29Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T06:49:29Z] keep-alive tick complete
```

- Post-run process state shows both tracked Oracle lanes live:
  - `deep_page_loop` `pid=375929`
  - `sustained_loop` `pid=670904`
- The live state file now records the expected post-restart counters:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 1,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- No new escalation entry was added on this heartbeat; the escalation file still
  contains only older historical entries.

## Disposition

This heartbeat satisfied the `BUY-37193` contract: the Oracle 5-minute
watchdog ran in the live workspace, detected a dead lane, restarted it within
the same tick, and left the Oracle lane set healthy again.
