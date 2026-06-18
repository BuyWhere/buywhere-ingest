# BUY-36019 — deep_page_loop forensics after BUY-36010 escalation (2026-06-08T21:09Z)

## Summary

`deep_page_loop` had two distinct runtime problems on June 8, 2026:

1. The repeated deaths that triggered `BUY-36010` were real lane failures under
   oversized deep-page batches. The loop kept restarting on the exact same
   `cursor=640, cycle=5748` state while 80-domain cycles attempted 59k-79k
   product batches and died before `saveState()` could persist progress.
2. After the lane was restarted, the watchdog itself leaked its lock into the
   child process. The current `node scripts/buy30590-deep-page-loop.mjs`
   process inherits FD 9 for `data/buy30854-keep-alive.lock`, so later
   keep-alive fires skip instead of observing `deep_page_loop OK` and clearing
   the stale dead counter.

This means the escalation was not a Paperclip execution-semantics failure. The
lane was genuinely dying, then the keep-alive script left a second runtime bug
that now hides fresh health checks.

## Exact Stop Point

The exact failure window is visible in the live deep-page loop log:

- `logs/buy30590_deep_page_loop.log:18752-18773` repeats fresh starts at the
  same state:
  - `2026-06-08T20:13:09.553Z starting at cursor=640, cycle=5748`
  - `2026-06-08T20:17:34.450Z starting at cursor=640, cycle=5748`
  - `2026-06-08T20:25:44.792Z starting at cursor=640, cycle=5748`
  - `2026-06-08T20:33:34.853Z starting at cursor=640, cycle=5748`
- Those restarts surround oversized work:
  - `logs/buy30590_deep_page_loop.log:18756` logged `59500` products on cycle
    `5749`
  - `logs/buy30590_deep_page_loop.log:18759` logged `79586` products on cycle
    `5749`
- No handled `FATAL:` or `cycle error:` line appears between those repeated
  starts, so the process disappeared before it could finish the cycle and call
  `saveState(state)`.

That is the recurring death pattern that led to the `BUY-36010` escalation at
`2026-06-08T21:02:51Z`.

## What Changed After Containment

The live workspace copy of
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30590-deep-page-loop.mjs`
now defaults to:

- `DEEP_PAGE_BATCH_DOMAINS=8`
- `DEEP_PAGE_CONCURRENCY=4`

After that containment, the lane began advancing immediately:

- `logs/buy30590_deep_page_loop.log:18774-18794` shows cycle `5749`, `5750`,
  `5752`, and `5753` completing after the lower-pressure restart.
- The current state file is
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-deep-page-state.json`
  with `{"cursor":736,"cycle":5760}`.
- Current process sample at `2026-06-08T21:08Z` showed
  `PID 2721335 PPID 1 ELAPSED 02:53 node scripts/buy30590-deep-page-loop.mjs`.

So the repeated deaths observed before `BUY-36010` were contained by reducing
batch pressure, not by any Paperclip status or wake-path change.

## Secondary Runtime Defect: Keep-Alive Lock Leak

The current keep-alive state is misleading because the restarted lane inherited
the watchdog lock:

- `data/buy30854-keep-alive-state.json` still shows `"deep_page_loop": 5`
- manual verification at `2026-06-08T21:07Z` skipped because another process
  already held `data/buy30854-keep-alive.lock`
- `lsof data/buy30854-keep-alive.lock` identified the holder as:
  - `node 2721335 ... data/buy30854-keep-alive.lock`

That lock comes from `scripts/buy30854-lane-keep-alive.sh`, which opens the
lock on FD 9 before calling:

```bash
nohup setsid bash -lc "$cmd" >> "$logfile" 2>&1 < /dev/null &
```

Because FD 9 is not closed before the restart, the relaunched lane inherits the
open file description and keeps the flock alive after the parent shell exits.
Future keep-alive ticks then log:

- `2026-06-08T21:07:50Z keep-alive tick skipped — another instance already holds ...`
- `2026-06-08T21:08:43Z keep-alive tick skipped — another instance already holds ...`

This does not explain the original deaths, but it does explain why the stale
escalated state remains even while the current deep-page loop is alive and
advancing.

## Related Work Reviewed

Reviewed before concluding:

- `docs/buy-35955-deep-page-loop-root-cause-2026-06-08T2044Z.md`
- `docs/buy-35976-deep-page-loop-fix-2026-06-08T2055Z.md`
- `doc/execution-semantics.md`

The new gap compared with those write-ups is the lock-leak mechanism. Earlier
notes captured the workload-pressure failure and one earlier host-ownership
theory, but they did not identify that the restarted lane itself now holds the
keep-alive flock and suppresses later health checks.

## Classification

- `deep_page_loop` deaths before `2026-06-08T20:49Z`: agent-actionable runtime
  bug in the lane's work shape; not a Paperclip liveness stop.
- stale `deep_page_loop=5` dead counter after `2026-06-08T21:05Z`:
  agent-actionable keep-alive bug; watchdog lock leaked into the restarted
  child, so later health checks skip.
- Paperclip execution-semantics path for BUY-36019: already covered. The issue
  had a live assignee path and this investigation produced a concrete diagnosis.

## Recommended Follow-Up

Create one follow-up engineering issue to fix the keep-alive lock inheritance in
`scripts/buy30854-lane-keep-alive.sh`, then re-run one verification tick after
that fix to prove:

1. the restarted child no longer owns `data/buy30854-keep-alive.lock`
2. a subsequent keep-alive tick can observe `deep_page_loop OK`
3. `data/buy30854-keep-alive-state.json` resets `deep_page_loop` back to `0`
