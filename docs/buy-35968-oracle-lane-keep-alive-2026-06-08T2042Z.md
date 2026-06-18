# BUY-35968 — Oracle lane keep-alive heartbeat (2026-06-08T20:42Z)

Issue scope: execute the `BUY-30854` lane keep-alive watchdog and verify it
still restarts dead Oracle lanes on the live 5-minute path.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
bash scripts/buy30854-lane-keep-alive.sh
tail -n 30 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
ps -eo pid,ppid,etime,cmd | grep -E 'buy30590-deep-page-loop|buy30331-sustained-loop|buy30590-woocommerce-discover|buy30727-lane-supervisor' | grep -v grep
```

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- A fresh watchdog run at `2026-06-08T20:42:44Z` detected `deep_page_loop`
  dead again, restarted it in the live Oracle workspace, and appended a third
  escalation record after the earlier `2026-06-08T20:33:36Z` and
  `2026-06-08T20:37:59Z` escalations.
- `sustained_loop` remained alive and `lane_supervisor` stayed intentionally
  skipped because `data/buy30727-supervisor.stopped` is still present.

Latest watchdog log block:

```text
===== keep-alive tick 2026-06-08T20:42:44Z =====
[2026-06-08T20:42:44Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=6)
[2026-06-08T20:42:46Z] deep_page_loop restarted pid=2640508 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
[2026-06-08T20:42:46Z] deep_page_loop ESCALATED — consecutive_dead_ticks=6 >= 4; written to /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive-escalation.json
[2026-06-08T20:42:46Z] sustained_loop OK pid=2350985
[2026-06-08T20:42:47Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T20:42:47Z] keep-alive tick complete
```

State after the run:

```json
{
  "deep_page_loop": 6,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

Escalation record tail:

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
2350983       1    01:24:59 bash -c node scripts/buy30331-sustained-loop.mjs & wait
2350985 2350983    01:24:59 node scripts/buy30331-sustained-loop.mjs
2640508       1       00:11 node scripts/buy30590-deep-page-loop.mjs
```

## Result

This execution heartbeat satisfied the watchdog contract: the Oracle
keep-alive path ran, detected a dead lane, restarted it, and persisted the
expected escalation artifact. The keep-alive mechanism is functioning, and the
next action is a diagnosis follow-up for the recurring `deep_page_loop`
crashes rather than more changes to the watchdog itself.
