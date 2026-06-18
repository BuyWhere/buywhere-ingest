# BUY-38027 — BUY-31716 fleet keep-alive closeout (2026-06-09T13:46:48Z)

Routine execution issue for the 5-minute `BUY-31716` discovery-fleet watchdog.

## What I ran

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
bash scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,240p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
ps -eo pid,etimes,cmd | rg "buy30331-sustained-loop|buy30590-brand-sitemap-miner|buy30590-retailer-sitemap-loop|buy31452-fast-wc-loop|cc-shopify-index-loop|buy30620-(crate-deep-page|hunt2-page|stock-page)-lane"
```

## Result

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- A fresh manual keep-alive tick completed successfully at `2026-06-09T13:46:38Z`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no verification errors for `paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still enforces the expected cadence with `OnUnitActiveSec=5min` and `Persistent=true`.
- Shared fleet state advanced `disk_last_sampled_at` to `2026-06-09T13:46:38Z`, kept `disk_use_pct=80`, retained `disk_pressure_pauses=15`, and left all tracked per-lane dead counts at `0`.
- Six active lanes were healthy on this tick:
  - `burst_discovery` pid `2775043`
  - `fast_wc_probe` pid `3848747`
  - `shopify_index_expansion` pid `3848851`
  - `crate_deep_page` pid `2146381`
  - `hunt2_page` pid `2146496`
  - `stock_page` pid `2146632`
- The remaining two lanes were intentionally skipped rather than dead:
  - `brand_sitemap_miner` remained suppressed by `data/buy30590-brand-sitemap-miner.stopped`
  - `retailer_sitemap_miner` remained suppressed by `data/buy30590-retailer-sitemap-loop.stopped`

## Fresh log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T13:46:38Z =====
[2026-06-09T13:46:38Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T13:46:38Z] host disk use=80% (threshold=95%, recover=90%)
[2026-06-09T13:46:38Z] burst_discovery OK pid=2775043 (no_heartbeat_file)
[2026-06-09T13:46:39Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T13:46:39Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T13:46:39Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T13:46:39Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T13:46:39Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T13:46:39Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T13:46:39Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T13:46:39Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T13:46:39Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T13:46:39Z] keep-alive tick complete
```

## Disposition

`BUY-38027` can close `done`: the 5-minute watchdog fired successfully in this heartbeat, the shared fleet state is clean, the six active BUY-31716 lanes were alive, and the only non-running lanes are the two explicitly stop-marked miners rather than keep-alive misses.
