# BUY-38568 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T18:29:08Z)

Issue scope: re-verify the `BUY-30854` Oracle lane keep-alive watchdog in the
active workspace, confirm the 5-minute restart path is still wired, and leave
durable evidence from this heartbeat.

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 12 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
ls -l data/buy30590-deep-page-loop.stopped data/checkpoints/buy30590_woocommerce.completed data/buy30727-supervisor.stopped
```

Findings:

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; there were no verification errors for
  `paperclip-lane-keep-alive.service` or `.timer`.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the watchdog cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`, and the service remains a
  `Type=oneshot` wrapper around `scripts/buy30854-lane-keep-alive.sh`.
- A fresh keep-alive tick completed at `2026-06-09T18:28:48Z`:

```text
===== keep-alive tick 2026-06-09T18:28:48Z =====
[2026-06-09T18:28:48Z] deep_page_loop STOPPED (already absent)
[2026-06-09T18:28:48Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T18:28:48Z] sustained_loop OK pid=3782962
[2026-06-09T18:28:48Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T18:28:48Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T18:28:48Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` remained reset after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `sustained_loop` is the only actively running Oracle lane at the moment; the
  other tracked lanes are intentionally suppressed by durable control markers:
  - `data/buy30590-deep-page-loop.stopped` last updated `2026-06-09 12:32 UTC`
  - `data/checkpoints/buy30590_woocommerce.completed` exists from
    `2026-06-06 02:26 UTC`
  - `data/buy30727-supervisor.stopped` exists from `2026-06-05 20:44 UTC`
- `data/buy30854-keep-alive-escalation.json` gained no new entry in this
  heartbeat. The only recorded escalations remain older `deep_page_loop` events
  from `2026-06-08`, before that lane was intentionally stop-marked.
- The restart path in `scripts/buy30854-lane-keep-alive.sh` still includes the
  detached relaunch plus `exec 9>&-` close, so a revived lane cannot inherit and
  pin the watchdog lock fd.

Disposition:

`BUY-38568` can close `done`: the Oracle 5-minute keep-alive watchdog is still
active and verifiable, the latest tick completed successfully, tracked state is
healthy, and all non-running lanes are skipped for explicit operator markers
rather than because the restart path regressed.
