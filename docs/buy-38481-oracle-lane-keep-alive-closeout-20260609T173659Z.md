# BUY-38481 — Oracle lane keep-alive closeout (2026-06-09T17:36:59Z)

Issue scope: execute the `BUY-30854` Oracle lane keep-alive watchdog in the
checked-out workspace, verify the 5-minute restart path still behaves
correctly, and leave durable proof from this heartbeat.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
ps -eo pid,etimes,cmd | rg 'buy30331-sustained-loop\.mjs|buy30590-deep-page-loop\.mjs|buy30590-woocommerce-discover\.mjs|buy30727-lane-supervisor\.mjs'
```

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported only the known unrelated
  `/etc/systemd/system/hindsight.service` warning; the watchdog service and
  timer verified cleanly.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the intended cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- The manual watchdog tick completed at `2026-06-09T17:36:29Z`:

```text
===== keep-alive tick 2026-06-09T17:36:28Z =====
[2026-06-09T17:36:28Z] deep_page_loop STOPPED (already absent)
[2026-06-09T17:36:29Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T17:36:29Z] sustained_loop OK pid=3782962
[2026-06-09T17:36:29Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T17:36:29Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T17:36:29Z] keep-alive tick complete
```

- Current lane state file after the tick reset all tracked counts to zero:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- The only active Oracle lane process in this heartbeat was the intentionally
  running sustained loop:

```text
3782959     922 bash -c node scripts/buy30331-sustained-loop.mjs & wait
3782962     922 node scripts/buy30331-sustained-loop.mjs
```

- The skip markers remained intentional rather than accidental:
  - `data/buy30590-deep-page-loop.stopped` last updated `2026-06-09 12:32`
  - `data/checkpoints/buy30590_woocommerce.completed` last updated `2026-06-06 02:26`
  - `data/buy30727-supervisor.stopped` last updated `2026-06-05 20:44`

- The shared watchdog log still contains fresh same-day proof that the restart
  path fires when a live lane actually dies:

```text
[2026-06-09T16:22:41Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T16:22:43Z] sustained_loop restarted pid=3578415 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3578412
```

## Disposition

`BUY-38481` can close `done`: the Oracle keep-alive watchdog still runs on the
intended 5-minute cadence, respects the current intentional stop/completion
markers, and the current log proves the dead-lane restart path still succeeds
when an active Oracle lane drops.
