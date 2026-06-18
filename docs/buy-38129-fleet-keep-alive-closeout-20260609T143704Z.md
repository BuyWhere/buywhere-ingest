# BUY-38129 — BUY-31716 fleet keep-alive closeout (2026-06-09T14:37:04Z)

Routine execution issue for the 5-minute `BUY-31716` discovery-fleet watchdog.

## What I ran

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh
tail -n 25 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,220p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
tail -n 20 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json
find /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data -maxdepth 1 \( -name 'buy30590-brand-sitemap-miner.stopped' -o -name 'buy30590-retailer-sitemap-loop.stopped' \) -printf '%f %TY-%Tm-%TdT%TH:%TM:%TSZ\n'
```

## Result

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no verification errors for the BUY-31716 service or timer units.
- The fleet log advanced through a fresh successful automatic tick at `2026-06-09T14:36:45Z`, with all active lanes healthy: `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, and `stock_page`.
- `data/buy31716-fleet-keep-alive-state.json` advanced `disk_last_sampled_at` to `2026-06-09T14:36:44Z`, retained `disk_use_pct=83`, kept `disk_pressure_pauses=15`, and left all tracked dead counts at `0`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were intentionally skipped, not dead; both stop markers are present and timestamped `2026-06-09T12:30:04Z`.
- `data/buy31716-fleet-keep-alive-escalation.json` did not gain a new entry in this heartbeat; the newest retained escalations remain historical entries from `2026-06-08`.
- The watchdog also exercised its duplicate-pruning path earlier in this runtime window: on the `2026-06-09T14:06:57Z` tick it killed duplicate `buy30331-sustained-loop.mjs` processes for `burst_discovery` and kept a single survivor (`pid=3103443`), after which later ticks showed the lane healthy under its current pid (`3131982`).

## Fresh log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T14:36:44Z =====
[2026-06-09T14:36:44Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T14:36:44Z] host disk use=83% (threshold=95%, recover=90%)
[2026-06-09T14:36:44Z] burst_discovery OK pid=3131982 (no_heartbeat_file)
[2026-06-09T14:36:44Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T14:36:44Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T14:36:44Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T14:36:44Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T14:36:44Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T14:36:44Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T14:36:45Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T14:36:45Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T14:36:45Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T14:36:45Z] keep-alive tick complete
```

## Disposition

`BUY-38129` can close `done`: the 5-minute fleet keep-alive remains active, the six live discovery lanes are healthy, the two missing sitemap lanes are intentionally stop-marked, and the watchdog showed both steady-state liveness and duplicate-process cleanup during this heartbeat window.
