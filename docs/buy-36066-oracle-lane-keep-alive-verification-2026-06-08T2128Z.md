# BUY-36066 — Oracle lane keep-alive verification (2026-06-08T21:28Z)

## Scope

Verify that the BUY-30854 Oracle keep-alive now performs the intended 5-minute
 dead-lane restart behavior without pinning its own lock or leaving stale dead
 counters behind.

## What I verified

1. The watchdog artifacts in the repo still encode the intended 5-minute
   cadence:
   - `systemd/paperclip-lane-keep-alive.timer` uses `OnBootSec=1min` and
     `OnUnitActiveSec=5min`
   - `systemd/paperclip-lane-keep-alive.service` runs
     `scripts/buy30854-lane-keep-alive.sh`
   - `scripts/deploy-systemd-units.sh` installs and enables both units
2. The keep-alive script in this checkout already contains the lock-release
   spawn path:

```bash
nohup setsid bash -lc "exec 9>&-; $cmd & wait" >> "$logfile" 2>&1 < /dev/null &
```

That closes FD 9 before the detached lane is launched, preventing the restarted
lane from inheriting `data/buy30854-keep-alive.lock`.

## Runtime verification

Commands run from the project checkout:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
cat data/buy30854-keep-alive-state.json
tail -n 40 logs/buy30854_keep_alive.log
ps -fp 2778630,2778633
```

Observed results:

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify ...` returned only an unrelated warning for
  `/etc/systemd/system/hindsight.service`; no error for the keep-alive units.
- Before the manual verification tick, the stale state file still showed:

```json
{
  "deep_page_loop": 8,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

- The manual keep-alive run appended a successful health-check tick at
  `2026-06-08T21:28:32Z`:

```text
===== keep-alive tick 2026-06-08T21:28:32Z =====
[2026-06-08T21:28:32Z] deep_page_loop OK pid=2778633
[2026-06-08T21:28:32Z] sustained_loop OK pid=2691392
[2026-06-08T21:28:32Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-08T21:28:32Z] keep-alive tick complete
```

- After that tick, the watchdog reset the stale counter:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

- Live process sample immediately after verification:

```text
paperclip 2778630 1        bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
paperclip 2778633 2778630  node scripts/buy30590-deep-page-loop.mjs
```

## Conclusion

As of `2026-06-08T21:28:32Z`, the Oracle BUY-30854 keep-alive is performing the
intended dead-lane recovery path correctly:

- the 5-minute timer and service definitions are in place
- the watchdog no longer leaves the keep-alive lock inherited by the restarted
  lane
- a fresh verification tick can now observe the live deep-page lane and reset
  stale dead counters back to `0`

The remaining `lane_supervisor` skip is intentional per BUY-31452 and is not a
keep-alive failure.
