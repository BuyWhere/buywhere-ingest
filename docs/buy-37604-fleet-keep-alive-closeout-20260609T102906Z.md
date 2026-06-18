# BUY-37604 — BUY-31716 fleet keep-alive closeout (2026-06-09T10:29:06Z)

Issue scope: verify that the BUY-31716 fleet keep-alive in this checkout still
enforces the 5-minute watchdog for the 8 discovery lanes and still restarts dead
lanes when needed.

## Commands

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify \
  systemd/paperclip-buy31716-fleet-keep-alive.service \
  systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
tail -n 80 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
cat /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-escalation.json')
data = json.load(open(p))
esc = data.get('escalations', [])
print(json.dumps({'count': len(esc), 'last': esc[-1] if esc else None}, indent=2))
PY
```

## Verification

- `bash -n` passed for `scripts/buy31716-fleet-keep-alive.sh`.
- `systemd-analyze verify` reported no BUY-31716 unit/timer errors; the only
  output was the known unrelated `/etc/systemd/system/hindsight.service`
  `StartLimitIntervalSec` warning.
- A fresh manual tick ran through the canonical Oracle workspace log and kept all
  8 lanes healthy at `2026-06-09T10:28:31Z`:
  `burst_discovery`, `brand_sitemap_miner`, `retailer_sitemap_miner`,
  `fast_wc_probe`, `shopify_index_expansion`, `crate_deep_page`, `hunt2_page`,
  and `stock_page`.
- The same log shows the restart path firing earlier in this heartbeat at
  `2026-06-09T10:14:27Z`, when the watchdog detected and restarted
  `brand_sitemap_miner`, `retailer_sitemap_miner`, `crate_deep_page`,
  `hunt2_page`, and `stock_page`, followed by an all-green recovery tick at
  `2026-06-09T10:15:01Z`.
- Shared state after the fresh tick:
  - `disk_last_sampled_at=2026-06-09T10:28:31Z`
  - `disk_use_pct=93`
  - `disk_pressure_pauses=10`
  - all per-lane dead counters remained `0`
- Escalation state still contains historical entries only; the most recent entry
  remains `shopify_index_expansion dead_ticks=12 at 2026-06-08T05:51:52Z`.

## Relevant log excerpt

```text
===== BUY-31716 fleet keep-alive tick 2026-06-09T10:14:27Z =====
[2026-06-09T10:14:27Z] host disk use=92% (threshold=95%, recover=90%)
[2026-06-09T10:14:27Z] burst_discovery OK pid=2139271 (no_heartbeat_file)
[2026-06-09T10:14:27Z] brand_sitemap_miner DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:14:29Z] brand_sitemap_miner restarted pid=2146097 (spawned=2146095)
[2026-06-09T10:14:29Z] retailer_sitemap_miner DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:14:31Z] retailer_sitemap_miner restarted pid=2146225 (spawned=2146223)
[2026-06-09T10:14:31Z] crate_deep_page DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:14:34Z] crate_deep_page restarted pid=2146381 (spawned=2146379)
[2026-06-09T10:14:34Z] hunt2_page DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:14:36Z] hunt2_page restarted pid=2146496 (spawned=2146494)
[2026-06-09T10:14:36Z] stock_page DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:14:38Z] stock_page restarted pid=2146632 (spawned=2146630)
[2026-06-09T10:14:38Z] keep-alive tick complete
===== BUY-31716 fleet keep-alive tick 2026-06-09T10:28:30Z =====
[2026-06-09T10:28:31Z] host disk use=93% (threshold=95%, recover=90%)
[2026-06-09T10:28:31Z] burst_discovery OK pid=2139271 (no_heartbeat_file)
[2026-06-09T10:28:31Z] brand_sitemap_miner OK pid=2146097 heartbeat_age=4s
[2026-06-09T10:28:31Z] retailer_sitemap_miner OK pid=2146225 heartbeat_age=1s
[2026-06-09T10:28:31Z] fast_wc_probe OK pid=3848747 (no_heartbeat_file)
[2026-06-09T10:28:31Z] shopify_index_expansion OK pid=3848851 (no_heartbeat_file)
[2026-06-09T10:28:31Z] crate_deep_page OK pid=2146381 (no_heartbeat_file)
[2026-06-09T10:28:31Z] hunt2_page OK pid=2146496 (no_heartbeat_file)
[2026-06-09T10:28:31Z] stock_page OK pid=2146632 (no_heartbeat_file)
[2026-06-09T10:28:31Z] keep-alive tick complete
```
