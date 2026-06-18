# BUY-37790 — BUY-31716 fleet keep-alive closeout (2026-06-09T14:16:30Z)

Issue scope: re-check the prior disk-pressure blocker on the `BUY-31716`
5-minute fleet keep-alive, verify whether the watchdog has resumed normal
operation, and leave the execution issue in the correct final state.

## Commands

```bash
df -h /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
tail -n 60 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,240p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
stat -c '%y %n' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-brand-sitemap-miner.stopped /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-retailer-sitemap-loop.stopped
```

## Findings

- The prior disk-pressure blocker has cleared:
  - `df -h` now shows `/` at `82%` usage.
  - `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-disk-pressure.marker`
    is absent.
- The fleet watchdog resumed normal ticks after recovery. Recent log blocks at
  `2026-06-09T13:51:29Z`, `2026-06-09T13:56:37Z`, `2026-06-09T14:04:09Z`, and
  `2026-06-09T14:06:57Z` all ran the normal liveness path instead of the
  disk-pressure pause path.
- Shared state confirms the recovery:
  - `disk_last_sampled_at=2026-06-09T14:06:57Z`
  - `disk_use_pct=80`
  - `last_disk_pressure_pause_at=2026-06-09T12:23:28Z`
- The fleet is currently in the expected steady state for this routine:
  - `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`,
    `crate_deep_page`, `hunt2_page`, and `stock_page` all logged `OK`.
  - `brand_sitemap_miner` and `retailer_sitemap_miner` were not treated as
    dead; the watchdog explicitly held them in `STOPPED/SKIPPED` state because
    the Oracle-workspace stop markers are present.
- The stop markers still exist and were last updated at
  `2026-06-09 12:30:04.492144303 +0000`:
  - `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-brand-sitemap-miner.stopped`
  - `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-retailer-sitemap-loop.stopped`

## Disposition

`BUY-37790` can close `done`: the temporary disk-pressure blocker from the
previous heartbeat has cleared, the 5-minute fleet watchdog has resumed normal
operation, and the current lane state matches the watchdog's intended behavior,
including explicit suppression of the two stop-marked sitemap lanes.
