# BUY-37756 / BUY-31716 fleet keep-alive closeout

Routine execution issue for the 5-minute BUY-31716 fleet keep-alive watchdog.

## Commands run

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 25 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
```

## Fresh verification

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated warning from `/etc/systemd/system/hindsight.service`; the BUY-31716 keep-alive service and timer verified cleanly.
- A fresh manual keep-alive tick completed at `2026-06-09T11:41:33Z`.
- All 8 lanes were healthy on that tick: `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, and `stock_page`.
- Shared state advanced to `disk_last_sampled_at=2026-06-09T11:41:33Z` with `disk_use_pct=94` and all per-lane dead counts at `0`.
- Historical escalation entries remain in `data/buy31716-fleet-keep-alive-escalation.json`, but this heartbeat did not append a new escalation.

## Fresh tick excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T11:41:33Z =====
[2026-06-09T11:41:33Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T11:41:33Z] host disk use=94% (threshold=95%, recover=90%)
[2026-06-09T11:41:33Z] burst_discovery OK pid=2139271 (no_heartbeat_file)
[2026-06-09T11:41:33Z] brand_sitemap_miner OK pid=2146097 heartbeat_age=4s
[2026-06-09T11:41:33Z] retailer_sitemap_miner OK pid=2146225 heartbeat_age=28s
[2026-06-09T11:41:33Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T11:41:34Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T11:41:34Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T11:41:34Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T11:41:34Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T11:41:34Z] keep-alive tick complete
```

## Disposition

`BUY-37756` can close `done`: the routine-execution watchdog completed a clean keep-alive tick for the full 8-lane BUY-31716 fleet, all tracked dead counters stayed at zero, and no follow-up action was required in this heartbeat.
