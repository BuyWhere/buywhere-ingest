# BUY-36079 — Oracle lane keep-alive 5-minute restart verification (2026-06-08)

## Scope

Confirm that the `BUY-30854` Oracle lane keep-alive in this checkout is now
capable of restarting dead Oracle lanes on the intended 5-minute cadence and
that the restarted deep-page lane stays visible to subsequent checks.

## Current implementation

- `systemd/paperclip-lane-keep-alive.timer` defines the 5-minute cadence with
  `OnUnitActiveSec=5min`
- `systemd/paperclip-lane-keep-alive.service` runs
  `scripts/buy30854-lane-keep-alive.sh`
- `scripts/buy30854-lane-keep-alive.sh` restarts dead lanes via:

```bash
nohup setsid bash -lc "exec 9>&-; $cmd & wait" >> "$logfile" 2>&1 < /dev/null &
```

That spawn path explicitly closes FD 9 before launching the detached child, so
the restarted lane does not inherit the keep-alive flock and block later ticks.

## Verification run

Commands run from this checkout on `2026-06-08`:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
bash scripts/buy30854-lane-keep-alive.sh
cat data/buy30854-keep-alive-state.json
tail -n 25 logs/buy30854_keep_alive.log
pgrep -af "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs"
```

Observed state after the verification tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

Recent keep-alive log evidence:

```text
===== keep-alive tick 2026-06-08T21:21:46Z =====
[2026-06-08T21:21:46Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=8)
[2026-06-08T21:21:49Z] deep_page_loop restarted pid=2778633 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2778630
[2026-06-08T21:21:49Z] deep_page_loop ESCALATED — consecutive_dead_ticks=8 >= 4; written to /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/data/buy30854-keep-alive-escalation.json
[2026-06-08T21:28:32Z] deep_page_loop OK pid=2778633
[2026-06-08T21:28:32Z] sustained_loop OK pid=2691392
[2026-06-08T21:29:59Z] deep_page_loop OK pid=2778633
[2026-06-08T21:29:59Z] sustained_loop OK pid=2691392
```

Live process sample:

```text
2691390 bash -c node scripts/buy30331-sustained-loop.mjs & wait
2691392 node scripts/buy30331-sustained-loop.mjs
2778630 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
2778633 node scripts/buy30590-deep-page-loop.mjs
```

## Conclusion

The `BUY-30854` Oracle keep-alive is now achieving the behavior requested by
`BUY-36079`:

- a dead deep-page lane was restarted successfully at `2026-06-08T21:21:49Z`
- later checks still saw the restarted process alive at `2026-06-08T21:28:32Z`
  and `2026-06-08T21:29:59Z`
- the stale dead counter for `deep_page_loop` reset back to `0`

The remaining `lane_supervisor` skip is intentional because
`data/buy30727-supervisor.stopped` is present per `BUY-31452`.
