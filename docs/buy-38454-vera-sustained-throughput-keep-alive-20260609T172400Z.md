# BUY-38454 — Vera sustained throughput keep-alive closeout (2026-06-09T17:24:00Z)

Issue scope: execute the `BUY-30854` Oracle lane keep-alive watchdog, confirm
the 5-minute watchdog path remains intact, and leave fresh heartbeat evidence
for the sustained-throughput lane set.

## Commands run

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
ps -eo pid,ppid,pgid,sid,etimes,cmd | rg 'buy30331-sustained-loop|buy30590-deep-page-loop|buy30727-lane-supervisor|buy30590-woocommerce-discover'
sed -n '1,120p' systemd/paperclip-lane-keep-alive.timer
```

## Verification

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
  reported only the known unrelated `/etc/systemd/system/hindsight.service`
  warning about `StartLimitIntervalSec`; there were no errors for the Oracle
  keep-alive service or timer.
- `systemd/paperclip-lane-keep-alive.timer` still enforces the watchdog cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.
- `bash scripts/buy30854-lane-keep-alive.sh` completed successfully and wrote a
  fresh keep-alive block ending at `2026-06-09T17:24:00Z`.

Fresh log proof:

```text
===== keep-alive tick 2026-06-09T17:24:00Z =====
[2026-06-09T17:24:00Z] deep_page_loop STOPPED (already absent)
[2026-06-09T17:24:00Z] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)
[2026-06-09T17:24:00Z] sustained_loop OK pid=3782962
[2026-06-09T17:24:00Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T17:24:00Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T17:24:00Z] keep-alive tick complete
```

Current tracked state after the fresh tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

Current process snapshot:

```text
3782959       1 3782959 3782959     155 bash -c node scripts/buy30331-sustained-loop.mjs & wait
3782962 3782959 3782959 3782959     155 node scripts/buy30331-sustained-loop.mjs
3787230 3770355 3787230 3787230     102 node /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/buy30590-woocommerce-discover.mjs --concurrency=20 --lane-name=buy30745_woocommerce_woo_75k_5k --pool-key=woo_75k_5k --checkpoint-file=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/checkpoints/buy30745_woocommerce_woo_75k_5k.json woo_75k_5k --start=75000 --count=5000
```

The local watchdog-managed lanes remain in the expected state: the sustained
loop is live in this workspace, while deep page, the legacy supervisor, and the
local WooCommerce discover lane are intentionally skipped because their stop or
completion markers remain present. The extra WooCommerce process shown above is
from a different workspace and does not affect this routine execution.

## Conclusion

`BUY-38454` can close `done`: the Oracle keep-alive watchdog ran cleanly in
this heartbeat, the 5-minute timer path is still valid, the local sustained
loop remained healthy, and all tracked dead-count state was reset to zero.
