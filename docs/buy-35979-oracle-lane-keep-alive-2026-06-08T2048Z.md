# BUY-35979 — Oracle lane keep-alive heartbeat (2026-06-08T20:48Z)

Issue scope: execute the `BUY-30854` lane keep-alive watchdog and verify the
live 5-minute path still restarts dead Oracle lanes.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
ps -eo pid,ppid,etime,cmd | grep -E 'buy30590-deep-page-loop|buy30331-sustained-loop|buy30590-woocommerce-discover|buy30727-lane-supervisor' | grep -v grep
```

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- A fresh watchdog run at `2026-06-08T20:48:05Z` found `deep_page_loop`
  healthy again as `pid=2654414`, proving the earlier restart on the live
  Oracle workspace held through the next 5-minute tick.
- The watchdog reset `deep_page_loop` back to `0` in
  `data/buy30854-keep-alive-state.json` while preserving the earlier escalation
  history from `2026-06-08T20:33:36Z`, `2026-06-08T20:37:59Z`, and
  `2026-06-08T20:42:46Z`.
- `sustained_loop` remained alive and `lane_supervisor` remained intentionally
  skipped because `data/buy30727-supervisor.stopped` is still present.

Latest watchdog log block:

```text
===== keep-alive tick 2026-06-08T20:48:05Z =====
[2026-06-08T20:48:05Z] deep_page_loop OK pid=2654414
[2026-06-08T20:48:05Z] sustained_loop OK pid=2350985
[2026-06-08T20:48:05Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T20:48:05Z] keep-alive tick complete
```

State after the run:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

Escalation record:

```json
{
  "escalations": [
    {
      "lane": "deep_page_loop",
      "dead_ticks": 4,
      "at": "2026-06-08T20:33:36Z",
      "note": "lane DEAD on >=4 consecutive keep-alive ticks; escalate to parent BUY-30854 with diagnostic context"
    },
    {
      "lane": "deep_page_loop",
      "dead_ticks": 5,
      "at": "2026-06-08T20:37:59Z",
      "note": "lane DEAD on >=4 consecutive keep-alive ticks; escalate to parent BUY-30854 with diagnostic context"
    },
    {
      "lane": "deep_page_loop",
      "dead_ticks": 6,
      "at": "2026-06-08T20:42:46Z",
      "note": "lane DEAD on >=4 consecutive keep-alive ticks; escalate to parent BUY-30854 with diagnostic context"
    }
  ]
}
```

Post-run process snapshot:

```text
2350983       1    01:30:18 bash -c node scripts/buy30331-sustained-loop.mjs & wait
2350985 2350983    01:30:18 node scripts/buy30331-sustained-loop.mjs
2654414       1       01:05 node scripts/buy30590-deep-page-loop.mjs
```

## Result

This heartbeat re-verified the watchdog contract on the live 5-minute path:
the Oracle lane keep-alive previously restarted a dead lane, and on the next
tick the relaunched lane stayed up and was recognized as healthy. No watchdog
code change is needed on this issue; the remaining work is the separate root
cause diagnosis for why `deep_page_loop` dies in the first place.
