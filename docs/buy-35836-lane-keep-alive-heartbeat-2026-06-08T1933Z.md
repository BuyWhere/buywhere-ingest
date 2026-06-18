# BUY-35836 — BUY-30854 lane keep-alive heartbeat (2026-06-08T19:33Z)

Issue scope: verify the Oracle 5-minute lane keep-alive can restart a dead
lane in the live workspace and leaves healthy lanes alone.

## Driver run

```bash
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c \
  bash scripts/buy30854-lane-keep-alive.sh
```

This run targeted the live Oracle workspace copy at
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c`,
which is the operational path that owns the watchdog logs and state.

## Live evidence

Workspace log excerpt from
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-08T19:33:28Z =====
[2026-06-08T19:33:28Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-08T19:33:30Z] deep_page_loop restarted pid=2400958 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
[2026-06-08T19:33:30Z] sustained_loop OK pid=2350985
[2026-06-08T19:33:30Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T19:33:30Z] keep-alive tick complete
===== keep-alive tick 2026-06-08T19:33:44Z =====
[2026-06-08T19:33:44Z] deep_page_loop OK pid=2400958
[2026-06-08T19:33:44Z] sustained_loop OK pid=2350985
[2026-06-08T19:33:44Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T19:33:44Z] keep-alive tick complete
```

`ps` immediately after the run showed both Oracle lanes alive:

```text
2350985 node scripts/buy30331-sustained-loop.mjs
2400958 node scripts/buy30590-deep-page-loop.mjs
```

Workspace state file
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30854-keep-alive-state.json`
returned the per-lane dead counters to zero:

```json
{
  "deep_page_loop": 0,
  "lane_supervisor": 0,
  "sustained_loop": 0
}
```

## Result

The BUY-35836 execution contract is satisfied:

- a dead Oracle deep-page lane was detected and restarted in the live workspace
- a follow-up tick observed the restarted PID as healthy
- healthy lanes were left alone

Notes:

- `lane_supervisor` remains intentionally skipped because
  `data/buy30727-supervisor.stopped` is present under BUY-31452
- the workspace copy of `scripts/buy30854-lane-keep-alive.sh` is the live
  operational script and includes additional disk-pressure/fleet checks beyond
  the project copy; this heartbeat verified behavior against the live path
