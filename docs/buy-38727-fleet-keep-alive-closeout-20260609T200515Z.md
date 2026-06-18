# BUY-38727 closeout — BUY-31716 fleet keep-alive

- Verified the active watchdog entrypoint is still `scripts/buy31716-fleet-keep-alive.sh`.
- Verified `systemd/paperclip-buy31716-fleet-keep-alive.timer` still enforces the 5-minute cadence with `OnUnitActiveSec=5min` and `Persistent=true`.
- Ran a fresh manual watchdog tick in the Oracle workspace and confirmed the fleet completed cleanly at `2026-06-09T20:05:15Z`.

Commands run:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,240p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
```

Results:

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no verification errors for `paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- The fresh keep-alive tick appended this block to `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T20:05:14Z =====
[2026-06-09T20:05:14Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T20:05:14Z] host disk use=89% (threshold=95%, recover=90%)
[2026-06-09T20:05:14Z] burst_discovery OK pid=3782962 (no_heartbeat_file)
[2026-06-09T20:05:14Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T20:05:14Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T20:05:14Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T20:05:14Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T20:05:14Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T20:05:14Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T20:05:15Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T20:05:15Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T20:05:15Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T20:05:15Z] keep-alive tick complete
```

- Active healthy lanes remained:
  `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`,
  `crate_deep_page`, `hunt2_page`, and `stock_page`.
- Intentionally skipped lanes remained:
  `brand_sitemap_miner` and `retailer_sitemap_miner`, both gated by stop markers last updated at `2026-06-09 12:30:04 UTC`.
- Shared state file `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json` advanced `disk_last_sampled_at` to `2026-06-09T20:05:14Z`, kept `disk_use_pct` at `89`, preserved `disk_pressure_pauses` at `15`, and kept every per-lane dead count at `0`.
- Escalation file `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json` gained no new entry in this heartbeat; it still contains `30` historical escalations, with the newest remaining the older `2026-06-08T05:51:52Z` `shopify_index_expansion` event.

`BUY-38727` can close `done`: the BUY-31716 keep-alive still performs the 5-minute fleet liveness sweep, completed a fresh tick in this heartbeat, and left the shared fleet state healthy with no new escalation.
