# BUY-38669 fleet keep-alive closeout

- Verified the active BUY-31716 fleet watchdog is still `scripts/buy31716-fleet-keep-alive.sh` and that `systemd/paperclip-buy31716-fleet-keep-alive.timer` retains the 5-minute cadence with `OnUnitActiveSec=5min` and `Persistent=true`.
- Ran `bash -n scripts/buy31716-fleet-keep-alive.sh`.
- Ran `systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer`.
- Ran `WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh`.

Findings

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning about `StartLimitIntervalSec`; there were no errors for the BUY-31716 service or timer units.
- The manual keep-alive tick completed at `2026-06-09T19:28:46Z` in the shared Oracle workspace log.
- Healthy live lanes in this heartbeat were `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`, and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were intentionally skipped because their stop markers were present at `2026-06-09 12:30:04 UTC`.
- Shared state advanced to `disk_last_sampled_at=2026-06-09T19:28:46Z`, preserved zero dead counts for every tracked lane, and recorded `disk_use_pct=88`.
- The escalation log gained no new entry in this heartbeat; the newest recorded escalation remains `2026-06-08T05:51:52Z`.

Latest log block

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T19:28:46Z =====
[2026-06-09T19:28:46Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T19:28:46Z] host disk use=88% (threshold=95%, recover=90%)
[2026-06-09T19:28:46Z] burst_discovery OK pid=3782962 (no_heartbeat_file)
[2026-06-09T19:28:46Z] brand_sitemap_miner STOPPED (already absent)
[2026-06-09T19:28:46Z] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)
[2026-06-09T19:28:46Z] retailer_sitemap_miner STOPPED (already absent)
[2026-06-09T19:28:46Z] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)
[2026-06-09T19:28:46Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T19:28:46Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T19:28:46Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T19:28:46Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T19:28:46Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T19:28:46Z] keep-alive tick complete
```

Current keep-alive state

```json
{
  "brand_sitemap_miner": 0,
  "burst_discovery": 0,
  "crate_deep_page": 0,
  "disk_last_sampled_at": "2026-06-09T19:28:46Z",
  "disk_pressure_pauses": 15,
  "disk_use_pct": "88",
  "fast_wc_probe": 0,
  "hunt2_page": 0,
  "last_disk_pressure_marker": "{\"created_at\": \"2026-06-09T11:51:52Z\", \"use_pct\": 95, \"threshold_pct\": 95, \"root\": \"/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c\", \"note\": \"write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)\"}",
  "last_disk_pressure_pause_at": "2026-06-09T12:23:28Z",
  "retailer_sitemap_miner": 0,
  "shopify_index_expansion": 0,
  "stock_page": 0
}
```
