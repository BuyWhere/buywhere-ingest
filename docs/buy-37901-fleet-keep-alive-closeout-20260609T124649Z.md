# BUY-37901 — BUY-31716 fleet keep-alive closeout (2026-06-09T12:46:49Z)

Routine execution issue for the 5-minute `BUY-31716` discovery-fleet watchdog.

## What I ran

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
```

## Result

- Shell syntax check passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; no errors were reported for the `paperclip-buy31716-fleet-keep-alive` service or timer units.
- A fresh keep-alive tick completed successfully at `2026-06-09T12:46:49Z`.
- Live fleet state in `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json` updated `disk_last_sampled_at` to `2026-06-09T12:46:49Z` and `disk_use_pct` to `79`.
- The active discovery lanes were all observed alive on this tick:
  - `burst_discovery` pid `2775043`
  - `fast_wc_probe` pid `3848747`
  - `shopify_index_expansion` pid `3848851`
  - `crate_deep_page` pid `2146381`
  - `hunt2_page` pid `2146496`
  - `stock_page` pid `2146632`
- `brand_sitemap_miner` and `retailer_sitemap_miner` were intentionally not restarted because their stop-marker files are still present:
  - `data/buy30590-brand-sitemap-miner.stopped`
  - `data/buy30590-retailer-sitemap-loop.stopped`

## Fresh log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T12:46:49Z =====
[2026-06-09T12:46:49Z] host disk use=79% (threshold=95%, recover=90%)
[2026-06-09T12:46:49Z] burst_discovery OK pid=2775043 (no_heartbeat_file)
[2026-06-09T12:46:49Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T12:46:49Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T12:46:49Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T12:46:49Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T12:46:49Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T12:46:49Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T12:46:49Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T12:46:49Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T12:46:49Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T12:46:49Z] keep-alive tick complete
```
