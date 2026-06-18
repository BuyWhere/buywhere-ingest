# BUY-37968 — BUY-31716 fleet keep-alive closeout (2026-06-09T13:17:13Z)

Routine execution issue for the 5-minute `BUY-31716` discovery-fleet watchdog.

## What I ran

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 30 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,220p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
stat -c '%y %n' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-brand-sitemap-miner.stopped /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-retailer-sitemap-loop.stopped
```

## Result

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no errors for `paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- A fresh manual keep-alive tick completed successfully at `2026-06-09T13:16:58Z`.
- The disk-pressure guard is no longer blocking the watchdog in this heartbeat:
  - host disk sample during the tick was `80%`
  - `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-disk-pressure.marker` was absent after the run
- Shared fleet state advanced `disk_last_sampled_at` to `2026-06-09T13:16:58Z`, kept `disk_pressure_pauses=15`, and left all tracked per-lane dead counts at `0`.
- The watchdog observed all active, non-suppressed lanes alive on this tick:
  - `burst_discovery` pid `2775043`
  - `fast_wc_probe` pid `3848747`
  - `shopify_index_expansion` pid `3848851`
  - `crate_deep_page` pid `2146381`
  - `hunt2_page` pid `2146496`
  - `stock_page` pid `2146632`
- The remaining two lanes are intentionally suppressed, not dead:
  - `brand_sitemap_miner` was skipped because `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-brand-sitemap-miner.stopped` exists and was last updated at `2026-06-09 12:30:04.492144303 +0000`
  - `retailer_sitemap_miner` was skipped because `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-retailer-sitemap-loop.stopped` exists and was last updated at `2026-06-09 12:30:04.492144303 +0000`
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still enforces the 5-minute cadence via `OnUnitActiveSec=5min` with `Persistent=true`.

## Fresh log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T13:16:58Z =====
[2026-06-09T13:16:58Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T13:16:58Z] host disk use=80% (threshold=95%, recover=90%)
[2026-06-09T13:16:58Z] burst_discovery OK pid=2775043 (no_heartbeat_file)
[2026-06-09T13:16:58Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T13:16:58Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T13:16:58Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T13:16:58Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T13:16:58Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T13:16:58Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T13:16:58Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T13:16:58Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T13:16:58Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T13:16:58Z] keep-alive tick complete
```

## Disposition

`BUY-37968` can close `done`: the fleet keep-alive is back on its normal restart path after the earlier disk-pressure pause cleared, the 5-minute systemd cadence remains intact, and the only non-running lanes are the two explicitly stop-marked ones rather than unhandled watchdog failures.
