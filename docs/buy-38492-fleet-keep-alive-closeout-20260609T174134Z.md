# BUY-38492 — BUY-31716 fleet keep-alive closeout (2026-06-09T17:41:34Z)

Issue scope: verify the active 5-minute BUY-31716 fleet keep-alive for the 8
discovery lanes and leave fresh runtime evidence.

## Commands run

```bash
bash -n scripts/buy31716-fleet-keep-alive.sh
systemd-analyze verify systemd/paperclip-buy31716-fleet-keep-alive.service systemd/paperclip-buy31716-fleet-keep-alive.timer
bash scripts/buy31716-fleet-keep-alive.sh
sed -n '1,220p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy31716-fleet-keep-alive-state.json
tail -n 40 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy31716_fleet_keep_alive.log
```

## Verification

- `scripts/buy31716-fleet-keep-alive.sh` passed `bash -n`.
- `systemd-analyze verify` reported only the known unrelated
  `/etc/systemd/system/hindsight.service` warning about
  `StartLimitIntervalSec`; the BUY-31716 service and timer verified cleanly.
- A fresh manual keep-alive tick completed at `2026-06-09T17:41:34Z`.
- The active lanes were healthy on that tick:
  `burst_discovery`, `fast_wc_probe`, `shopify_index_expansion`,
  `crate_deep_page`, `hunt2_page`, and `stock_page`.
- The two sitemap lanes were intentionally skipped by their stop markers:
  `data/buy30590-brand-sitemap-miner.stopped` and
  `data/buy30590-retailer-sitemap-loop.stopped`, both carrying the
  `BUY-34200` stop reason.
- Shared state advanced to
  `disk_last_sampled_at=2026-06-09T17:41:34Z`, retained `disk_use_pct=91`,
  and all tracked lane dead counts were `0`.

## Live restart evidence from this heartbeat window

- The same canonical keep-alive log shows a real restart during today’s run:
  `burst_discovery` was detected dead at `2026-06-09T17:21:37Z`,
  relaunched at `2026-06-09T17:21:39Z`, and then recorded healthy on
  subsequent ticks at `2026-06-09T17:22:02Z`, `2026-06-09T17:26:27Z`,
  `2026-06-09T17:31:30Z`, `2026-06-09T17:36:25Z`, and the manual
  verification tick at `2026-06-09T17:41:34Z`.
- `data/buy31716-fleet-keep-alive-escalation.json` did not gain a new entry
  during this verification; its contents remain the historical June 8
  escalation records.

## Conclusion

`BUY-38492` can close `done`: the 5-minute fleet watchdog remains wired to the
canonical script and timer, it still performs live restarts when a lane dies,
and the latest verification tick shows the fleet healthy within the intended
steady-state exceptions for the two BUY-34200 stop-marked sitemap lanes.
