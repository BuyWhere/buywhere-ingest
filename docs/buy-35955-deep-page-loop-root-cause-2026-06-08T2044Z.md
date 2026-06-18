# BUY-35955 — deep-page loop root cause (2026-06-08T20:44Z)

## Summary

`buy30590-deep-page-loop.mjs` is not primarily dying because of an application
error inside the loop. The durable host process for that lane was never
deployed. The repo contains a persistent systemd unit for the deep-page loop and
systemd timer wiring for the keep-alive path, but the live host does not have
either unit installed. As a result, the loop is still being launched as a
heartbeat-owned child process by `scripts/buy30854-lane-keep-alive.sh`, and
those child processes are known to die minutes after the originating heartbeat
ends.

## Evidence

1. The deep-page loop source exists only in Oracle's live workspace and is
   restarted by the keep-alive watchdog from there:

   - `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30590-deep-page-loop.mjs`
   - keep-alive log: restarts at `2026-06-08T20:03:04Z`, `20:07:55Z`,
     `20:13:11Z`, `20:17:36Z`, `20:25:46Z`, `20:33:36Z`

2. The host does not have the persistent units installed:

   - `systemctl status paperclip-buy30590-deep-page-loop.service --no-pager`
     returned `Unit paperclip-buy30590-deep-page-loop.service could not be found.`
   - `systemctl status paperclip-lane-keep-alive.service --no-pager`
     returned `Unit paperclip-lane-keep-alive.service could not be found.`
   - `systemctl status paperclip-lane-keep-alive.timer --no-pager`
     returned `Unit paperclip-lane-keep-alive.timer could not be found.`

3. The repo already contains the intended durable wiring:

   - `systemd/paperclip-buy30590-deep-page-loop.service`
   - `docs/buy-35805-lane-keep-alive-systemd-5min-2026-06-08.md` explicitly
     records that a root-capable operator still needed to deploy the updated
     units to `/etc/systemd/system`.

4. The observed failure mode matches a non-durable launch, not an in-loop fatal:

   - `logs/buy30590_deep_page_loop.log` shows repeated fresh starts with the
     exact same state:
     - `2026-06-08T20:13:09.553Z starting at cursor=640, cycle=5748`
     - `2026-06-08T20:17:34.450Z starting at cursor=640, cycle=5748`
     - `2026-06-08T20:25:44.792Z starting at cursor=640, cycle=5748`
     - `2026-06-08T20:33:34.853Z starting at cursor=640, cycle=5748`
   - The state file on disk still reads `{"cursor":640,"cycle":5748}`, proving
     the process died before it could finish `runCycle()` and persist progress.
   - No `FATAL:` line is logged for those deaths. The process simply disappears
     and is then relaunched on the next keep-alive fire.

## Secondary code issue

The loop only saves `data/buy30590-deep-page-state.json` after a full cycle:

- `scripts/buy30590-deep-page-loop.mjs` mutates `state.cursor` and
  `state.cycle` at the start of `runCycle()`
- it calls `saveState(state)` only after fetch + ingest finish

That means any external termination before end-of-cycle replays the same batch.
This is not the root cause of death, but it amplifies the damage by duplicating
work after every forced restart.

## Root cause

The lane is missing its durable host deployment. The loop is still running on a
heartbeat-owned execution path, so each restart is temporary and the process is
culled again after the heartbeat lifecycle ends. The 4-consecutive-tick
escalation is therefore a deployment/runtime ownership failure, not a product
catalog traversal bug.

## Required unblock action

A root-capable operator must deploy and enable the existing units:

```bash
sudo bash scripts/deploy-systemd-units.sh
systemctl status paperclip-buy30590-deep-page-loop.service --no-pager
systemctl status paperclip-lane-keep-alive.timer --no-pager
systemctl list-timers paperclip-lane-keep-alive.timer
```

After that, re-verify that:

1. `buy30590-deep-page-loop.mjs` is owned by systemd rather than a transient
   heartbeat child.
2. a follow-up keep-alive tick observes the lane `OK` without restart.
3. the deep-page state file advances past `cursor=640, cycle=5748`.
