# BUY-38009 — BUY-31716 fleet keep-alive closeout (2026-06-09T13:36:49Z)

Routine execution issue for the 5-minute `BUY-31716` discovery-fleet watchdog.

## What I verified

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
ps -eo pid,etimes,cmd | rg "buy30331-sustained-loop|buy30590-brand-sitemap-miner|buy30590-retailer-sitemap-loop|buy31452-fast-wc-loop|cc-shopify-index-loop|buy30620-(crate-deep-page|hunt2-page|stock-page)-lane|buy30620-page-lane-runner"
```

## Result

- The 5-minute watchdog timer fired again during this heartbeat at `2026-06-09T13:31:31Z`, so this execution issue has fresh live-host evidence from the current run window.
- `bash -n scripts/buy31716-fleet-keep-alive.sh` passed.
- `systemd-analyze verify` emitted only the known unrelated host warning from `/etc/systemd/system/hindsight.service`; there were no verification errors for `paperclip-buy31716-fleet-keep-alive.service` or `paperclip-buy31716-fleet-keep-alive.timer`.
- The shared fleet state advanced `disk_last_sampled_at` to `2026-06-09T13:31:31Z`, kept `disk_use_pct=80`, retained `disk_pressure_pauses=15`, and left every tracked per-lane dead count at `0`.
- The active discovery lanes were healthy on the fresh tick:
  - `burst_discovery` pid `2775043`
  - `fast_wc_probe` pid `3848747`
  - `shopify_index_expansion` pid `3848851`
  - `crate_deep_page` pid `2146381`
  - `hunt2_page` pid `2146496`
  - `stock_page` pid `2146632`
- The two remaining lanes were intentionally suppressed, not watchdog misses:
  - `brand_sitemap_miner` skipped because `data/buy30590-brand-sitemap-miner.stopped` exists
  - `retailer_sitemap_miner` skipped because `data/buy30590-retailer-sitemap-loop.stopped` exists
- The active process list still shows the orphan-reaper-safe parent shape (`bash -c ... & wait` plus child `node`) for the restarted lane families, which is the core durability fix behind the 5-minute keep-alive path.

## Fresh log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T13:31:31Z =====
[2026-06-09T13:31:31Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T13:31:31Z] host disk use=80% (threshold=95%, recover=90%)
[2026-06-09T13:31:31Z] burst_discovery OK pid=2775043 (no_heartbeat_file)
[2026-06-09T13:31:31Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T13:31:31Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T13:31:31Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T13:31:31Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T13:31:31Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T13:31:31Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T13:31:31Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T13:31:31Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T13:31:31Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T13:31:31Z] keep-alive tick complete
```

## Disposition

`BUY-38009` can close `done`: the 5-minute restart path for the eight-lane [BUY-31716](/BUY/issues/BUY-31716) fleet is live, the six active lanes are healthy on the latest tick, and the two inactive lanes are explicitly stop-marked rather than silently dead.
