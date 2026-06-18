# BUY-37596 — BUY-31716 fleet keep-alive closeout (2026-06-09T10:23:44Z)

Routine execution issue for the 5-minute `BUY-31716` fleet keep-alive watchdog.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify \
  systemd/paperclip-buy31716-fleet-keep-alive.service \
  systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 30 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
```

## Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` accepted the fleet keep-alive service and timer; the only output was the known unrelated `/etc/systemd/system/hindsight.service` warning about `StartLimitIntervalSec`.
- A fresh manual keep-alive tick completed at `2026-06-09T10:23:34Z`.
- All 8 tracked lanes were healthy on that tick:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`,
  `hunt2_page`, and `stock_page`.
- Shared state advanced to `disk_last_sampled_at=2026-06-09T10:23:34Z`,
  with all recorded per-lane dead counts at `0` and `disk_use_pct=93`.

## Restart Evidence

The live keep-alive log also captured a real restart cycle earlier in this same
heartbeat window:

- `2026-06-09T10:14:27Z` `brand_sitemap_miner` detected dead and restarted as pid `2146097`
- `2026-06-09T10:14:29Z` `retailer_sitemap_miner` restarted as pid `2146225`
- `2026-06-09T10:14:31Z` `crate_deep_page` restarted as pid `2146381`
- `2026-06-09T10:14:34Z` `hunt2_page` restarted as pid `2146496`
- `2026-06-09T10:14:36Z` `stock_page` restarted as pid `2146632`
- `2026-06-09T10:15:01Z` through `2026-06-09T10:23:34Z` subsequent ticks showed all lanes healthy again

## Disposition

`BUY-37596` can close `done`: the `BUY-31716` fleet watchdog is still running
on a 5-minute cadence, it successfully restarts dead discovery lanes, and the
latest manual tick completed cleanly with all 8 lanes healthy.
