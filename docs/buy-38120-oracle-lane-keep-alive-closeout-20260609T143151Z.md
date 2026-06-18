# BUY-38120 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T14:31:51Z)

Issue scope: execute the `BUY-30854` Oracle lane keep-alive watchdog, confirm
the 5-minute restart path still works for dead Oracle lanes, and leave durable
proof from this heartbeat.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 80 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs'
stat -c '%y %n' data/buy30590-deep-page-loop.stopped
stat -c '%y %n' data/checkpoints/buy30590_woocommerce.completed
stat -c '%y %n' data/buy30727-supervisor.stopped
```

## Findings

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported only the known unrelated
  `/etc/systemd/system/hindsight.service:14` warning; there were no errors for
  `systemd/paperclip-lane-keep-alive.service` or
  `systemd/paperclip-lane-keep-alive.timer`.
- The live keep-alive log captured a real dead-lane restart during this
  heartbeat: `sustained_loop` was detected dead at `2026-06-09T14:12:22Z` and
  relaunched successfully at `2026-06-09T14:12:24Z` as pid `3131982`.
- Later ticks proved the recovery held. The latest block appended in this
  heartbeat completed at `2026-06-09T14:31:29Z` with `sustained_loop` healthy
  at pid `3131982`.
- `deep_page_loop` was intentionally absent and correctly skipped because
  `data/buy30590-deep-page-loop.stopped` exists and was last updated at
  `2026-06-09 12:32:23.508154346 +0000`.
- `woocommerce_discover` remained intentionally skipped by completion marker
  `data/checkpoints/buy30590_woocommerce.completed`, last updated at
  `2026-06-06 02:26:34.831697028 +0000`.
- `lane_supervisor` remained intentionally skipped by stop marker
  `data/buy30727-supervisor.stopped`, last updated at
  `2026-06-05 20:44:24.113131171 +0000`.
- `data/buy30854-keep-alive-state.json` reset all tracked lane dead counters to
  `0` after the successful restart:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `data/buy30854-keep-alive-escalation.json` did not gain a new escalation
  entry in this heartbeat; it still only contains the older `deep_page_loop`
  escalation history from 2026-06-08.

## Log Excerpt

```text
===== keep-alive tick 2026-06-09T14:12:22Z =====
[2026-06-09T14:12:22Z] deep_page_loop STOPPED (already absent)
[2026-06-09T14:12:22Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T14:12:22Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T14:12:24Z] sustained_loop restarted pid=3131982 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=3131979
[2026-06-09T14:12:25Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T14:12:25Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T14:12:25Z] keep-alive tick complete
...
===== keep-alive tick 2026-06-09T14:31:29Z =====
[2026-06-09T14:31:29Z] deep_page_loop STOPPED (already absent)
[2026-06-09T14:31:29Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T14:31:29Z] sustained_loop OK pid=3131982
[2026-06-09T14:31:29Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T14:31:29Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T14:31:29Z] keep-alive tick complete
```

## Disposition

`BUY-38120` can close `done`. This heartbeat revalidated the committed
watchdog/unit wiring and captured fresh runtime proof that the dead-lane restart
path still works on the intended 5-minute keep-alive flow for `BUY-30854`.
