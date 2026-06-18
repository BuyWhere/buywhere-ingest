Acknowledged — closing as cancelled per Rich's directive and Ops's verification. Final Oracle disposition.

## Final state on this host

- 0 of 5 prepared units in `/etc/systemd/system/` (only Ops's unrelated `paperclip-*` units: disk-guard, fleet-sweep, kill-watcher, runaway-killer, scraper-corral, sigkill-trap)
- `data/buy30727-supervisor.stopped` present (Jun 5 20:44) — CC supervisor stays dead as intended per [BUY-31452](/BUY/issues/BUY-31452)
- Active productive lanes alive: `node scripts/buy30331-sustained-loop.mjs` (PID 2918087, ~3.5h uptime) and `node scripts/buy30590-deep-page-loop.mjs` (PID 2923321, ~3.5h uptime)
- 2-min cron `bash scripts/buy30854-lane-keep-alive.sh` (PID 2918086 → 2918087) is the live supervision mechanism per [BUY-30854](/BUY/issues/BUY-30854)
- Lane uptimes of 3.5h indicate the 2-min keep-alive is currently absorbing the 20-30 min heartbeat-cgroup-kill windows

## What I'm NOT doing

- Not redeploying any of the 5 units (Rich's explicit directive)
- Not creating duplicate work for the 4 units not covered by Rich's buy30727 test (loop-supervisor, buy30331, buy30590, lane-keep-alive)
- Not re-opening the systemd durability question unless evidence shows a >2-min gap that the bash keep-alive missed

## Downstream follow-up (separate heartbeat)

[BUY-31847](/BUY/issues/BUY-31847) is assigned to me and is `blocked` on this issue. Per Paperclip rules, `cancelled` blockers do not auto-resolve dependents. If the 2-min bash keep-alive is the durable answer to the heartbeat-cgroup-kill gap (which current lane uptimes suggest), [BUY-31847](/BUY/issues/BUY-31847) can be closed independently with a note pointing at the keep-alive. Tracking that on [BUY-31847](/BUY/issues/BUY-31847) in a later heartbeat.

## Note on original scope vs. Rich's test

For the record: the original issue scoped 5 units. Rich's deploy+test+remove cycle was on `buy30727-supervisor.service` alone — the only unit with a stop-marker conflict. The other 4 units (loop-supervisor, buy30331-sustained-loop, buy30590-deep-page-loop, lane-keep-alive) do not have stop-marker conflicts and could be deployed without the BUY-31452 collision. Closing as cancelled per the user's directive regardless; flagging here so the partial scope is on the record in case the heartbeat-cgroup-kill gap re-emerges later.

— Oracle (final disposition)
