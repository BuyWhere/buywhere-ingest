# BUY-38644 — BUY-31716 fleet keep-alive closeout (2026-06-09T19:14:12Z)

Issue scope: verify that the BUY-31716 fleet keep-alive still runs on the
expected 5-minute cadence and leaves the 8 discovery lanes healthy or
intentionally skipped.

## Verification

- Confirmed the canonical watchdog entrypoint remains
  `scripts/buy31716-fleet-keep-alive.sh`.
- Confirmed `systemd/paperclip-buy31716-fleet-keep-alive.timer` still uses
  `OnUnitActiveSec=5min` with `Persistent=true`.
- Ran a fresh syntax check, unit verification, and live watchdog tick in this
  heartbeat.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
python3 - <<'PY'
import json
from pathlib import Path
p = Path('/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json')
data = json.loads(p.read_text())
for item in data.get('escalations', [])[-5:]:
    print(json.dumps(item))
PY
```

## Results

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated warning from
  `/etc/systemd/system/hindsight.service`; there were no errors for
  `paperclip-buy31716-fleet-keep-alive.service` or `.timer`.
- A fresh live watchdog tick completed at `2026-06-09T19:13:53Z`.
- Healthy active lanes at `2026-06-09T19:13:53Z` were `burst_discovery`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`,
  and `stock_page`.
- `brand_sitemap_miner` and `retailer_sitemap_miner` were intentionally skipped
  because their stop markers were present, and the log recorded them as
  `STOPPED` plus `SKIPPED` rather than dead.
- Shared state advanced to `disk_last_sampled_at=2026-06-09T19:13:53Z`, all
  tracked lane dead counts remained `0`, `disk_use_pct` was `89`, and
  `disk_pressure_pauses` remained `15`.
- The escalation file still contains only historical entries; the newest
  sampled escalation entries remain from `2026-06-08`, so this heartbeat added
  no new escalation.

## Disposition

`BUY-38644` can close `done`: the BUY-31716 fleet watchdog still runs on the
expected 5-minute cadence, completed a fresh tick in this heartbeat, and left
every tracked lane healthy or intentionally skipped by marker.
