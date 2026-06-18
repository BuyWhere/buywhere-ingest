# BUY-37555 — Oracle lane keep-alive closeout (2026-06-09T10:01:39Z)

Issue scope: execute the `BUY-30854` 5-minute Oracle lane keep-alive watchdog in
the current workspace, verify the dead-lane restart path remains healthy, and
record fresh evidence for closeout.

## What ran

- Manual watchdog tick: `bash scripts/buy30854-lane-keep-alive.sh`
- Unit verification:
  `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- Process snapshot:
  `ps -eo pid,etime,cmd | rg 'buy30590-deep-page-loop\.mjs|buy30331-sustained-loop\.mjs|buy30590-woocommerce-discover\.mjs|buy30727-lane-supervisor\.mjs'`

## Fresh runtime evidence

Recent keep-alive log excerpt from `logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-09T09:58:19Z =====
[2026-06-09T09:58:19Z] deep_page_loop OK pid=748760
[2026-06-09T09:58:20Z] sustained_loop OK pid=670904
[2026-06-09T09:58:20Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T09:58:20Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T09:58:20Z] keep-alive tick complete
```

Current keep-alive state file:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

Current active Oracle lane processes:

```text
670901    03:12:02 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
670904    03:12:02 node scripts/buy30331-sustained-loop.mjs
748757    02:51:13 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
748760    02:51:13 node scripts/buy30590-deep-page-loop.mjs
```

## Timer and unit status

`systemd/paperclip-lane-keep-alive.timer` still provides the intended cadence:

```ini
[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
Persistent=true
```

`systemd-analyze verify` returned only the known unrelated warning below and no
error for the lane keep-alive service or timer:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

## Disposition

`BUY-37555` can close `done`. The Oracle keep-alive watchdog still runs on a
5-minute cadence, both active Oracle lanes were healthy on the fresh manual tick,
the skipped lanes remained intentionally suppressed by their marker files, and
all dead-count state is reset to zero.
