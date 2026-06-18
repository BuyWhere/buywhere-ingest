# BUY-38191 — BUY-31716 fleet keep-alive closeout (2026-06-09T15:11:26Z)

Routine execution issue for the 5-minute `BUY-31716` discovery-fleet watchdog.

## What I ran

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
find /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data -maxdepth 1 \( -name 'buy30590-brand-sitemap-miner.stopped' -o -name 'buy30590-retailer-sitemap-loop.stopped' \) -printf '%f %TY-%Tm-%TdT%TH:%TM:%TSZ\n'
```

## Result

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- A fresh keep-alive tick completed successfully at `2026-06-09T15:11:14Z` with host disk use at `84%`, below the `95%` guard threshold.
- Six active lanes were healthy on this tick: `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were intentionally skipped, not failed. Their stop markers remain present and are timestamped `2026-06-09T12:30:04Z`.
- `data/buy31716-fleet-keep-alive-state.json` advanced `disk_last_sampled_at` to `2026-06-09T15:11:14Z`, kept `disk_use_pct` at `84`, retained `disk_pressure_pauses=15`, and left every per-lane dead count at `0`.
- No new escalation was added in this heartbeat; the newest retained escalation entries remain historical records from `2026-06-08`.

## Fresh log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T15:11:14Z =====
[2026-06-09T15:11:14Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T15:11:14Z] host disk use=84% (threshold=95%, recover=90%)
[2026-06-09T15:11:14Z] burst_discovery OK pid=3131982 (no_heartbeat_file)
[2026-06-09T15:11:14Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T15:11:14Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T15:11:14Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T15:11:14Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T15:11:14Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T15:11:14Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T15:11:14Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T15:11:15Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T15:11:15Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T15:11:15Z] keep-alive tick complete
```

## Disposition

`BUY-38191` can close `done`: the 5-minute fleet keep-alive executed successfully, covered the full 8-lane configuration, kept the six active discovery lanes healthy, and correctly honored the two sitemap stop markers instead of treating them as dead-lane failures.
