# BUY-38452 — BUY-31716 fleet keep-alive closeout (2026-06-09T17:22:03Z)

Wake scope: verify the active `BUY-31716` fleet keep-alive still enforces the
5-minute restart path for the 8 discovery lanes and leave a final disposition on
`BUY-38452`.

## What was verified

- `scripts/buy31716-fleet-keep-alive.sh` remains the active watchdog entrypoint.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` still executes that
  script from this checkout.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still uses
  `OnUnitActiveSec=5min` with `Persistent=true`.
- Two live watchdog ticks completed during this heartbeat at
  `2026-06-09T17:21:37Z` and `2026-06-09T17:22:02Z`.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json
stat -c '%y %n' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-brand-sitemap-miner.stopped /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-retailer-sitemap-loop.stopped
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service:14`; the fleet keep-alive unit and
  timer had no verification errors.
- The first live tick at `2026-06-09T17:21:37Z` caught `burst_discovery` dead,
  restarted it immediately, and logged `burst_discovery restarted pid=3782962
  (spawned=3782959)`.
- The second live tick at `2026-06-09T17:22:02Z` confirmed the restarted
  `burst_discovery` process healthy as `pid=3782962`.
- Both ticks saw the rest of the active lanes healthy:
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`,
  and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were intentionally skipped
  because their stop markers remain present in the Oracle workspace, both last
  updated at `2026-06-09 12:30:04.492144303 +0000`.
- The shared state file at
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
  advanced `disk_last_sampled_at` to `2026-06-09T17:22:02Z`, kept
  `disk_use_pct` at `87`, and reset every tracked lane counter to `0` after the
  restart verification tick.
- The escalation file still ends with the historical `2026-06-08T05:51:52Z`
  `shopify_index_expansion` entry; this heartbeat appended no new escalation.

## Conclusion

`BUY-38452` can close `done`. The `BUY-31716` fleet watchdog is still wired to
its 5-minute cadence, proved it can restart a dead lane during this heartbeat,
and then confirmed the recovered lane healthy on the immediate follow-up tick.
