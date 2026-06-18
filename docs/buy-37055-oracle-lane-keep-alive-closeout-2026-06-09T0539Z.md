# BUY-37055 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T05:39Z)

Wake scope: confirm the Oracle 5-minute keep-alive still restarts dead lanes
and remains active in the live workspace.

## What I verified

- `scripts/buy30854-lane-keep-alive.sh` is still the active watchdog and owns
  the Oracle lane restart path for `deep_page_loop` and `sustained_loop`.
- `systemd/paperclip-lane-keep-alive.timer` still preserves the 5-minute
  cadence with `OnUnitActiveSec=5min`.
- `systemd/paperclip-lane-keep-alive.service` still runs the watchdog as a
  oneshot from this workspace.
- The live keep-alive log shows an actual restart of `deep_page_loop` at
  `2026-06-09T05:26:32Z`, then subsequent healthy ticks through
  `2026-06-09T05:39:23Z`.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 30 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs'
```

## Evidence

- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; it reported no errors for
  `paperclip-lane-keep-alive.service` or `.timer`.
- Recent log excerpt:

```text
===== keep-alive tick 2026-06-09T05:26:32Z =====
[2026-06-09T05:26:32Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T05:26:34Z] deep_page_loop restarted pid=375929 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=375926
[2026-06-09T05:26:35Z] sustained_loop OK pid=3907215
[2026-06-09T05:26:35Z] keep-alive tick complete
...
===== keep-alive tick 2026-06-09T05:39:23Z =====
[2026-06-09T05:39:23Z] deep_page_loop OK pid=375929
[2026-06-09T05:39:23Z] sustained_loop OK pid=3907215
[2026-06-09T05:39:23Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` is back to zero dead counters for all
  tracked lanes after the restart:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `pgrep` after the manual tick confirmed both live Oracle processes:

```text
375929 node scripts/buy30590-deep-page-loop.mjs
3907215 node scripts/buy30331-sustained-loop.mjs
```

## Disposition

No code change was needed in this wake. The Oracle 5-minute keep-alive remains
wired, the restart path fired successfully for a dead lane on 2026-06-09, and
the current state/log evidence shows the watchdog healthy again.
