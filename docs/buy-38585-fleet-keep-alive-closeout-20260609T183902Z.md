# BUY-38585 — BUY-31716 fleet keep-alive closeout (2026-06-09T18:39:02Z)

Routine execution issue for the 5-minute `BUY-31716` fleet keep-alive watchdog covering the 8 discovery lanes.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh
tail -n 80 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json
```

## Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no verification errors for `paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- The keep-alive timer definition still enforces the 5-minute cadence via `OnUnitActiveSec=5min` with `Persistent=true`.
- A fresh keep-alive tick completed at `2026-06-09T18:38:42Z` through `2026-06-09T18:38:43Z` in `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`.
- Six discovery lanes were healthy on the fresh tick: `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were not treated as dead lanes; both were explicitly logged as `SKIPPED` because their stop markers are present at `data/buy30590-brand-sitemap-miner.stopped` and `data/buy30590-retailer-sitemap-loop.stopped`.
- Shared state in `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json` advanced to `disk_last_sampled_at=2026-06-09T18:38:42Z`, kept all tracked per-lane dead counts at `0`, preserved `disk_pressure_pauses=15`, and recorded `disk_use_pct=89`.
- `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json` did not gain a new entry in this heartbeat; it still contains only the older 2026-06-08 escalation history.

## Log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T18:38:42Z =====
[2026-06-09T18:38:42Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T18:38:42Z] host disk use=89% (threshold=95%, recover=90%)
[2026-06-09T18:38:42Z] burst_discovery OK pid=3782962 (no_heartbeat_file)
[2026-06-09T18:38:42Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T18:38:42Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T18:38:42Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T18:38:42Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T18:38:42Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T18:38:42Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T18:38:43Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T18:38:43Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T18:38:43Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T18:38:43Z] keep-alive tick complete
```

`BUY-38585` can close `done`: the `BUY-31716` keep-alive remains wired for 5-minute restart checks, the fresh watchdog tick was healthy, no dead-count or escalation state regressed, and the only non-running lanes were intentionally stop-marked rather than missed by the watchdog.
