# BUY-36542 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T00:58Z)

Issue scope: confirm the Oracle 5-minute lane keep-alive for `BUY-30854`
still performs dead-lane restarts and remains healthy in the current checkout.

## Verified implementation

- `scripts/buy30854-lane-keep-alive.sh` contains the watchdog logic for:
  - per-lane dead-tick state in `data/buy30854-keep-alive-state.json`
  - escalation logging in `data/buy30854-keep-alive-escalation.json`
  - detached relaunches that explicitly close FD 9 before restarting a lane,
    preventing lock inheritance from `data/buy30854-keep-alive.lock`
- `systemd/paperclip-lane-keep-alive.service` runs the watchdog as a
  `Type=oneshot` service in the Oracle checkout.
- `systemd/paperclip-lane-keep-alive.timer` sets the 5-minute cadence via
  `OnUnitActiveSec=5min` with `Persistent=true`.

## Commands run

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
tail -n 30 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
```

## Results

- `bash -n` passed.
- `systemd-analyze verify` reported no keep-alive unit errors; the only output
  was the known unrelated host warning for `/etc/systemd/system/hindsight.service`.
- Direct watchdog execution appended a fresh tick:

```text
===== keep-alive tick 2026-06-09T00:58:42Z =====
[2026-06-09T00:58:42Z] deep_page_loop OK pid=2778633
[2026-06-09T00:58:43Z] sustained_loop OK pid=2691392
[2026-06-09T00:58:43Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T00:58:43Z] keep-alive tick complete
```

- The shared keep-alive state after the tick is:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 2
}
```

- The existing escalation file still records the earlier June 8 deep-page
  incidents, but no new escalation was emitted by this verification tick.

## Disposition

`BUY-36542` can close `done`: the Oracle keep-alive watchdog is implemented in
this checkout, the 5-minute systemd timer wiring is present, and a fresh
verification tick on 2026-06-09 confirmed the tracked active lanes remained
healthy.
