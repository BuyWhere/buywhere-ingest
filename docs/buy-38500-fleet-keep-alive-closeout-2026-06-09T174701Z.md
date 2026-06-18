# BUY-38500 — BUY-31716 fleet keep-alive closeout (2026-06-09T17:47:01Z)

Wake scope: verify the active `BUY-31716` fleet keep-alive still enforces the
5-minute restart path for the 8 discovery lanes and leave a final disposition on
`BUY-38500`.

## What was verified

- `scripts/buy31716-fleet-keep-alive.sh` is still the active watchdog entrypoint.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` still executes that
  script from this checkout.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still uses
  `OnUnitActiveSec=5min`.
- A live watchdog tick completed at `2026-06-09T17:46:43Z`.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 80 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service:14`; no errors were reported for the
  fleet keep-alive unit or timer.
- The latest log block shows the expected 5-minute cadence leading into the
  manual execution, with ticks at `2026-06-09T17:26:27Z`, `17:31:30Z`,
  `17:36:25Z`, `17:41:34Z`, and `17:46:43Z`.
- The latest tick saw these lanes alive: `burst_discovery`, `fast_wc_probe`,
  `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were intentionally skipped
  because their stop markers remain present:
  `data/buy30590-brand-sitemap-miner.stopped` and
  `data/buy30590-retailer-sitemap-loop.stopped`.
- The state file at
  `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
  now shows all tracked per-lane dead counters at `0`, with
  `disk_last_sampled_at`=`2026-06-09T17:46:43Z`, `disk_use_pct`=`89`, and
  `disk_pressure_pauses`=`15`.
- The escalation file still ends at the historical
  `2026-06-08T05:51:52Z` `shopify_index_expansion` escalation; no new
  escalation was appended by this heartbeat.

## Conclusion

`BUY-38500` can close `done`. The `BUY-31716` fleet watchdog remains wired to a
real 5-minute cadence, completed a fresh tick during this heartbeat, and
currently observes every active lane as healthy while preserving the intentional
stop-marker skips.
