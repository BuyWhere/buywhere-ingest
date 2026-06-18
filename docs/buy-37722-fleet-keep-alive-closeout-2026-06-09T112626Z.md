# BUY-37722 — BUY-31716 fleet keep-alive closeout (2026-06-09T11:26:26Z)

Wake scope: verify that the `BUY-31716` fleet keep-alive still restarts the 8
discovery lanes on a 5-minute cadence and leave fresh runtime evidence for this
heartbeat.

## What was verified

- `scripts/buy31716-fleet-keep-alive.sh` remains the active watchdog for the 8
  fleet lanes:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`,
  `hunt2_page`, and `stock_page`.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` still runs the
  watchdog from this workspace as a oneshot service.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` still preserves the
  expected cadence with `OnUnitActiveSec=5min` and `Persistent=true`.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy31716-fleet-keep-alive.sh
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported no `BUY-31716` unit errors; the only output
  was the known unrelated warning for `/etc/systemd/system/hindsight.service`.
- A fresh manual tick completed at `2026-06-09T11:26:27Z`.
- All 8 tracked lanes were alive on the fresh tick:

```text
[2026-06-09T11:26:26Z] burst_discovery OK pid=2139271 (no_heartbeat_file)
[2026-06-09T11:26:27Z] brand_sitemap_miner OK pid=2146097 heartbeat_age=29s
[2026-06-09T11:26:27Z] retailer_sitemap_miner OK pid=2146225 heartbeat_age=18s
[2026-06-09T11:26:27Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T11:26:27Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T11:26:27Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T11:26:27Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T11:26:27Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T11:26:27Z] keep-alive tick complete
```

- `data/buy31716-fleet-keep-alive-state.json` shows all per-lane dead-tick
  counters at `0`.
- `disk_use_pct` sampled at `94`, below the `95` percent guard threshold, so
  the watchdog stayed on its normal liveness path.
- `data/buy31716-fleet-keep-alive-escalation.json` still contains only older
  historical escalations from `2026-06-08`; this heartbeat did not append a
  new escalation record.

## Conclusion

`BUY-37722` can close `done`: the `BUY-31716` fleet watchdog remains wired to
its 5-minute restart cadence and currently sees all 8 discovery lanes alive,
with no new escalation triggered in this heartbeat.
