# BUY-38103 — BUY-31716 fleet keep-alive closeout (2026-06-09T14:22:08Z)

Routine execution closeout for the 5-minute `BUY-31716` discovery-fleet watchdog.

## What I verified

- `scripts/buy31716-fleet-keep-alive.sh` is still the live watchdog entrypoint.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still enforces the 5-minute cadence with `OnUnitActiveSec=5min` and `Persistent=true`.
- A fresh runtime tick completed in the active Oracle workspace and advanced the shared fleet state.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 80 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
ls -l /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-brand-sitemap-miner.stopped /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-retailer-sitemap-loop.stopped
```

## Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning; the `BUY-31716` keep-alive service and timer had no verification errors.
- A fresh watchdog tick completed at `2026-06-09T14:21:34Z` through `2026-06-09T14:21:35Z`.
- Shared fleet state advanced `disk_last_sampled_at` to `2026-06-09T14:21:34Z`, updated `disk_use_pct` to `82`, retained `disk_pressure_pauses=15`, and kept all tracked per-lane dead counts at `0`.
- The watchdog found six currently active lanes healthy on this tick:
  - `burst_discovery` pid `3131982`
  - `fast_wc_probe` pid `3848747`
  - `shopify_index_expansion` pid `3848851`
  - `crate_deep_page` pid `2146381`
  - `hunt2_page` pid `2146496`
  - `stock_page` pid `2146632`
- The remaining two lanes were intentionally suppressed rather than dead:
  - `brand_sitemap_miner` was `STOPPED` and `SKIPPED` because `data/buy30590-brand-sitemap-miner.stopped` exists with mtime `2026-06-09 12:30 UTC`
  - `retailer_sitemap_miner` was `STOPPED` and `SKIPPED` because `data/buy30590-retailer-sitemap-loop.stopped` exists with mtime `2026-06-09 12:30 UTC`
- During this heartbeat the watchdog also cleaned up duplicate `burst_discovery` loop processes at `2026-06-09T14:06:57Z`, keeping pid `3103443` and killing stale duplicates before the later healthy tick moved to pid `3131982`.

## Fresh log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T14:21:34Z =====
[2026-06-09T14:21:34Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T14:21:34Z] host disk use=82% (threshold=95%, recover=90%)
[2026-06-09T14:21:34Z] burst_discovery OK pid=3131982 (no_heartbeat_file)
[2026-06-09T14:21:34Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T14:21:34Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T14:21:34Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T14:21:34Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T14:21:34Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T14:21:34Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T14:21:34Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T14:21:35Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T14:21:35Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T14:21:35Z] keep-alive tick complete
```

## Disposition

`BUY-38103` can close `done`: the `BUY-31716` fleet keep-alive remains on its 5-minute restart path, the shared state and timer wiring are healthy, and the only non-running lanes are the two intentionally stop-marked `BUY-34200` lanes rather than watchdog misses.
