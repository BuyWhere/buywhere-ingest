# BUY-37030 — Vera sustained throughput keep-alive heartbeat (2026-06-09T05:26:51Z)

Routine execution issue for the 5-minute `BUY-30854` lane keep-alive watchdog.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
ps -eo pid,ppid,etimes,cmd | rg 'buy30590-deep-page-loop|buy30331-sustained-loop'
cat data/buy30854-keep-alive-state.json
python3 - <<'PY'
import json
from pathlib import Path
p = Path('data/buy30854-keep-alive-escalation.json')
obj = json.loads(p.read_text()) if p.exists() else {'escalations': []}
arr = obj.get('escalations', [])
print(f'count={len(arr)}')
if arr:
    import json as _json
    print(_json.dumps(arr[-1], indent=2))
PY
bash scripts/buy30854-lane-keep-alive.sh
tail -n 24 logs/buy30854_keep_alive.log
bash scripts/buy30854-lane-keep-alive.sh
tail -n 16 logs/buy30854_keep_alive.log
ps -eo pid,ppid,etimes,args | rg 'buy30590-deep-page-loop|buy30331-sustained-loop'
```

## Result

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- The first explicit tick at `2026-06-09T05:26:04Z` found `deep_page_loop` duplicated, killed pid `3907026`, and reported the older survivor as pid `374655`.
- A second explicit tick at `2026-06-09T05:26:32Z` then found `deep_page_loop` absent and relaunched it successfully as pid `375929`.
- `sustained_loop` stayed healthy throughout at pid `3907215`.
- `woocommerce_discover` remained intentionally skipped because `data/checkpoints/buy30590_woocommerce.completed` is present.
- `lane_supervisor` remained intentionally skipped because `data/buy30727-supervisor.stopped` is present per `BUY-31452`.
- Dead-count state finished reset to zero for all tracked lanes.
- No new escalation was emitted; the escalation file still ends with the historical `deep_page_loop` entry from `2026-06-08T21:21:49Z`.

## Evidence

Latest keep-alive log block:

```text
===== keep-alive tick 2026-06-09T05:26:04Z =====
[2026-06-09T05:26:04Z] duplicate buy30590-deep-page-loop.mjs killed pid=3907026 (kept 374655)
[2026-06-09T05:26:04Z] deep_page_loop OK pid=374655
[2026-06-09T05:26:04Z] sustained_loop OK pid=3907215
[2026-06-09T05:26:04Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T05:26:04Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T05:26:04Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T05:26:32Z =====
[2026-06-09T05:26:32Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T05:26:34Z] deep_page_loop restarted pid=375929 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=375926
[2026-06-09T05:26:35Z] sustained_loop OK pid=3907215
[2026-06-09T05:26:35Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T05:26:35Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T05:26:35Z] keep-alive tick complete
```

Tracked processes after the relaunch:

```text
375926       1       2 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
375929  375926       2 node scripts/buy30590-deep-page-loop.mjs
3907212       1   11221 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
3907215 3907212   11221 node scripts/buy30331-sustained-loop.mjs
```

State file after the relaunch tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

Latest escalation entry remains unchanged:

```json
{
  "lane": "deep_page_loop",
  "dead_ticks": 8,
  "at": "2026-06-08T21:21:49Z",
  "note": "lane DEAD on >=4 consecutive keep-alive ticks; escalate to parent BUY-30854 with diagnostic context"
}
```
