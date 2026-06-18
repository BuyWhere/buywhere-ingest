# BUY-38569 fleet keep-alive closeout

- Issue: [BUY-38569](/BUY/issues/BUY-38569)
- Parent: [BUY-31716](/BUY/issues/BUY-31716)
- Verified at: `2026-06-09T18:31:26Z`

## What I checked

- `bash -n scripts/buy31716-fleet-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer`
- Manual tick: `WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh`
- Shared state: `data/buy31716-fleet-keep-alive-state.json`
- Escalation ledger: `data/buy31716-fleet-keep-alive-escalation.json`
- Runtime log: `logs/buy31716_fleet_keep_alive.log`
- Live process check: `pgrep -af 'buy30331-sustained-loop.mjs|buy30590-brand-sitemap-miner.mjs|buy30590-retailer-sitemap-loop.mjs|buy31452-fast-wc-loop.mjs|cc-shopify-index-loop.mjs|buy30620-page-lane-runner.mjs.*--role=crate|buy30620-crate-deep-page-lane.mjs|buy30620-page-lane-runner.mjs.*--role=hunt2|buy30620-hunt2-page-lane.mjs|buy30620-page-lane-runner.mjs.*--role=stock|buy30620-stock-page-lane.mjs'`

## Results

- Script syntax check passed.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning; no error was reported for the BUY-31716 keep-alive service or timer.
- The fresh keep-alive tick completed at `2026-06-09T18:31:00Z` after starting at `2026-06-09T18:30:59Z`.
- Healthy lanes on this tick:
  - `burst_discovery` pid `3782962`
  - `fast_wc_probe` pid `3848747`
  - `shopify_index_expansion` pid `3848851`
  - `crate_deep_page` pid `2146381`
  - `hunt2_page` pid `2146496`
  - `stock_page` pid `2146632`
- Intentionally stopped and skipped lanes on this tick:
  - `brand_sitemap_miner`, via `data/buy30590-brand-sitemap-miner.stopped`
    containing `BUY-34200: stop external maglev-proxy-based brand sitemap miner.`
  - `retailer_sitemap_miner`, via `data/buy30590-retailer-sitemap-loop.stopped`
    containing `BUY-34200: stop external maglev-proxy-based retailer sitemap loop.`
- Shared keep-alive state advanced to `disk_last_sampled_at=2026-06-09T18:30:59Z` with `disk_use_pct=89` and `disk_pressure_pauses=15`.
- All tracked per-lane dead counts remained `0`.
- No new escalation entry was appended; the escalation ledger remained at 30 historical entries, with the last one still from `2026-06-08T05:51:52Z`.

## Tick excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T18:30:59Z =====
[2026-06-09T18:30:59Z] host disk use=89% (threshold=95%, recover=90%)
[2026-06-09T18:30:59Z] burst_discovery OK pid=3782962 (no_heartbeat_file)
[2026-06-09T18:31:00Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T18:31:00Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T18:31:00Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T18:31:00Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T18:31:00Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T18:31:00Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T18:31:00Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T18:31:00Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T18:31:00Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T18:31:00Z] keep-alive tick complete
```

## Conclusion

The 5-minute BUY-31716 fleet keep-alive path remains operational. Six discovery
lanes were live on this heartbeat, and the two sitemap lanes were intentionally
kept stopped under the existing `BUY-34200` marker policy.
