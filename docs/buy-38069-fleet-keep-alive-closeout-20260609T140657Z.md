# BUY-38069 — BUY-31716 fleet keep-alive closeout (2026-06-09T14:06:57Z)

Routine execution issue for the 5-minute `BUY-31716` fleet keep-alive watchdog.

## Verification

- `bash -n scripts/buy31716-fleet-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer`
- `bash scripts/buy31716-fleet-keep-alive.sh`
- `tail -n 30 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`
- `cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`

## Results

- Shell syntax check passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for `/etc/systemd/system/hindsight.service`; there were no validation errors for `systemd/paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- A fresh manual tick completed at `2026-06-09T14:06:57Z` and appended cleanly to `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`.
- Live lanes observed healthy on that tick:
  `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were not treated as dead; the keep-alive explicitly held them in `STOPPED/SKIPPED` state because the stop markers `data/buy30590-brand-sitemap-miner.stopped` and `data/buy30590-retailer-sitemap-loop.stopped` are present in the Oracle workspace.
- The watchdog observed duplicate `burst_discovery` loop processes, killed PIDs `2775043` and `3103444`, and kept PID `3103443` live. The tick still completed successfully and left the lane healthy.
- Shared fleet state advanced `disk_last_sampled_at` to `2026-06-09T14:06:57Z`, kept `disk_use_pct` at `80`, and preserved zero dead counts for every tracked lane key.

## Log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T14:06:57Z =====
[2026-06-09T14:06:57Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T14:06:57Z] host disk use=80% (threshold=95%, recover=90%)
[2026-06-09T14:06:57Z] duplicate buy30331-sustained-loop\.mjs killed pid=2775043 (kept 3103443)
[2026-06-09T14:06:57Z] duplicate buy30331-sustained-loop\.mjs killed pid=3103444 (kept 3103443)
[2026-06-09T14:06:57Z] burst_discovery OK pid=3103443 (no_heartbeat_file)
[2026-06-09T14:06:57Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T14:06:57Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T14:06:57Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T14:06:57Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T14:06:57Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T14:06:58Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T14:06:58Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T14:06:58Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T14:06:58Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T14:06:58Z] keep-alive tick complete
```

## Conclusion

`BUY-38069` can close `done`. The watchdog, service, and timer remain valid; the fleet tick completed successfully at `2026-06-09T14:06:57Z`; six lanes were actively healthy; two sitemap lanes stayed intentionally suppressed by stop markers; and the duplicate `burst_discovery` processes were collapsed back to one live PID during the run.
