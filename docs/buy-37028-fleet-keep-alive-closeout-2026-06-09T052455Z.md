# BUY-37028 — BUY-31716 fleet keep-alive closeout (2026-06-09T05:24:55Z)

Issue scope: confirm the 5-minute BUY-31716 fleet keep-alive still restarts and
monitors the eight discovery lanes from the live watchdog path.

## Verification

- `bash -n scripts/buy31716-fleet-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer`
- `bash scripts/buy31716-fleet-keep-alive.sh`
- `tail -n 20 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log`
- `cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json`
- `python3 - <<'PY' ... buy31716-fleet-keep-alive-escalation.json ... PY`

## Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; it reported no errors for
  `systemd/paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- The manual keep-alive tick at `2026-06-09T05:24:55Z` completed and reported
  all 8 discovery lanes healthy:
  - `burst_discovery` OK `pid=3907215`
  - `brand_sitemap_miner` OK `pid=2316250` `heartbeat_age=7s`
  - `retailer_sitemap_miner` OK `pid=2316426` `heartbeat_age=44s`
  - `fast_wc_probe` OK `pid=3848747`
  - `shopify_index_expansion` OK `pid=3848851`
  - `crate_deep_page` OK `pid=2316670`
  - `hunt2_page` OK `pid=4120587`
  - `stock_page` OK `pid=2316883`
- The watchdog sampled host disk use at `88%`, below the `95%` guard
  threshold, so the tick was not paused by disk pressure.
- The shared state file advanced `disk_last_sampled_at` to
  `2026-06-09T05:24:55Z`, preserved `disk_use_pct` at `88`, and kept every lane
  dead-count at `0`.
- The escalation file still ends with the older `2026-06-08T05:51:52Z`
  `shopify_index_expansion` event; this heartbeat added no new escalation.

## Conclusion

`BUY-37028` can close `done`: the BUY-31716 fleet keep-alive remains wired to
the canonical script and 5-minute systemd timer, and the current verification
tick found all eight discovery lanes alive with no restart or escalation needed.
