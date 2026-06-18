# BUY-38173 — BUY-31716 fleet keep-alive closeout (2026-06-09T15:04:00Z)

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
- The fleet log advanced through a fresh successful tick at `2026-06-09T15:03:41Z`, covering all 8 configured lanes. Six active lanes were healthy: `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were not treated as failures. Both were intentionally skipped because their stop markers are present and timestamped `2026-06-09T12:30:04Z`.
- `data/buy31716-fleet-keep-alive-state.json` advanced `disk_last_sampled_at` to `2026-06-09T15:03:41Z`, retained `disk_pressure_pauses=15`, updated `disk_use_pct` to `84`, and left every per-lane dead count at `0`.
- `data/buy31716-fleet-keep-alive-escalation.json` did not gain a new entry in this heartbeat; the newest retained escalations remain historical entries from `2026-06-08`.

## Fresh log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T15:03:41Z =====
[2026-06-09T15:03:41Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T15:03:41Z] host disk use=84% (threshold=95%, recover=90%)
[2026-06-09T15:03:41Z] burst_discovery OK pid=3131982 (no_heartbeat_file)
[2026-06-09T15:03:41Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T15:03:41Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T15:03:41Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T15:03:41Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T15:03:41Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T15:03:41Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T15:03:41Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T15:03:41Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T15:03:41Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T15:03:41Z] keep-alive tick complete
```

## Disposition

`BUY-38173` can close `done`: the 5-minute fleet keep-alive still executes successfully, still evaluates the full 8-lane configuration, keeps six active discovery lanes healthy, and correctly treats the two sitemap lanes as intentional stop-marked skips rather than dead-lane restarts.
