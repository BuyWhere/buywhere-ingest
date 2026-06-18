# BUY-37558 — BUY-31716 fleet keep-alive closeout (2026-06-09T10:03:04Z)

Issue scope: confirm the 5-minute `BUY-31716` fleet keep-alive still runs and preserves restart coverage for the 8 discovery lanes.

## Commands run

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 80 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
tail -n 60 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json
ps -eo pid,etimes,cmd | rg 'buy30331-sustained-loop|buy30590-brand-sitemap-miner|buy30590-retailer-sitemap-loop|buy31452-fast-wc-loop|cc-shopify-index-loop|buy30620-page-lane-runner|buy30620-(crate|hunt2|stock)-page-lane'
```

## Result

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no errors for `systemd/paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- A fresh manual keep-alive tick completed successfully at `2026-06-09T10:03:04Z` and found all 8 tracked lanes alive with no restarts.
- The log also shows the timer-driven cadence remained live on consecutive ticks at `2026-06-09T09:46:45Z`, `2026-06-09T09:51:47Z`, `2026-06-09T09:56:23Z`, and `2026-06-09T10:03:04Z`.
- Host disk pressure did not pause the watchdog on the latest tick: sampled disk usage was `93%` against the `95%` guard threshold.

## Lane status from the 2026-06-09T10:03:04Z tick

- `burst_discovery` OK `pid=670904`
- `brand_sitemap_miner` OK `pid=2316250` `heartbeat_age=8s`
- `retailer_sitemap_miner` OK `pid=2316426` `heartbeat_age=3s`
- `fast_wc_probe` OK `pid=3848747`
- `shopify_index_expansion` OK `pid=3848851`
- `crate_deep_page` OK `pid=2316670`
- `hunt2_page` OK `pid=4120587`
- `stock_page` OK `pid=2316883`

## Shared state after verification

`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`

```json
{
  "brand_sitemap_miner": 0,
  "burst_discovery": 0,
  "crate_deep_page": 0,
  "disk_last_sampled_at": "2026-06-09T10:03:04Z",
  "disk_pressure_pauses": 10,
  "disk_use_pct": "93",
  "fast_wc_probe": 0,
  "hunt2_page": 0,
  "last_disk_pressure_marker": "{\"created_at\": \"2026-06-07T21:16:42Z\", \"use_pct\": 80, \"threshold_pct\": 50, \"root\": \"/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c\", \"note\": \"write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)\"}",
  "last_disk_pressure_pause_at": "2026-06-07T21:16:42Z",
  "retailer_sitemap_miner": 0,
  "shopify_index_expansion": 0,
  "stock_page": 0
}
```

## Notes

- All per-lane dead-tick counters were `0` in the shared state after the latest tick.
- `data/buy31716-fleet-keep-alive-escalation.json` still ends with historical `2026-06-08` escalation rows; this heartbeat appended no new escalation rows.
- Live process inspection matched the expected wrapper-plus-node shape for the Oracle-owned lanes and confirmed the Shopper-owned page lanes were also present during verification.

This heartbeat satisfied the `BUY-37558` contract locally: the keep-alive watchdog ran successfully, the timer/service wiring remained valid, and all 8 `BUY-31716` discovery lanes stayed alive on the live 5-minute cadence.
