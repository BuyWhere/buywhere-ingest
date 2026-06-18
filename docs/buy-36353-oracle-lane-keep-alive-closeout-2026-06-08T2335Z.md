# BUY-36353 — BUY-30854 lane keep-alive closeout (2026-06-08T23:35Z)

Issue scope: verify that the Oracle lane keep-alive path in this checkout still
provides the intended 5-minute restart/watchdog behavior for dead Oracle lanes
and that the runtime remains healthy enough to close the issue.

## Commands run

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
ps -eo pid,ppid,etime,cmd | grep -E 'buy30590-deep-page-loop|buy30331-sustained-loop|buy30590-woocommerce-discover|buy30727-lane-supervisor' | grep -v grep
cat data/buy30854-keep-alive-state.json
tail -n 20 logs/buy30854_keep_alive.log
```

## Results

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported no Oracle keep-alive unit errors. The only
  output remained the unrelated host warning for
  `/etc/systemd/system/hindsight.service`.
- The manual keep-alive tick appended a fresh healthy block at
  `2026-06-08T23:35:17Z`:

```text
===== keep-alive tick 2026-06-08T23:35:17Z =====
[2026-06-08T23:35:17Z] deep_page_loop OK pid=2778633
[2026-06-08T23:35:17Z] sustained_loop OK pid=2691392
[2026-06-08T23:35:17Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T23:35:17Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

- Live Oracle lane processes at verification time:

```text
2691390       1    02:37:43 bash -c node scripts/buy30331-sustained-loop.mjs & wait
2691392 2691390    02:37:43 node scripts/buy30331-sustained-loop.mjs
2778630       1    02:13:39 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
2778633 2778630    02:13:39 node scripts/buy30590-deep-page-loop.mjs
```

## Disposition

BUY-36353 can close `done`.

The 5-minute Oracle lane keep-alive remains present and healthy in this
checkout: the watchdog script parses cleanly, the service and timer units verify
cleanly apart from an unrelated host warning, and a fresh manual tick confirmed
the active Oracle deep-page and sustained lanes are still alive without needing
restart.
