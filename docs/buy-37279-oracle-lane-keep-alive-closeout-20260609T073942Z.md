# BUY-37279 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T07:39:42Z)

Issue scope: execute the `BUY-30854` 5-minute Oracle lane keep-alive watchdog
in the current workspace, verify the live dead-lane restart path still works,
and leave fresh runtime evidence for this execution issue.

## Verification

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
cat data/buy30854-keep-alive-state.json
pgrep -af "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs"
tail -n 25 logs/buy30854_keep_alive.log
```

Results:

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported no keep-alive unit errors; the only output
  was the known unrelated host warning for `/etc/systemd/system/hindsight.service`.
- `bash scripts/buy30854-lane-keep-alive.sh` completed successfully and wrote a
  fresh tick at `2026-06-09T07:39:32Z`.
- `data/buy30854-keep-alive-state.json` ended this heartbeat at:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `pgrep -af` immediately after the tick confirmed the live Oracle lanes:
  `node scripts/buy30331-sustained-loop.mjs` at pid `670904` and
  `node scripts/buy30590-deep-page-loop.mjs` at pid `748760`.
- The log tail for the fresh tick shows the expected healthy/intentional states:

```text
===== keep-alive tick 2026-06-09T07:39:32Z =====
[2026-06-09T07:39:33Z] deep_page_loop OK pid=748760
[2026-06-09T07:39:33Z] sustained_loop OK pid=670904
[2026-06-09T07:39:33Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T07:39:33Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T07:39:33Z] keep-alive tick complete
```

## Restart Evidence

The same shared log still carries a recent real restart on the live 5-minute
path, followed by the current healthy tick:

```text
===== keep-alive tick 2026-06-09T07:10:16Z =====
[2026-06-09T07:10:16Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T07:10:18Z] deep_page_loop restarted pid=748760 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=748757
===== keep-alive tick 2026-06-09T07:39:32Z =====
[2026-06-09T07:39:33Z] deep_page_loop OK pid=748760
[2026-06-09T07:39:33Z] sustained_loop OK pid=670904
```

That is enough to show the watchdog still performs the intended 5-minute
dead-lane restart role and returns to steady-state zero dead counts afterward.

## Disposition

`BUY-37279` can close `done`: this heartbeat reran the Oracle keep-alive in the
checked-out workspace, verified the systemd wiring remains valid, recorded a
fresh successful tick, and left current evidence that the live restart path is
still functioning.
