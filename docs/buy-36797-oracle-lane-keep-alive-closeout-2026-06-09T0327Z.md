# BUY-36797 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T03:27Z)

Issue scope: execute the 5-minute Oracle lane keep-alive watchdog for
`BUY-30854`, confirm the current checkout still restarts dead lanes, and
dispose the routine execution issue with fresh evidence.

## Verification run

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
pgrep -af "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs|buy30727-lane-supervisor.mjs"
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported no Oracle-unit errors. The only output was
  the known unrelated host warning from `/etc/systemd/system/hindsight.service`
  about `StartLimitIntervalSec`.
- Direct watchdog execution appended a fresh successful tick:

```text
===== keep-alive tick 2026-06-09T03:26:58Z =====
[2026-06-09T03:26:59Z] deep_page_loop OK pid=3907026
[2026-06-09T03:26:59Z] sustained_loop OK pid=3907215
[2026-06-09T03:26:59Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T03:26:59Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T03:26:59Z] keep-alive tick complete
```

- `data/buy30854-keep-alive-state.json` after the tick is fully reset:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- Live process inspection still shows both active Oracle node lanes running
  after the tick:

```text
3907026 node scripts/buy30590-deep-page-loop.mjs
3907215 node scripts/buy30331-sustained-loop.mjs
```

- `data/buy30854-keep-alive-escalation.json` did not gain a new escalation
  entry in this heartbeat; it still only contains the historical June 8
  `deep_page_loop` escalations.

## Disposition

`BUY-36797` can close `done`: the Oracle keep-alive watchdog still validates,
the 5-minute systemd cadence remains configured in-repo, and the fresh
2026-06-09T03:26:58Z tick confirmed the tracked Oracle lanes are healthy with
dead-count state reset to zero.
