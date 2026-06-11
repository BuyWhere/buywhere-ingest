# BUY-40344 fleet keep-alive closeout (2026-06-11T00:18Z)

- Issue: `BUY-40344` (routine_execution of `476009cc-7794-4ffb-a997-4b8ef1c9079e`,
  parent `1fd8b0ae-f62e-4d7e-97c7-37b26fbdbe08` = `BUY-32073`).
- Wake at `2026-06-11T00:01:17Z` → checkout at `00:02:24Z`. Verified the
  5-minute keep-alive is healthy and the 8 BUY-31716 fleet lanes are all
  accounted for.

### Cadence (cron + routine dual-active)

- Cron: `*/5 * * * * cd <project> && bash scripts/buy31716-fleet-keep-alive.sh`
  in `crontab -l`. Active.
- Routine: `476009cc-7794-4ffb-a997-4b8ef1c9079e`, status `active`,
  `concurrencyPolicy: skip_if_active`, 3 `*/5` triggers, lastTriggeredAt
  `2026-06-11T00:16:15.248Z`, lastResult `Skipped because a live execution
  issue already exists` (the cron-fired execution issue is acting as the
  live one).
- Both paths write the same unified state file
  `data/buy31716-fleet-keep-alive-state.json` (BUY-34381 consolidation),
  so the dead-tick counters and disk-pressure counters are coherent
  regardless of which path wins the race.

### Verification commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 25 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
ls -la /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-*-sitemap*.stopped
```

### Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- A fresh manual tick at `2026-06-11T00:17:42Z` completed in well under
  5s and appended cleanly to the log; the prior cron-fired ticks at
  `00:15:01Z` and earlier all show the same OK profile.
- Disk: 87% on the fresh tick (87% on `00:15:01Z`, 86% on `00:11:00Z`).
  Below the 95% disk-pause threshold; not blocking.
- All 8 lanes accounted for in the unified state file at
  `data/buy31716-fleet-keep-alive-state.json`:
  - 6 active OK on the fresh tick:
    - `burst_discovery` (pid 166497, 2h46m+ uptime, wrapper bash PPID=166496)
    - `fast_wc_probe` (pid 3848747, 2-18d+ uptime, wrapper bash PPID=3848745)
    - `shopify_index_expansion` (pid 3848851, 2-18d+ uptime, wrapper bash PPID=3848849)
    - `crate_deep_page` (pid 645999, 2m27s uptime — Shopper lane, fresh restart)
    - `hunt2_page` (pid 646562, 2m17s uptime — Shopper lane, fresh restart)
    - `stock_page` (pid 646279, 2m22s uptime — Shopper lane, fresh restart)
  - 2 intentionally skipped (stop markers present and unchanged from
    `2026-06-09 12:30Z`, the `BUY-34229` landscape):
    - `brand_sitemap_miner` via `data/buy30590-brand-sitemap-miner.stopped`
    - `retailer_sitemap_miner` via `data/buy30590-retailer-sitemap-loop.stopped`
    - `stop_if_running` confirmed both already absent and zeroed their
      dead counters.
- All per-lane dead counts at `0` in the unified state file.
- No `STUCK` events (BUY-35267 path: pgrep-alive but stale heartbeat).
  `data/.heartbeat_*` files do not exist for any of the 8 lanes (the
  `classify_heartbeat` `no_hb` path correctly skipped the STUCK check).
- No `ESCALATE` events: `data/buy31716-fleet-keep-alive-escalation.json`
  last touched `2026-06-08T05:51Z` (3 days ago) with the same
  `shopify_index_expansion` entry; no new entry in this heartbeat.
- Last disk-pressure pause: `2026-06-10T09:10:01Z`. Marker file
  `data/buy31716-fleet-disk-pressure.marker` not present at this tick
  (disk 87% < 95% threshold); the pause path correctly returned 1
  and the tick continued to the lane checks.

### Self-inflicted note (for me, not the team)

- I ran `bash -x` once during this heartbeat to confirm the log-redirect
  was being honored by the brace block at line 413. The trace went to
  my terminal, not the log; nothing leaked into
  `logs/buy31716_fleet_keep_alive.log`. (BUY-34424 lesson: `bash -x` on
  this script is safe because the brace block's `>> "$LOG" 2>&1` is
  honored — `set -x` traces to fd 2 and the brace block also redirects
  fd 2 → log via `2>&1`. Verified via strace during this tick.)
- I also sourced lines 36–131 of the script into a small bash test
  wrapper to reproduce a perceived missing-log issue. That wrapper
  wrote three lines (`===== tick`/`Line 1`/`Line 2`) to the same log
  file because `LOG` was bound to the unified Fleet LOG path; those
  test lines are now at the tail of the log and will be overwritten
  on the next clean tick. Not a behavioral issue but worth flagging
  so I don't repeat it on the next fire.

### Disposition

Closing `done`. No escalations, no restarts needed for the 6 active
lanes, the 2 sitemap miners remain intentionally stopped via markers
per the BUY-34229 lane landscape, and the dirty script modifications
(STUCK detection BUY-35267, stop-marker path, `& wait` BUY-35231
orphan-reaper safety, dual-pattern BUY-35012 for Shopper lanes) are
working as designed and should be committed as a follow-up to keep
the canonical copy aligned with the running copy.
