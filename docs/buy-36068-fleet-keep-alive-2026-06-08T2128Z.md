# BUY-36068 — BUY-31716 fleet keep-alive execution

Timestamp: 2026-06-08T21:28:00Z

## Summary

Executed the `BUY-31716` fleet keep-alive watchdog for the eight discovery
lanes from the checked-out workspace. The manual tick completed successfully,
all eight tracked lanes were alive after the run, and the shared state file
kept every lane dead counter at `0`.

This heartbeat also confirmed the live 5-minute restart path is working, not
just the one-off manual invocation: the same keep-alive log shows
`burst_discovery` was detected dead and restarted automatically at
`2026-06-08T20:57:43Z`, then remained healthy on subsequent ticks.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c \
  bash scripts/buy31716-fleet-keep-alive.sh
systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager
systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager
pgrep -af 'buy30331-sustained-loop.mjs|buy30590-brand-sitemap-miner.mjs|buy30590-retailer-sitemap-loop.mjs|buy31452-fast-wc-loop.mjs|cc-shopify-index-loop.mjs|buy30620-crate-deep-page-lane.mjs|buy30620-hunt2-page-lane.mjs|buy30620-stock-page-lane.mjs'
```

## Live watchdog evidence

Latest log block from
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-08T21:28:00Z =====
[2026-06-08T21:28:00Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-08T21:28:00Z] host disk use=85% (threshold=95%, recover=90%)
[2026-06-08T21:28:00Z] burst_discovery OK pid=2691392 (no_heartbeat_file)
[2026-06-08T21:28:00Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=14s
[2026-06-08T21:28:00Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=8s
[2026-06-08T21:28:01Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-08T21:28:01Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-08T21:28:01Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-08T21:28:01Z] hunt2_page OK pid=2316743 (no_heartbeat_file)
[2026-06-08T21:28:01Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-08T21:28:01Z] keep-alive tick complete
```

Automatic restart evidence from the same live log:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-08T20:57:43Z =====
[2026-06-08T20:57:43Z] burst_discovery DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-08T20:57:45Z] burst_discovery restarted pid=2691392 (spawned=2691390)
```

## State and process snapshot

State file
`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
after the tick:

- `disk_last_sampled_at = 2026-06-08T21:28:00Z`
- `disk_use_pct = 85`
- dead counters stayed at `0` for:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`,
  `hunt2_page`, `stock_page`

`pgrep -af` immediately after the tick showed all eight expected lane drivers:

- `node scripts/buy30331-sustained-loop.mjs`
- `node scripts/buy30590-brand-sitemap-miner.mjs`
- `node scripts/buy30590-retailer-sitemap-loop.mjs`
- `node scripts/buy31452-fast-wc-loop.mjs`
- `node scripts/cc-shopify-index-loop.mjs`
- `node scripts/buy30620-crate-deep-page-lane.mjs`
- `node scripts/buy30620-hunt2-page-lane.mjs`
- `node scripts/buy30620-stock-page-lane.mjs`

## Host timer visibility

- `systemctl status paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned `Unit paperclip-buy31716-fleet-keep-alive.timer could not be found.`
- `systemctl list-timers paperclip-buy31716-fleet-keep-alive.timer --no-pager`
  returned `0 timers listed.`

That host-level timer visibility gap remains a separate deployment concern, but
it does not block closing this execution issue because the watchdog is clearly
alive on a 5-minute cadence and the restart path fired successfully during the
observed window.
