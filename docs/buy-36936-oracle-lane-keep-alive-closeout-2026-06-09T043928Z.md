# BUY-36936 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T04:39:28Z)

Issue scope: confirm the 5-minute Oracle lane keep-alive restart path is
present in this checkout and still operating cleanly against the live lanes.

## Code and deployment wiring present

- `scripts/buy30854-lane-keep-alive.sh` implements the watchdog/restart path
  for the Oracle lanes and persists dead-tick counters in
  `data/buy30854-keep-alive-state.json`.
- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a oneshot
  unit.
- `systemd/paperclip-lane-keep-alive.timer` provides the intended 5-minute
  cadence with `OnBootSec=1min`, `OnUnitActiveSec=5min`, and `Persistent=true`.

## Fresh verification

Commands run in this workspace:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
```

Results:

- `bash -n` passed.
- `systemd-analyze verify` reported no Oracle keep-alive unit errors. The only
  output remained the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`.
- The manual watchdog run appended a fresh healthy tick to
  `logs/buy30854_keep_alive.log` at `2026-06-09T04:39:23Z`:

```text
===== keep-alive tick 2026-06-09T04:39:23Z =====
[2026-06-09T04:39:23Z] deep_page_loop OK pid=3907026
[2026-06-09T04:39:23Z] sustained_loop OK pid=3907215
[2026-06-09T04:39:23Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T04:39:23Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T04:39:23Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` reset all tracked dead counters to
  zero after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- Live process table at verification time:

```text
3907023       1    02:19:57 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
3907026 3907023    02:19:57 node scripts/buy30590-deep-page-loop.mjs
3907212       1    02:19:55 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
3907215 3907212    02:19:55 node scripts/buy30331-sustained-loop.mjs
```

## Disposition

BUY-36936 can close `done`.

The 5-minute Oracle lane keep-alive is wired in this checkout, a fresh manual
tick succeeded, and the live Oracle deep-page and sustained lanes remain
healthy under the watchdog.
