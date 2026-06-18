# BUY-37860 — BUY-31716 fleet keep-alive closeout (2026-06-09T12:27:16Z)

Routine execution closeout for the 5-minute `BUY-31716` fleet keep-alive watchdog.

## Scope

- Verified the active watchdog entrypoint at `scripts/buy31716-fleet-keep-alive.sh`.
- Verified the 5-minute timer configuration in `systemd/paperclip-buy31716-fleet-keep-alive.timer`.
- Executed the watchdog manually twice: first to observe the live tick and restart behavior, then to confirm the restarted lanes recovered cleanly.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 30 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,260p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
ps -eo pid,etimes,cmd | rg "buy30331-sustained-loop|buy30590-brand-sitemap-miner|buy30590-retailer-sitemap-loop|buy31452-fast-wc-loop|cc-shopify-index-loop|buy30620-(crate-deep-page|hunt2-page|stock-page)-lane"
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning about `StartLimitIntervalSec`; there were no keep-alive unit or timer errors.
- The first manual tick at `2026-06-09T12:26:39Z` detected `brand_sitemap_miner` and `retailer_sitemap_miner` as dead and restarted both lanes successfully.
- The second manual tick at `2026-06-09T12:27:15Z` confirmed all eight lanes healthy, with fresh heartbeat ages of `6s` for `brand_sitemap_miner` and `4s` for `retailer_sitemap_miner`.
- Shared state advanced to `disk_last_sampled_at=2026-06-09T12:27:15Z`, `disk_use_pct=81`, `disk_pressure_pauses=15`, and zero dead counts for all tracked lanes.
- The earlier disk-pressure marker cleared during the routine path at `2026-06-09T12:23:28Z` once host disk use recovered below the `90%` clear threshold.

## Lane Snapshot

| Lane | Evidence |
| --- | --- |
| `burst_discovery` | OK `pid=2139271` |
| `brand_sitemap_miner` | Restarted on first pass, then OK `pid=2751329`, heartbeat age `6s` |
| `retailer_sitemap_miner` | Restarted on first pass, then OK `pid=2751709`, heartbeat age `4s` |
| `fast_wc_probe` | OK `pid=3848747` |
| `shopify_index_expansion` | OK `pid=3848851` |
| `crate_deep_page` | OK `pid=2146381` |
| `hunt2_page` | OK `pid=2146496` |
| `stock_page` | OK `pid=2146632` |

## Log Excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T12:26:39Z =====
[2026-06-09T12:26:39Z] host disk use=81% (threshold=95%, recover=90%)
[2026-06-09T12:26:39Z] burst_discovery OK pid=2139271 (no_heartbeat_file)
[2026-06-09T12:26:39Z] brand_sitemap_miner DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T12:26:41Z] brand_sitemap_miner restarted pid=2751329 (spawned=2751327)
[2026-06-09T12:26:41Z] retailer_sitemap_miner DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T12:26:43Z] retailer_sitemap_miner restarted pid=2751709 (spawned=2751707)
[2026-06-09T12:26:44Z] keep-alive tick complete
===== BUY-31716 fleet keep-alive tick 2026-06-09T12:27:15Z =====
[2026-06-09T12:27:15Z] burst_discovery OK pid=2139271 (no_heartbeat_file)
[2026-06-09T12:27:15Z] brand_sitemap_miner OK pid=2751329 heartbeat_age=6s
[2026-06-09T12:27:15Z] retailer_sitemap_miner OK pid=2751709 heartbeat_age=4s
[2026-06-09T12:27:16Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T12:27:16Z] keep-alive tick complete
```

This routine execution completed successfully. No code change was required in this heartbeat because the watchdog already recovered the dead lanes as designed.
