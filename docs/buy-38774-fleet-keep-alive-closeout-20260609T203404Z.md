# BUY-38774 fleet keep-alive closeout

- Verified the active `BUY-31716` fleet keep-alive still runs `scripts/buy31716-fleet-keep-alive.sh` via `systemd/paperclip-buy31716-fleet-keep-alive.service`.
- Verified `systemd/paperclip-buy31716-fleet-keep-alive.timer` still enforces the 5-minute cadence with `OnUnitActiveSec=5min` and `Persistent=true`.

### Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
```

### Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no unit errors for `paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- A fresh manual keep-alive tick completed at `2026-06-09T20:34:04Z`.
- Healthy live lanes on that tick remained `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` remained intentionally skipped because their stop markers are present:
  - `data/buy30590-brand-sitemap-miner.stopped`
  - `data/buy30590-retailer-sitemap-loop.stopped`
- Shared state at `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json` advanced `disk_last_sampled_at` to `2026-06-09T20:34:04Z`, kept all per-lane dead counts at `0`, recorded `disk_use_pct` `89`, and left `disk_pressure_pauses` at `15`.
- The escalation file gained no new entry in this heartbeat; it still ends with the older `2026-06-08T05:51:52Z` `shopify_index_expansion` escalation.
