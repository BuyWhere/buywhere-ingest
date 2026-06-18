# BUY-36014 — sustained throughput keep-alive tick (2026-06-08T21:05Z)

Routine execution issue for Vera's 5-minute sustained-throughput keep-alive watchdog.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
bash scripts/buy30854-lane-keep-alive.sh
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
ps -eo pid,ppid,etime,cmd | grep -E 'buy30590-deep-page-loop|buy30331-sustained-loop|buy30590-woocommerce-discover|buy30727-lane-supervisor' | grep -v grep
tail -n 30 logs/buy30854_keep_alive.log
```

## Results

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `bash scripts/buy30854-lane-keep-alive.sh` completed successfully and appended a fresh tick ending `2026-06-08T21:05:45Z`.
- Fresh log block from `logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-08T21:05:42Z =====
[2026-06-08T21:05:43Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=5)
[2026-06-08T21:05:45Z] deep_page_loop restarted pid=2721335 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
[2026-06-08T21:05:45Z] deep_page_loop ESCALATED — consecutive_dead_ticks=5 >= 4; written to /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive-escalation.json
[2026-06-08T21:05:45Z] sustained_loop OK pid=2691392
[2026-06-08T21:05:45Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T21:05:45Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` after the tick:

```json
{
  "deep_page_loop": 5,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

- `data/buy30854-keep-alive-escalation.json` now includes a fresh `deep_page_loop` escalation at `2026-06-08T21:05:45Z` with `dead_ticks=5`.
- Post-run process snapshot at `2026-06-08T21:06:10Z`:

```text
2691390       1       08:27 bash -c node scripts/buy30331-sustained-loop.mjs & wait
2691392 2691390       08:27 node scripts/buy30331-sustained-loop.mjs
2721335       1       00:27 node scripts/buy30590-deep-page-loop.mjs
```

## Disposition

This execution issue can close `done`: the keep-alive watchdog fired successfully, restarted the dead `deep_page_loop`, and left `sustained_loop` alive. The repeated `deep_page_loop` escalations are a lane-health follow-up, not a failure of this single 5-minute execution tick; that investigation is already documented in `BUY-35976`.
