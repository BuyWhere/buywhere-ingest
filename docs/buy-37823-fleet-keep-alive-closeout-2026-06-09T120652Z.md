# BUY-37823 — BUY-31716 fleet keep-alive closeout (2026-06-09T12:06:52Z)

Routine execution issue for the 5-minute BUY-31716 fleet watchdog covering 8
discovery lanes.

## Verification run

Commands run from the active Oracle workspace:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify \
  systemd/paperclip-buy31716-fleet-keep-alive.service \
  systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
tail -n 80 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
```

## Results

- `bash -n scripts/buy31716-fleet-keep-alive.sh` passed.
- `systemd-analyze verify` reported only the known unrelated
  `/etc/systemd/system/hindsight.service` warning and no error for the
  BUY-31716 keep-alive service or timer.
- The watchdog still runs from
  `systemd/paperclip-buy31716-fleet-keep-alive.service` on the
  5-minute `OnUnitActiveSec=5min` timer with `Persistent=true`.
- A fresh manual watchdog invocation completed at `2026-06-09T12:06:27Z`.
  Because the existing disk-pressure marker is still active, that tick took the
  intentional disk-pause path instead of respawning lanes:

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T12:06:27Z =====
[2026-06-09T12:06:27Z] invocation: $0=scripts/buy31716-fleet-keep-alive.sh realpath=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/buy31716-fleet-keep-alive.sh
[2026-06-09T12:06:27Z] host disk use=92% (threshold=95%, recover=90%)
[2026-06-09T12:06:27Z] disk-pressure PAUSE — marker present, sweep: freed=0 removed=0, pause_count=14
[2026-06-09T12:06:27Z] BUY-31716 fleet keep-alive tick complete (disk-pause path)
```

- The same live log shows the most recent full healthy lane scan before the
  disk guard tripped, at `2026-06-09T11:46:37Z`, with all 8 tracked lanes
  healthy: `burst_discovery`, `brand_sitemap_miner`,
  `retailer_sitemap_miner`, `fast_wc_probe`, `shopify_index_expansion`,
  `crate_deep_page`, `hunt2_page`, and `stock_page`.
- Shared state after this heartbeat remained fully reset for all lane dead
  counters and advanced the disk sample timestamp:

```json
{
  "brand_sitemap_miner": 0,
  "burst_discovery": 0,
  "crate_deep_page": 0,
  "disk_last_sampled_at": "2026-06-09T12:03:53Z",
  "disk_pressure_pauses": 13,
  "disk_use_pct": "92",
  "fast_wc_probe": 0,
  "hunt2_page": 0,
  "last_disk_pressure_marker": "{\"created_at\": \"2026-06-09T11:51:52Z\", \"use_pct\": 95, \"threshold_pct\": 95, \"root\": \"/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c\", \"note\": \"write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)\"}",
  "last_disk_pressure_pause_at": "2026-06-09T12:03:53Z",
  "retailer_sitemap_miner": 0,
  "shopify_index_expansion": 0,
  "stock_page": 0
}
```

## Conclusion

`BUY-37823` can close `done`. The fleet keep-alive watchdog, service, and
timer are still wired correctly; the latest heartbeat proved the 5-minute
watchdog fired successfully in this workspace; and the most recent non-paused
tick confirmed all 8 tracked BUY-31716 lanes were healthy. The current
disk-pressure marker is intentionally suppressing restart work until host disk
usage falls to the configured recovery threshold.
