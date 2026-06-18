# BUY-36032 — keep-alive lock inheritance fix (2026-06-08)

## Change

Updated `scripts/buy30854-lane-keep-alive.sh` so restarted Oracle lanes do not
inherit the watchdog's `flock` on `data/buy30854-keep-alive.lock`.

- restart path now runs `nohup setsid bash -lc "exec 9>&-; $cmd & wait"` so FD
  9 is closed before the detached lane process is launched
- restart logging now includes the spawned detached-shell PID for follow-up
  verification

## Verification

1. `bash -n scripts/buy30854-lane-keep-alive.sh`
2. descriptor-inheritance reproduction comparing the old and new spawn patterns

Observed result from the reproduction:

```text
OLD_HOLDER=2770488
NEW_HOLDER=none
```

That demonstrates the pre-fix launch pattern leaked the lock into a surviving
child process, while the new launch pattern releases the lock once the parent
keep-alive exits.
