# BUY-36889 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T04:15:07Z)

Issue scope: confirm the 5-minute Oracle lane keep-alive still restarts dead
Oracle lanes and remains live in the current workspace.

## What I verified

- `scripts/buy30854-lane-keep-alive.sh` still owns the Oracle dead-lane restart
  path for `deep_page_loop`, `sustained_loop`, optional
  `woocommerce_discover`, and `lane_supervisor`.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog from this
  checkout as a `Type=oneshot` unit.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the 5-minute cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- A fresh direct watchdog run completed successfully during this heartbeat and
  appended the latest live tick through `2026-06-09T04:14:57Z`.

## Verification

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs'
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported no errors for the Oracle keep-alive unit or
  timer; the only output was the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`.
- The latest log tail shows a clean tick at `2026-06-09T04:14:57Z`:
  - `deep_page_loop OK pid=3907026`
  - `sustained_loop OK pid=3907215`
  - `woocommerce_discover SKIPPED` because
    `data/checkpoints/buy30590_woocommerce.completed` is present.
  - `lane_supervisor SKIPPED` because `data/buy30727-supervisor.stopped` is
    present.
- `pgrep -af` confirmed the active Oracle lane processes are still present:
  - `3907026 node scripts/buy30590-deep-page-loop.mjs`
  - `3907215 node scripts/buy30331-sustained-loop.mjs`
- `data/buy30854-keep-alive-state.json` remained fully reset:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `data/buy30854-keep-alive-escalation.json` still contains only the historical
  June 8 `deep_page_loop` escalations; this heartbeat added no new escalation.

## Disposition

`BUY-36889` can close `done`: the Oracle keep-alive watchdog remains live on
the intended 5-minute cadence, the active Oracle lanes are healthy on the
latest `2026-06-09T04:14:57Z` tick, and the restart path for dead lanes remains
present in this checkout without requiring a code change.
