# BUY-38544 Oracle lane keep-alive closeout

- Issue: `BUY-38544`
- Parent: `BUY-30854`
- Captured at: `2026-06-09T18:14:17Z`

## Verification

- `ps -eo pid,etime,cmd | grep -E 'buy30590-deep-page-loop|buy30331-sustained-loop|buy30590-woocommerce-discover|buy30727-lane-supervisor' | grep -v grep`
  - Only `buy30331-sustained-loop.mjs` was live before the tick, at pid `3782962`.
- `bash scripts/buy30854-lane-keep-alive.sh`
  - Completed successfully and appended a fresh keep-alive tick at `2026-06-09T18:14:04Z`.
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
  - Returned only the known unrelated `/etc/systemd/system/hindsight.service` warning.

## Tick result

Tail of `logs/buy30854_keep_alive.log` for the fresh tick:

```text
===== keep-alive tick 2026-06-09T18:14:04Z =====
[2026-06-09T18:14:04Z] deep_page_loop STOPPED (already absent)
[2026-06-09T18:14:04Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T18:14:04Z] sustained_loop OK pid=3782962
[2026-06-09T18:14:04Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T18:14:04Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T18:14:04Z] keep-alive tick complete
```

## State

- `data/buy30854-keep-alive-state.json` remains:
  - `deep_page_loop: 0`
  - `sustained_loop: 0`
  - `woocommerce_discover: 0`
  - `lane_supervisor: 0`
- Stop/completion markers in force:
  - `data/buy30590-deep-page-loop.stopped` last updated `2026-06-09 12:32:23 +0000`
  - `data/buy30727-supervisor.stopped` last updated `2026-06-05 20:44:24 +0000`
  - `data/checkpoints/buy30590_woocommerce.completed` last updated `2026-06-06 02:26:34 +0000`

## Restart-proof context

- The most recent live restart proof remains `docs/buy-37871-oracle-lane-keep-alive-closeout-20260609T123146Z.md`, which recorded repeated `deep_page_loop` restarts at `2026-06-09T12:23:48Z`, `2026-06-09T12:26:42Z`, `2026-06-09T12:27:21Z`, and `2026-06-09T12:30:40Z` before the later stop marker was introduced.
- Since the stop marker was introduced, the watchdog has correctly treated `deep_page_loop` as intentionally stopped rather than dead.

## Cadence

- `systemd/paperclip-lane-keep-alive.timer` still sets:
  - `OnBootSec=1min`
  - `OnUnitActiveSec=5min`
  - `Persistent=true`
