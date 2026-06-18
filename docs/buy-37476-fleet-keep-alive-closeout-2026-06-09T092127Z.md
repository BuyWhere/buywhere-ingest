# BUY-37476 fleet keep-alive closeout

Timestamp: 2026-06-09T09:21:27Z

## Scope

Routine execution for [BUY-31716](/BUY/issues/BUY-31716): verify the 5-minute
keep-alive watchdog for the 8 new discovery lanes and confirm the watchdog can
still complete a healthy tick from the active Oracle workspace.

## Verification

Commands run:

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 20 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
python3 - <<'PY'
import json, os
p='/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json'
data=json.load(open(p))
esc=data.get('escalations', [])
print('escalations=', len(esc))
print('last=', json.dumps(esc[-1], indent=2))
PY
```

## Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated warning from
  `/etc/systemd/system/hindsight.service`; there were no service/timer errors
  for `paperclip-buy31716-fleet-keep-alive`.
- A fresh manual keep-alive tick completed at `2026-06-09T09:21:27Z`.
- The tick logged all 8 lanes as healthy:
  - `burst_discovery` pid `670904`
  - `brand_sitemap_miner` pid `2316250`, heartbeat age `0s`
  - `retailer_sitemap_miner` pid `2316426`, heartbeat age `8s`
  - `fast_wc_probe` pid `3848747`
  - `shopify_index_expansion` pid `3848851`
  - `crate_deep_page` pid `2316670`
  - `hunt2_page` pid `4120587`
  - `stock_page` pid `2316883`
- `data/buy31716-fleet-keep-alive-state.json` advanced
  `disk_last_sampled_at` to `2026-06-09T09:21:26Z`, recorded `disk_use_pct` as
  `93`, and kept all per-lane dead counts at `0`.
- `data/buy31716-fleet-keep-alive-escalation.json` still contains only
  historical entries; the latest remains the prior
  `shopify_index_expansion` escalation at `2026-06-08T05:51:52Z`, so this tick
  added no new escalation.

## Disposition

No code change was required in this heartbeat. The watchdog, service unit, and
5-minute timer remain valid, and the routine execution can be closed `done`.
