# BUY-36789 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T03:25Z)

Issue scope: confirm the Oracle 5-minute lane keep-alive for `BUY-30854`
still performs dead-lane restarts and remains healthy in the current checkout.

## Verified implementation

- `scripts/buy30854-lane-keep-alive.sh` is the active watchdog and still
  contains:
  - per-lane dead-tick state persisted in `data/buy30854-keep-alive-state.json`
  - escalation logging in `data/buy30854-keep-alive-escalation.json`
  - detached relaunches that explicitly close FD 9 before restarting a lane,
    preventing lock inheritance from `data/buy30854-keep-alive.lock`
- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a
  `Type=oneshot` service in this Oracle checkout.
- `systemd/paperclip-lane-keep-alive.timer` preserves the 5-minute cadence via
  `OnUnitActiveSec=5min` with `Persistent=true`.

## Commands run

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
pgrep -af "buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30727-lane-supervisor.mjs|buy30590-woocommerce-discover.mjs"
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported no errors for the Oracle keep-alive unit or
  timer; the only output was the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`.
- Direct watchdog execution appended a fresh verification tick:

```text
===== keep-alive tick 2026-06-09T03:24:43Z =====
[2026-06-09T03:24:43Z] deep_page_loop OK pid=3907026
[2026-06-09T03:24:44Z] sustained_loop OK pid=3907215
[2026-06-09T03:24:44Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T03:24:44Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T03:24:44Z] keep-alive tick complete
```

- The current keep-alive state is fully reset to zero dead ticks:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- Live process inspection after the tick still showed the two active Oracle
  lanes running:

```text
3907026 node scripts/buy30590-deep-page-loop.mjs
3907215 node scripts/buy30331-sustained-loop.mjs
```

- `data/buy30854-keep-alive-escalation.json` still only contains the historical
  June 8 `deep_page_loop` escalations; this verification heartbeat added no new
  escalation entry.

## Disposition

`BUY-36789` can close `done`: the Oracle keep-alive watchdog and 5-minute
systemd timer remain wired in the current checkout, and the fresh verification
tick at `2026-06-09T03:24:43Z` confirmed the tracked Oracle lanes are healthy.
