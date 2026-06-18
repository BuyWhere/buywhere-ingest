# BUY-38745 — BUY-31716 fleet keep-alive closeout (2026-06-09T20:14:08Z)

Issue scope: verify that the 5-minute `BUY-31716` fleet keep-alive still runs
cleanly for the 8 discovery lanes and leaves the shared Oracle fleet state
healthy.

Commands run:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 30 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,220p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
stat -c '%y %n' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-brand-sitemap-miner.stopped /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30590-retailer-sitemap-loop.stopped
```

Results:

- `scripts/buy31716-fleet-keep-alive.sh` passed `bash -n`.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still sets
  `OnUnitActiveSec=5min` with `Persistent=true`.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; the BUY-31716 service/timer pair had
  no verification errors.
- A fresh manual tick completed at `2026-06-09T20:14:09Z`.
- Automatic ticks were already continuing before the manual run, including
  `2026-06-09T20:08:49Z`, so the watchdog was not stalled between heartbeats.
- Shared fleet state advanced to `disk_last_sampled_at=2026-06-09T20:14:08Z`
  with `disk_use_pct=88`, `disk_pressure_pauses=15`, and all tracked dead-count
  fields at `0`.
- Live healthy lanes on the fresh tick were `burst_discovery`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`,
  `hunt2_page`, and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were intentionally
  skipped because stop markers were present at `2026-06-09 12:30:04 UTC`.

Fresh log block:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T20:14:08Z =====
[2026-06-09T20:14:08Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T20:14:08Z] host disk use=88% (threshold=95%, recover=90%)
[2026-06-09T20:14:08Z] burst_discovery OK pid=3782962 (no_heartbeat_file)
[2026-06-09T20:14:08Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T20:14:08Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T20:14:08Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T20:14:08Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T20:14:08Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T20:14:08Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T20:14:08Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T20:14:09Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T20:14:09Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T20:14:09Z] keep-alive tick complete
```

Conclusion:

`BUY-38745` can close `done`: the fleet keep-alive remains wired to its 5-minute
cadence, a fresh manual tick completed during this heartbeat, dead-count state
stayed at zero, and the two sitemap lanes remain intentionally stopped rather
than dead.
