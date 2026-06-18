# BUY-36920 — Vera sustained throughput keep-alive heartbeat (2026-06-09T04:34:12Z)

Routine execution issue for the 5-minute `BUY-30854` lane keep-alive watchdog.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
bash scripts/buy30854-lane-keep-alive.sh
tail -n 12 logs/buy30854_keep_alive.log
ps -eo pid,ppid,etimes,cmd | rg '^\s*[0-9]+\s+[0-9]+\s+[0-9]+\s+(bash -lc exec 9>&-|node scripts/(buy30590-deep-page-loop|buy30331-sustained-loop)\.mjs)'
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
```

## Result

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- The explicit heartbeat tick completed at `2026-06-09T04:34:12Z`.
- `deep_page_loop` stayed healthy at pid `3907026`.
- `sustained_loop` stayed healthy at pid `3907215`.
- `woocommerce_discover` remained intentionally skipped because `data/checkpoints/buy30590_woocommerce.completed` is present.
- `lane_supervisor` remained intentionally skipped because `data/buy30727-supervisor.stopped` is present per `BUY-31452`.
- Dead-count state is fully reset to zero for all tracked lanes.
- No new escalation was emitted by this tick; the escalation file still ends with the historical `deep_page_loop` entry from `2026-06-08T21:21:49Z`.

## Evidence

Latest keep-alive log block:

```text
===== keep-alive tick 2026-06-09T04:34:03Z =====
[2026-06-09T04:34:03Z] deep_page_loop OK pid=3907026
[2026-06-09T04:34:03Z] sustained_loop OK pid=3907215
[2026-06-09T04:34:03Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T04:34:03Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T04:34:03Z] keep-alive tick complete
===== keep-alive tick 2026-06-09T04:34:12Z =====
[2026-06-09T04:34:12Z] deep_page_loop OK pid=3907026
[2026-06-09T04:34:12Z] sustained_loop OK pid=3907215
[2026-06-09T04:34:12Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T04:34:12Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T04:34:12Z] keep-alive tick complete
```

Tracked processes after the tick:

```text
3907023       1    8087 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
3907026 3907023    8087 node scripts/buy30590-deep-page-loop.mjs
3907212       1    8085 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
3907215 3907212    8085 node scripts/buy30331-sustained-loop.mjs
```

State file after the tick:

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
