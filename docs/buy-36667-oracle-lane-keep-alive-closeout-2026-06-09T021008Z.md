# BUY-36667 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T02:10Z)

Issue scope: keep the Oracle 5-minute lane watchdog honest by ensuring it
restarts dead lanes without leaving stale dead-count state behind for lanes
that are intentionally skipped.

## What changed

- Updated `scripts/buy30854-lane-keep-alive.sh` so the watchdog now resets:
  - `woocommerce_discover` dead counts to `0` when
    `data/checkpoints/buy30590_woocommerce.completed` is present.
  - `lane_supervisor` dead counts to `0` when
    `data/buy30727-supervisor.stopped` is present.
- This keeps `data/buy30854-keep-alive-state.json` aligned with current
  watchdog semantics instead of preserving misleading historical dead counts.

## Verification

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
WORKSPACE_ROOT="$PWD" bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
```

Results:

- `bash -n` passed.
- `systemd-analyze verify` reported no errors for the Oracle keep-alive units.
  The only output was an unrelated warning from `/etc/systemd/system/hindsight.service`.
- The live watchdog tick at `2026-06-09T02:09:54Z` logged:
  - `deep_page_loop OK pid=2778633`
  - `sustained_loop OK pid=2691392`
  - `woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)`
  - `lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)`
- `data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Conclusion

`BUY-36667` can close `done`: the Oracle keep-alive still validates and runs on
its 5-minute path, and the watchdog state file now clears stale dead counters
for intentionally skipped lanes instead of advertising false failures.
