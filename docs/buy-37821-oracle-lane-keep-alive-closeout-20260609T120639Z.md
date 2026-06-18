# BUY-37821 — Oracle lane keep-alive closeout (2026-06-09T12:06:39Z)

Scope: verify that the `BUY-30854` 5-minute Oracle lane keep-alive is still
active, still restarts dead Oracle lanes, and still leaves clean watchdog
state after a fresh tick.

## Verification

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
rg -n "restarted pid=|DEAD — restarting" logs/buy30854_keep_alive.log | tail -n 20
```

Results:

- `bash -n` passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` reported no keep-alive unit or timer errors; the
  only output was the known unrelated host warning from
  `/etc/systemd/system/hindsight.service`.
- A fresh manual tick completed at `2026-06-09T12:06:39Z` with both active
  Oracle lanes healthy, the completed WooCommerce lane intentionally skipped,
  and the supervisor intentionally skipped behind its BUY-31452 stop marker:

```text
===== keep-alive tick 2026-06-09T12:06:39Z =====
[2026-06-09T12:06:39Z] deep_page_loop OK pid=2138816
[2026-06-09T12:06:39Z] sustained_loop OK pid=2139271
[2026-06-09T12:06:39Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T12:06:39Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T12:06:39Z] keep-alive tick complete
```

- The watchdog log shows the cadence continuing through this heartbeat, with
  recent ticks at `2026-06-09T11:58:17Z`, `2026-06-09T12:04:55Z`, and
  `2026-06-09T12:06:39Z`.
- The restart path has fired successfully in production today. The latest live
  restart evidence in the log is:

```text
[2026-06-09T10:12:57Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=2)
[2026-06-09T10:12:59Z] deep_page_loop restarted pid=2138816 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2138813
[2026-06-09T10:12:59Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=2)
[2026-06-09T10:13:01Z] sustained_loop restarted pid=2139271 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2139268
```

- The watchdog state file is clean after the fresh tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Conclusion

`BUY-37821` can close `done`: the Oracle keep-alive remains on its 5-minute
cadence, the active lanes are healthy on a fresh manual tick, and the dead-lane
restart path has demonstrably relaunched Oracle lanes in production today.
