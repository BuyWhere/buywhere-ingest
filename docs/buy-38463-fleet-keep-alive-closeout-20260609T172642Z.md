# BUY-38463 — BUY-31716 fleet keep-alive closeout (2026-06-09T17:26:42Z)

Routine execution issue for the 5-minute `BUY-31716` fleet keep-alive watchdog covering the 8 discovery lanes.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh
tail -n 80 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,240p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
jq '.events | length as $n | {count:$n,last:(if $n>0 then .[$n-1] else null end)}' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json
```

## Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no verification errors for `paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still enforces the watchdog cadence with `OnUnitActiveSec=5min` and `Persistent=true`.
- A fresh manual watchdog run completed successfully and appended a clean tick at `2026-06-09T17:26:27Z`.
- The shared state file advanced `disk_last_sampled_at` to `2026-06-09T17:26:27Z`, recorded `disk_use_pct` at `90`, and preserved `0` dead counts for all tracked lanes: `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` remained intentionally skipped because their stop markers were present; the watchdog logged both as stopped/skipped rather than dead.
- The log captured a real restart path for `burst_discovery` at `2026-06-09T17:21:37Z`, then a healthy follow-up tick at `2026-06-09T17:22:02Z` and another healthy tick at `2026-06-09T17:26:27Z`.
- `data/buy31716-fleet-keep-alive-escalation.json` still has `0` events, so this heartbeat appended no new escalation entry.

## Log Excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T17:21:37Z =====
[2026-06-09T17:21:37Z] host disk use=87% (threshold=95%, recover=90%)
[2026-06-09T17:21:37Z] burst_discovery DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T17:21:39Z] burst_discovery restarted pid=3782962 (spawned=3782959)
...
===== BUY-31716 fleet keep-alive tick 2026-06-09T17:26:27Z =====
[2026-06-09T17:26:27Z] burst_discovery OK pid=3782962 (no_heartbeat_file)
[2026-06-09T17:26:27Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T17:26:27Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T17:26:27Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T17:26:27Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T17:26:27Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T17:26:27Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T17:26:27Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T17:26:27Z] keep-alive tick complete
```

This heartbeat satisfied the `BUY-38463` execution contract: the live `BUY-31716` fleet watchdog ran, recovered a dead lane, and left fresh shared state and log evidence showing the 8-lane keep-alive remains healthy.
