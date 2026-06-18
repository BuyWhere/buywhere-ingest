# BUY-35991 — Oracle lane keep-alive heartbeat (2026-06-08T20:53Z)

Issue scope: execute the `BUY-30854` keep-alive verification path, confirm the
watchdog still restarts dead Oracle lanes, and leave durable evidence on the
execution issue.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
ps -eo pid,ppid,etime,cmd | grep -E 'buy30590-deep-page-loop|buy30331-sustained-loop|buy30590-woocommerce-discover|buy30727-lane-supervisor' | grep -v grep
bash scripts/buy30854-lane-keep-alive.sh
tail -n 30 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
if [ -f data/buy30854-keep-alive-escalation.json ]; then cat data/buy30854-keep-alive-escalation.json; fi
systemctl status paperclip-lane-keep-alive.timer --no-pager
systemctl list-timers paperclip-lane-keep-alive.timer --no-pager
```

## Results

- `bash -n` passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` found no errors in
  `systemd/paperclip-lane-keep-alive.service` or
  `systemd/paperclip-lane-keep-alive.timer`.
- The verify command emitted one unrelated host warning for
  `/etc/systemd/system/hindsight.service`:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

- Pre-check process table showed the live Oracle lanes currently present:

```text
2350985 node scripts/buy30331-sustained-loop.mjs
2662992 node scripts/buy30590-deep-page-loop.mjs
```

- The explicit watchdog invocation at `2026-06-08T20:53:03Z` exited through the
  lock guard because another keep-alive instance already held
  `data/buy30854-keep-alive.lock`:

```text
[2026-06-08T20:53:03Z] keep-alive tick skipped — another instance already holds /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive.lock
```

- Fresh log evidence immediately before this heartbeat shows the watchdog was
  active on the live path and restarted the dead deep-page lane twice:

```text
[2026-06-08T20:49:00Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-08T20:49:02Z] deep_page_loop restarted pid=2662082 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
[2026-06-08T20:49:31Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=2)
[2026-06-08T20:49:33Z] deep_page_loop restarted pid=2662992 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
[2026-06-08T20:49:33Z] sustained_loop OK pid=2350985
[2026-06-08T20:49:33Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
```

- Persisted state after the observed restarts:

```json
{
  "deep_page_loop": 2,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

- Escalation history remains recorded for the earlier repeated deep-page deaths
  at `20:33:36Z`, `20:37:59Z`, and `20:42:46Z` in
  `data/buy30854-keep-alive-escalation.json`.
- `systemctl status paperclip-lane-keep-alive.timer` reported `Unit
  paperclip-lane-keep-alive.timer could not be found.` and `systemctl
  list-timers` returned `0 timers listed`, so this environment does not expose
  the unit as installed under `/etc/systemd/system` even though the repo unit
  files validate.

## Conclusion

This heartbeat confirmed the `BUY-30854` watchdog logic is valid and that the
live keep-alive path is actively restarting dead Oracle lanes, with the most
recent deep-page restarts recorded at `2026-06-08T20:49:02Z` and
`2026-06-08T20:49:33Z`. Healthy lanes were left alone, and the intentionally
stopped `lane_supervisor` remained skipped.
