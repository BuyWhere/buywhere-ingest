# BUY-37567 — BUY-31716 fleet keep-alive closeout (2026-06-09T10:15:02Z)

Issue scope: confirm the 5-minute `BUY-31716` fleet keep-alive still restarts dead processes across the 8 discovery lanes.

## Commands run

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 30 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
```

## Result

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no errors for `systemd/paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- The timer/service wiring still targets the canonical watchdog script on a 5-minute cadence.
- A manual keep-alive tick at `2026-06-09T10:14:27Z` exercised the restart path and relaunched 5 dead lanes: `brand_sitemap_miner`, `retailer_sitemap_miner`, `crate_deep_page`, `hunt2_page`, and `stock_page`.
- An immediate follow-up tick at `2026-06-09T10:15:01Z` showed all 8 lanes healthy after those restarts, proving the fleet recovered within one additional keep-alive pass.

## Restart evidence

From `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`:

- `2026-06-09T10:14:27Z` `brand_sitemap_miner DEAD` -> restarted as pid `2146097`
- `2026-06-09T10:14:29Z` `retailer_sitemap_miner DEAD` -> restarted as pid `2146225`
- `2026-06-09T10:14:31Z` `crate_deep_page DEAD` -> restarted as pid `2146381`
- `2026-06-09T10:14:34Z` `hunt2_page DEAD` -> restarted as pid `2146496`
- `2026-06-09T10:14:36Z` `stock_page DEAD` -> restarted as pid `2146632`

## Healthy fleet on the follow-up tick

- `burst_discovery` OK `pid=2139271`
- `brand_sitemap_miner` OK `pid=2146097` `heartbeat_age=4s`
- `retailer_sitemap_miner` OK `pid=2146225` `heartbeat_age=2s`
- `fast_wc_probe` OK `pid=3848747`
- `shopify_index_expansion` OK `pid=3848851`
- `crate_deep_page` OK `pid=2146381`
- `hunt2_page` OK `pid=2146496`
- `stock_page` OK `pid=2146632`

## Shared state after verification

`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`

```json
{
  "brand_sitemap_miner": 0,
  "burst_discovery": 0,
  "crate_deep_page": 0,
  "disk_last_sampled_at": "2026-06-09T10:15:01Z",
  "disk_pressure_pauses": 10,
  "disk_use_pct": "92",
  "fast_wc_probe": 0,
  "hunt2_page": 0,
  "last_disk_pressure_marker": "{\"created_at\": \"2026-06-07T21:16:42Z\", \"use_pct\": 80, \"threshold_pct\": 50, \"root\": \"/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c\", \"note\": \"write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)\"}",
  "last_disk_pressure_pause_at": "2026-06-07T21:16:42Z",
  "retailer_sitemap_miner": 0,
  "shopify_index_expansion": 0,
  "stock_page": 0
}
```

This heartbeat satisfied `BUY-37567`: the 5-minute fleet keep-alive remained wired correctly, the restart path fired on real dead lanes, and the next verification pass confirmed all 8 `BUY-31716` lanes healthy.
