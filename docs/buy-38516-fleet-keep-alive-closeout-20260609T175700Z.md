# BUY-38516 — BUY-31716 fleet keep-alive closeout (2026-06-09T17:57Z)

Issue scope: verify the `BUY-31716` fleet keep-alive still enforces the 5-minute
restart path for the 8-lane discovery fleet, capture fresh live evidence, and
close this execution issue if the watchdog remains healthy.

## Verification run

Commands executed in this heartbeat:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
ps -eo pid,etimes,args | rg "buy30331-sustained-loop|buy30590-brand-sitemap-miner|buy30590-retailer-sitemap-loop|buy31452-fast-wc-loop|cc-shopify-index-loop|buy30620-(crate-deep-page-lane|hunt2-page-lane|stock-page-lane)" -N
tail -n 30 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
```

## Findings

- `bash -n scripts/buy31716-fleet-keep-alive.sh` passed.
- `systemd-analyze verify` reported only the known unrelated warning for
  `/etc/systemd/system/hindsight.service`; there were no errors for
  `systemd/paperclip-buy31716-fleet-keep-alive.service` or
  `systemd/paperclip-buy31716-fleet-keep-alive.timer`.
- A fresh manual keep-alive tick completed at `2026-06-09T17:56:51Z` in the
  live Oracle workspace log. The previous fresh manual tick from this heartbeat
  completed at `2026-06-09T17:56:43Z`.
- Six active lanes were healthy on the fresh tick:
  `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`,
  `crate_deep_page`, `hunt2_page`, and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were not treated as dead;
  both were intentionally skipped because their stop markers were present:
  `data/buy30590-brand-sitemap-miner.stopped` and
  `data/buy30590-retailer-sitemap-loop.stopped`.
- The direct process snapshot matched the log: one active Node process per live
  lane, with long-lived runtimes for the three Shopper-owned lanes and the
  Oracle-owned `burst_discovery`, `fast_wc_probe`, and
  `shopify_index_expansion` loops.
- Shared state advanced to `disk_last_sampled_at=2026-06-09T17:56:51Z`, all
  tracked per-lane dead counters remained `0`, `disk_use_pct` dropped to `88`,
  and `disk_pressure_pauses` remained `15`.
- `data/buy31716-fleet-keep-alive-escalation.json` gained no new escalation
  entry in this heartbeat.

Latest log block:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T17:56:51Z =====
[2026-06-09T17:56:51Z] host disk use=88% (threshold=95%, recover=90%)
[2026-06-09T17:56:51Z] burst_discovery OK pid=3782962 (no_heartbeat_file)
[2026-06-09T17:56:51Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T17:56:51Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T17:56:51Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T17:56:51Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T17:56:51Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T17:56:51Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T17:56:51Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T17:56:51Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T17:56:51Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T17:56:51Z] keep-alive tick complete
```

## Disposition

`BUY-38516` can close `done`: the `BUY-31716` fleet watchdog still runs on the
intended 5-minute cadence, the live restart/health-check path executed in this
heartbeat, the two intentionally stopped sitemap lanes remained skipped instead
of flapping as dead, and all tracked fleet dead counters remained reset.
