# BUY-36817 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T03:39:51Z)

Issue scope: execute the 5-minute Oracle lane keep-alive watchdog and confirm
it still restarts dead Oracle lanes without duplicating live processes.

## Verified implementation

- `scripts/buy30854-lane-keep-alive.sh` remains the active watchdog and still
  checks `deep_page_loop`, `sustained_loop`, optional
  `woocommerce_discover`, and the optional `lane_supervisor`.
- The watchdog still uses `flock` plus detached `nohup setsid` restarts that
  explicitly close FD 9 before relaunching a dead lane, preventing lock
  inheritance from `data/buy30854-keep-alive.lock`.
- `systemd/paperclip-lane-keep-alive.service` is still the oneshot unit that
  runs the watchdog in this checkout.
- `systemd/paperclip-lane-keep-alive.timer` still holds the 5-minute cadence
  through `OnUnitActiveSec=5min` with `Persistent=true`.

## Commands run

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs'
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported no errors for the Oracle keep-alive units;
  the only output was the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`.
- Direct watchdog execution completed successfully and the most recent log tail
  shows the fresh `2026-06-09T03:34:39Z` tick keeping both live Oracle lanes
  healthy:

```text
===== keep-alive tick 2026-06-09T03:34:39Z =====
[2026-06-09T03:34:39Z] deep_page_loop OK pid=3907026
[2026-06-09T03:34:39Z] sustained_loop OK pid=3907215
[2026-06-09T03:34:39Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T03:34:39Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T03:34:39Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` is fully reset, showing no consecutive
  dead ticks:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- Live process inspection after the tick still showed both Oracle lanes running:

```text
3907023 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
3907026 node scripts/buy30590-deep-page-loop.mjs
3907212 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
3907215 node scripts/buy30331-sustained-loop.mjs
```

## Disposition

`BUY-36817` can close `done`: the 5-minute Oracle lane keep-alive watchdog ran
successfully in this heartbeat, the timer/service wiring still verifies, and the
tracked Oracle lanes are healthy with zero dead-tick carryover.
