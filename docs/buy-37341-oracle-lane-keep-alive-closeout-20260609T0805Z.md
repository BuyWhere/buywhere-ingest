# BUY-37341 — Oracle lane keep-alive closeout (2026-06-09T08:05Z)

Scope: `BUY-30854` 5-minute keep-alive for dead Oracle lanes.

## What this heartbeat verified

- The live watchdog script is present at `scripts/buy30854-lane-keep-alive.sh`.
- The in-repo systemd units still define the intended 5-minute cadence:
  - `systemd/paperclip-lane-keep-alive.service`
  - `systemd/paperclip-lane-keep-alive.timer`
- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer` completed; the only warning came from unrelated host unit `hindsight.service`.

## Live workspace verification

Workspace root used for the live run:

`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c`

Commands run:

```bash
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash -n scripts/buy30854-lane-keep-alive.sh
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy30854-lane-keep-alive.sh
ps -eo pid,etimes,cmd | rg "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs"
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30854-keep-alive-state.json
tail -n 5 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy30854_keep_alive.log
```

Observed live Oracle lane processes:

```text
670904 node scripts/buy30331-sustained-loop.mjs
748760 node scripts/buy30590-deep-page-loop.mjs
```

Latest keep-alive log block:

```text
[2026-06-09T08:04:55Z] deep_page_loop OK pid=748760
[2026-06-09T08:04:55Z] sustained_loop OK pid=670904
[2026-06-09T08:04:55Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T08:04:55Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T08:04:55Z] keep-alive tick complete
```

State file after the tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Result

The Oracle keep-alive restart path is live and working in the checked workspace:

- the watchdog runs cleanly,
- both active Oracle lanes are detected as alive,
- dead-count state is reset to zero after the successful tick, and
- the expected skips remain in place for WooCommerce completion and the intentionally stopped supervisor.

This heartbeat did not require a new code change.
