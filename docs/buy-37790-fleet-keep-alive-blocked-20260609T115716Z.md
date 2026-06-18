# BUY-37790 — BUY-31716 fleet keep-alive blocked closeout (2026-06-09T11:57:16Z)

Issue scope: execute the `BUY-31716` 5-minute fleet keep-alive watchdog in the
current workspace, confirm the restart path for the 8 discovery lanes remains
wired, and leave the issue in a truthful final disposition for the current live
state.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,240p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-disk-pressure.marker
df -h /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
```

## Findings

- `bash -n scripts/buy31716-fleet-keep-alive.sh` passed.
- `systemd-analyze verify` reported no error for
  `systemd/paperclip-buy31716-fleet-keep-alive.service` or
  `systemd/paperclip-buy31716-fleet-keep-alive.timer`; the only output was the
  known unrelated `/etc/systemd/system/hindsight.service` warning.
- The fleet watchdog is still wired through
  `scripts/buy31716-fleet-keep-alive.sh` and the timer still runs every
  5 minutes via `OnUnitActiveSec=5min` with `Persistent=true`.
- The latest normal liveness-check tick in the shared Oracle workspace log was
  `2026-06-09T11:46:37Z` through `2026-06-09T11:46:39Z`, and it reported all 8
  tracked lanes healthy:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`,
  and `stock_page`.
- The most recent watchdog executions at `2026-06-09T11:51:52Z` and
  `2026-06-09T11:56:31Z` did not run the normal liveness/restart path. They
  entered the intended disk-pressure guard path instead:
  - `2026-06-09T11:51:52Z`: `disk-pressure TRIP — use=95% >= threshold=95%`
  - `2026-06-09T11:56:31Z`: `disk-pressure PAUSE — marker present`
- Live disk usage has recovered only to `92%`, but the guard will not clear the
  marker until usage drops below the configured recover threshold of `90%`.
- Shared state now records:
  - `disk_last_sampled_at=2026-06-09T11:56:31Z`
  - `disk_use_pct=92`
  - `disk_pressure_pauses=12`
  - all per-lane dead counts remain `0`
- The current marker file proves the present blocker:

```json
{
  "created_at": "2026-06-09T11:51:52Z",
  "use_pct": 95,
  "threshold_pct": 95,
  "root": "/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c",
  "note": "write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)"
}
```

## Disposition

`BUY-37790` should move to `blocked`, not `done`: the keep-alive wiring and
5-minute cadence are intact, and the last normal tick proved all 8 lanes alive,
but the fleet watchdog is currently paused by an active disk-pressure marker and
will not resume normal liveness/restart checks until the Oracle workspace
filesystem drops below `90%` usage and clears the guard.
