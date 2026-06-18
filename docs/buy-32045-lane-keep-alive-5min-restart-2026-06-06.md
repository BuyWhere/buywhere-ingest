# BUY-32045 — 5-minute restart of dead Oracle lanes

## Summary

Confirmed that the 5-minute BUY-30854 keep-alive routine is actively restarting
dead Oracle lanes, and synced the checked-out repo copy of
`scripts/buy30854-lane-keep-alive.sh` to the live watchdog implementation so
the behavior is preserved in source control.

## What changed

- Replaced the repo's legacy 4-lane keep-alive script with the live logic used
  by the Oracle workspace watchdog.
- The repo script now includes:
  - root-scoped process filtering so only the Oracle workspace lanes are matched
  - duplicate-process cleanup when multiple matching lane processes exist
  - per-lane dead-tick state persisted in `data/buy30854-keep-alive-state.json`
  - escalation recording after 4 consecutive dead ticks
  - checkpoint-aware `woocommerce_discover` handling
  - `buy30727-supervisor.stopped` marker handling for the BUY-31452 stop order

## Evidence

Live keep-alive log in the Oracle workspace:

```text
===== keep-alive tick 2026-06-06T01:58:54Z =====
[2026-06-06T01:58:54Z] deep_page_loop OK pid=4121471
[2026-06-06T01:58:54Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-06T01:58:56Z] sustained_loop restarted pid=4151740
[2026-06-06T01:58:56Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-06T01:58:56Z] keep-alive tick complete
```

Follow-up validation run using the patched repo script against the live
workspace:

```text
===== keep-alive tick 2026-06-06T02:04:12Z =====
[2026-06-06T02:04:12Z] deep_page_loop OK pid=4121471
[2026-06-06T02:04:12Z] sustained_loop OK pid=4153029
[2026-06-06T02:04:12Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-06T02:04:12Z] keep-alive tick complete
```

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy30854-lane-keep-alive.sh`

## Result

The live Oracle keep-alive path is satisfying the issue contract: dead lanes are
checked on a 5-minute cadence and restarted on the next keep-alive tick.
