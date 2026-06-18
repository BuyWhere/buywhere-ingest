# BUY-37958 Oracle lane keep-alive closeout

Timestamp: `2026-06-09T13:11:43Z`

Scope: confirm that the `BUY-30854` Oracle lane keep-alive still runs on a
5-minute cadence, still contains the dead-lane restart implementation, and
still handles intentional lane stop markers without duplicating work.

## Verification

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default bash scripts/buy30854-lane-keep-alive.sh
tail -n 40 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
ls -l --time-style=long-iso data/buy30590-deep-page-loop.stopped data/checkpoints/buy30590_woocommerce.completed data/buy30727-supervisor.stopped
```

Results:

- `bash -n` passed.
- `systemd-analyze verify` reported no errors for the keep-alive service or
  timer. The only output was the known unrelated host warning from
  `/etc/systemd/system/hindsight.service`.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the expected cadence:
  `OnBootSec=1min`, `OnUnitActiveSec=5min`, `Persistent=true`.
- `systemd/paperclip-lane-keep-alive.service` remains `Type=oneshot` and still
  executes `scripts/buy30854-lane-keep-alive.sh`.
- The current watchdog script still contains the dead-lane restart path,
  including the detached relaunch and `exec 9>&-` lock-fd close before spawn:

```bash
nohup setsid bash -lc "exec 9>&-; $cmd & wait" >> "$logfile" 2>&1 < /dev/null &
```

- The manual tick in this heartbeat completed successfully at
  `2026-06-09T13:08:08Z`:

```text
===== keep-alive tick 2026-06-09T13:08:07Z =====
[2026-06-09T13:08:07Z] deep_page_loop STOPPED (already absent)
[2026-06-09T13:08:07Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T13:08:07Z] sustained_loop OK pid=2775043
[2026-06-09T13:08:08Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T13:08:08Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T13:08:08Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` reset all tracked counts to `0` after
  the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `data/buy30590-deep-page-loop.stopped` exists and was updated at
  `2026-06-09 12:32`, so the absence of a fresh deep-page restart in this
  heartbeat is intentional, not a watchdog failure.
- `data/checkpoints/buy30590_woocommerce.completed` and
  `data/buy30727-supervisor.stopped` remain present, so those lanes continue to
  be intentionally skipped.
- `data/buy30854-keep-alive-escalation.json` did not receive a new entry in this
  heartbeat; it still contains only the historical `2026-06-08` deep-page
  escalation records.

## Conclusion

`BUY-37958` can close `done`.

The requested 5-minute keep-alive implementation for `BUY-30854` is present and
verified in the active workspace:

- the systemd timer still drives the watchdog every 5 minutes
- the watchdog still contains the dead-lane restart path and lock-inheritance
  fix
- the current runtime state is healthy and intentionally suppresses the stopped
  deep-page lane instead of thrashing or duplicating it

The latest live dead-lane restart proof remains captured in
`docs/buy-37871-oracle-lane-keep-alive-closeout-20260609T123146Z.md`, where the
watchdog restarted `deep_page_loop` multiple times before the later stop marker
was introduced.
