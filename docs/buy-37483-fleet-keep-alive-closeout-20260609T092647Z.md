# BUY-37483 — BUY-31716 fleet keep-alive closeout (2026-06-09T09:26:47Z)

Fresh verification for the 5-minute BUY-31716 fleet keep-alive watchdog.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
```

## Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning and no error for `systemd/paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- A fresh manual keep-alive tick completed at `2026-06-09T09:26:47Z`.
- All 8 tracked lanes were healthy on that tick:
  - `burst_discovery`
  - `brand_sitemap_miner`
  - `retailer_sitemap_miner`
  - `fast_wc_probe`
  - `shopify_index_expansion`
  - `crate_deep_page`
  - `hunt2_page`
  - `stock_page`
- Shared state advanced to `disk_last_sampled_at=2026-06-09T09:21:26Z` before the manual tick and then the file mtime advanced to `2026-06-09 09:26:47 +0000`; all per-lane dead counts remained `0`.
- Current disk sample stayed below the guard threshold at `disk_use_pct=93`.
- No new escalation entry was appended during this heartbeat.

## Fresh log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T09:26:47Z =====
[2026-06-09T09:26:47Z] host disk use=93% (threshold=95%, recover=90%)
[2026-06-09T09:26:47Z] burst_discovery OK pid=670904 (no_heartbeat_file)
[2026-06-09T09:26:47Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=21s
[2026-06-09T09:26:47Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=21s
[2026-06-09T09:26:47Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T09:26:47Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T09:26:47Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-09T09:26:47Z] hunt2_page OK pid=4120587 (no_heartbeat_file)
[2026-06-09T09:26:47Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-09T09:26:47Z] keep-alive tick complete
```
