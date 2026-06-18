# BUY-37452 — BUY-31716 fleet keep-alive closeout (2026-06-09T09:11:48Z)

Issue scope: verify the 5-minute keep-alive watchdog still covers the 8 BUY-31716 discovery lanes and can complete a healthy tick from the active Oracle workspace.

## Verification run

Commands:

- `bash -n scripts/buy31716-fleet-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer`
- `bash scripts/buy31716-fleet-keep-alive.sh`

`systemd-analyze verify` output:

```text
/etc/systemd/system/hindsight.service:14: Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.
```

That warning is unrelated to the BUY-31716 keep-alive unit and timer. The fleet keep-alive service/timer pair produced no verification errors.

## Manual keep-alive tick

Tail of `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log` after the manual tick:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T09:11:28Z =====
[2026-06-09T09:11:28Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T09:11:28Z] host disk use=92% (threshold=95%, recover=90%)
[2026-06-09T09:11:28Z] burst_discovery OK pid=670904 (no_heartbeat_file)
[2026-06-09T09:11:28Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=2s
[2026-06-09T09:11:29Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=26s
[2026-06-09T09:11:29Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T09:11:29Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T09:11:29Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-09T09:11:29Z] hunt2_page OK pid=4120587 (no_heartbeat_file)
[2026-06-09T09:11:29Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-09T09:11:29Z] keep-alive tick complete
```

## Shared state after tick

`/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`:

```json
{
  "brand_sitemap_miner": 0,
  "burst_discovery": 0,
  "crate_deep_page": 0,
  "disk_last_sampled_at": "2026-06-09T09:11:28Z",
  "disk_pressure_pauses": 10,
  "disk_use_pct": "92",
  "fast_wc_probe": 0,
  "hunt2_page": 0,
  "last_disk_pressure_marker": "{\"created_at\": \"2026-06-07T21:16:42Z\", \"use_pct\": 80, \"threshold_pct\": 50, \"root\": \"/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c\", \"note\": \"write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)\"}",
  "last_disk_pressure_pause_at": "2026-06-07T21:16:42Z",
  "retailer_sitemap_miner": 0,
  "shopify_index_expansion": 0,
  "stock_page": 0
}
```

The historical escalation file still contains older June 8 entries, but the fresh 2026-06-09T09:11:28Z tick added no new escalation for any of the 8 lanes.

## Disposition

BUY-37452 can close `done`. The fleet keep-alive watchdog, service, and timer are present, a fresh manual tick completed successfully, all eight tracked lanes were healthy, and the shared dead-count state remained at zero.
