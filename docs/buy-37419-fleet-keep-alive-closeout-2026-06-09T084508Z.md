# BUY-37419 — BUY-31716 fleet keep-alive closeout (2026-06-09T08:45:08Z)

Wake scope: run the `BUY-31716` fleet keep-alive execution issue and verify the
5-minute restart watchdog still covers the 8 discovery lanes introduced under
the fleet scale-up work.

## What is wired

- `scripts/buy31716-fleet-keep-alive.sh` is the active watchdog for the 8
  lanes named in `BUY-37419`:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`,
  `hunt2_page`, and `stock_page`.
- `systemd/paperclip-buy31716-fleet-keep-alive.service` runs the watchdog as a
  oneshot service from this workspace.
- `systemd/paperclip-buy31716-fleet-keep-alive.timer` preserves the expected
  5-minute cadence with `OnUnitActiveSec=5min` and `Persistent=true`.

## Verification run

Commands executed in this heartbeat:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json
```

Results:

- `bash -n` passed.
- `systemd-analyze verify` reported no error for the fleet keep-alive unit or
  timer. The only output was the known unrelated warning for
  `/etc/systemd/system/hindsight.service`.
- A fresh manual tick completed at `2026-06-09T08:44:50Z`.
- The keep-alive log shows every lane healthy on that tick:

```text
[2026-06-09T08:44:49Z] burst_discovery OK pid=670904 (no_heartbeat_file)
[2026-06-09T08:44:49Z] brand_sitemap_miner OK pid=2316250 heartbeat_age=26s
[2026-06-09T08:44:49Z] retailer_sitemap_miner OK pid=2316426 heartbeat_age=24s
[2026-06-09T08:44:50Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T08:44:50Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T08:44:50Z] crate_deep_page OK pid=2316670 (no_heartbeat_file)
[2026-06-09T08:44:50Z] hunt2_page OK pid=4120587 (no_heartbeat_file)
[2026-06-09T08:44:50Z] stock_page OK pid=2316883 (no_heartbeat_file)
[2026-06-09T08:44:50Z] keep-alive tick complete
```

- `data/buy31716-fleet-keep-alive-state.json` shows all per-lane dead-tick
  counters at `0`.
- `disk_use_pct` was `92`, below the `95` percent disk guard threshold, so the
  watchdog stayed on its normal liveness path.
- `data/buy31716-fleet-keep-alive-escalation.json` still contains historical
  escalations from `2026-06-08`, but this heartbeat did not append any new
  escalation record.

## Conclusion

`BUY-37419` can close `done`: the `BUY-31716` fleet watchdog is still wired to
its 5-minute cadence and currently sees all 8 discovery lanes alive, with dead
tick counters reset and no new escalation triggered in this run.
