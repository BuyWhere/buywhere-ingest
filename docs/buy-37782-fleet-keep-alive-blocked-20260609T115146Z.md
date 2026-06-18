# BUY-37782 — BUY-31716 fleet keep-alive blocked by disk-pressure pause (2026-06-09T11:51:46Z)

This heartbeat re-verified the `BUY-31716` 8-lane fleet keep-alive and found that the watchdog is no longer on its normal restart path. A fresh manual tick tripped the disk-pressure guard and entered the pause path, which suppresses dead-lane restart until the marker clears.

## Scope

- Verified the canonical watchdog at `scripts/buy31716-fleet-keep-alive.sh`.
- Re-verified the systemd wiring for the 5-minute cadence.
- Executed a fresh manual tick and captured the resulting log, state, and marker evidence.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
tail -n 30 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 20 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
sed -n '1,220p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
sed -n '1,120p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-disk-pressure.marker
df -P /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
findmnt -T /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported only the known unrelated `/etc/systemd/system/hindsight.service` warning about `StartLimitIntervalSec`; there were no errors for the `paperclip-buy31716-fleet-keep-alive` service or timer.
- The live timer path was healthy through `2026-06-09T11:46:39Z`; that tick reported all 8 lanes OK.
- The manual verification run at `2026-06-09T11:51:52Z` did **not** perform the normal lane-health pass. It logged `disk-pressure TRIP`, wrote `/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-disk-pressure.marker`, and exited via `disk-pressure PAUSE`.
- Shared state now records `disk_last_sampled_at=2026-06-09T11:51:52Z`, `disk_use_pct=95`, `disk_pressure_pauses=11`, and `last_disk_pressure_pause_at=2026-06-09T11:51:52Z`.
- Because the helper uses `DISK_GUARD_RECOVER_PCT=90`, future ticks will continue to pause while the marker exists until the sampled filesystem drops below `90%`. At that point the helper clears the marker and normal restart behavior resumes automatically.

## Last Healthy Tick

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T11:46:37Z =====
[2026-06-09T11:46:37Z] host disk use=94% (threshold=95%, recover=90%)
[2026-06-09T11:46:37Z] burst_discovery OK pid=2139271 (no_heartbeat_file)
[2026-06-09T11:46:38Z] brand_sitemap_miner OK pid=2146097 heartbeat_age=9s
[2026-06-09T11:46:38Z] retailer_sitemap_miner OK pid=2146225 heartbeat_age=24s
[2026-06-09T11:46:38Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T11:46:39Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T11:46:39Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T11:46:39Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T11:46:39Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T11:46:39Z] keep-alive tick complete
```

## Blocking Tick

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T11:51:52Z =====
[2026-06-09T11:51:52Z] disk-pressure TRIP — use=95% >= threshold=95%, marker written to /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-disk-pressure.marker
[2026-06-09T11:51:52Z] host disk use=95% (threshold=95%, recover=90%)
[2026-06-09T11:51:52Z] disk-pressure PAUSE — marker present, sweep: freed=0 removed=0, pause_count=11
[2026-06-09T11:51:52Z] BUY-31716 fleet keep-alive tick complete (disk-pause path)
```

## Marker

```json
{
  "created_at": "2026-06-09T11:51:52Z",
  "use_pct": 95,
  "threshold_pct": 95,
  "root": "/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c",
  "note": "write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)"
}
```

## Note On Filesystem Sampling

An immediate manual `df -P` on the same workspace path showed `92%` used on `/dev/vda1`, while the keep-alive helper had just recorded `95%`. The blocker call above is based on the watchdog's own sampled value and persisted marker/state, because that is what governs future keep-alive behavior. Even if the live filesystem is now below `95%`, the marker will still keep future ticks on the pause path until the helper samples below the `90%` recovery threshold.

## Current Disposition

`BUY-31716` fleet keep-alive is temporarily **not providing the 5-minute restart guarantee**. The timer is still firing, but restart work is suppressed by the active disk-pressure marker. The issue should remain blocked until the Oracle workspace filesystem is reduced below the recovery threshold and a fresh keep-alive tick clears the marker.
