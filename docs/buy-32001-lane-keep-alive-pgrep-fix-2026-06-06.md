# BUY-32001 — lane keep-alive pgrep pattern fix

## Symptom (caught on 2026-06-06 heartbeat)

`scripts/buy30854-lane-keep-alive.sh` was incorrectly reporting two alive
lanes as DEAD and spawning duplicate short-lived processes that died in the
heartbeat-cgroup window. The actual long-lived processes kept running
untouched because the keep-alive never found them.

Example from `logs/buy30854_keep_alive.log`:

```
[2026-06-05T21:24:00Z] deep_page_loop OK pid=3042321
[2026-06-05T21:24:00Z] sustained_loop OK pid=2210102
... 4-hour gap (routine had been stalled) ...
[2026-06-06T01:20:30Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-06T01:20:32Z] deep_page_loop restarted pid=3992921
[2026-06-06T01:20:32Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-06T01:20:35Z] sustained_loop restarted pid=3993233
```

But `ps -eo pid,etime,cmd` 4 minutes later showed the original PIDs were
still alive — the keep-alive had spawned duplicate children that died
while the parents (3042321, 3742757) were never killed.

## Root cause

The script's pgrep pattern was `node scripts/buy30590-deep-page-loop.mjs`
(prefixed with `node ` and a relative path). The long-lived lanes were
started with the **absolute** path, so their `/proc/<pid>/cmdline` is:

```
node /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30590-deep-page-loop.mjs
```

`pgrep -af` is a literal-substring match, so `node scripts/...` did **not**
match `/abs/path/scripts/...`. Result: every routine tick thought the lane
was dead and spawned a fresh `node scripts/<name>.mjs` child (the
relative-path form, which the pgrep *did* match, masking the bug for the
*next* tick but also creating a duplicate).

## Fix

Changed pgrep pattern from `node scripts/<name>.mjs` to bare `<name>.mjs`
for all three live lanes (`deep_page_loop`, `sustained_loop`,
`lane_supervisor`). The bare filename matches both
`node /abs/path/scripts/<name>.mjs` and `node scripts/<name>.mjs`.

Files updated:

- `scripts/buy30854-lane-keep-alive.sh` (project repo, legacy 4-lane variant)
- `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30854-lane-keep-alive.sh`
  (live workspace copy, the one the 5-min routine actually invokes)

Both `pgrep_pat` and the bare `pgrep -f` calls in the project-repo copy
were updated. The workspace copy's `pgrep_pat` helper already filters out
its own `buy30854-lane-keep-alive` argv and the wrapping `/bin/bash` line,
so the bare filename is safe to feed through it.

## Verification

Post-fix tick at 2026-06-06T01:26:46Z:

```
[2026-06-06T01:26:46Z] deep_page_loop OK pid=3042321
[2026-06-06T01:26:46Z] sustained_loop OK pid=3742757
[2026-06-06T01:26:46Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-06T01:26:46Z] keep-alive tick complete
```

Both long-lived absolute-path processes are now detected correctly and
`buy30854-keep-alive-state.json` shows `deep_page_loop: 0` and
`sustained_loop: 0` (consecutive-dead-tick counter reset to 0 because
the lanes are alive).

Sanity test of the pgrep helper against all three patterns:

```
pgrep_pat buy30590-deep-page-loop.mjs = 3042321
pgrep_pat buy30331-sustained-loop.mjs = 3742757
pgrep_pat buy30727-lane-supervisor.mjs = 3747066
```

No duplicates were left behind by the buggy ticks — `ps` shows exactly
one of each lane. The restart command itself was unchanged (still
`node scripts/<name>.mjs` from `$ROOT`), so a fresh restart from a dead
state still spawns the relative-path form, which the new pattern
continues to match.

## Operational status

- Routine `a791c831-d108-4027-81c0-aca7014a09d0` (`5min-keep-alive`,
  cron `*/5 * * * *`, `concurrencyPolicy: skip_if_active`) firing on
  cadence; the 01:23:25Z fire was skipped because this execution issue
  is in_progress (expected behaviour).
- `lane_supervisor` remains SKIPPED per Rich's BUY-31452 directive (47
  CC-MAIN indices saturated, `data/buy30727-supervisor.stopped` marker
  present).
- No escalation triggered — the dead-tick counter never reached the
  4-tick threshold, because the lanes were always actually alive.

## Related

- Parent: [BUY-30854](/BUY/issues/BUY-30854) (Oracle accelerated discovery)
- Routine: `a791c831-d108-4027-81c0-aca7014a09d0`
- Trigger: cron `*/5 * * * *` UTC
- Source: [docs/buy-30854-lane-keep-alive.md](/BUY/issues/BUY-30854#document-buy-30854-lane-keep-alive)
