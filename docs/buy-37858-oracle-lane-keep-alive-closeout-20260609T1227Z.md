# BUY-37858 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T12:27Z)

Issue scope: keep the 5-minute Oracle lane watchdog honest by verifying the
dead-lane restart path in the current workspace and correcting any state that
would falsely escalate healthy recoveries.

## Change

- Updated `scripts/buy30854-lane-keep-alive.sh` so a successful lane restart
  resets that lane's consecutive-dead counter to `0`.
- This prevents `data/buy30854-keep-alive-state.json` from carrying forward
  stale dead counts and escalating a lane that the watchdog already revived on
  the current tick.

## Verification

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
bash scripts/buy30854-lane-keep-alive.sh
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30727-lane-supervisor.mjs'
kill 2751471
bash scripts/buy30854-lane-keep-alive.sh
tail -n 12 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
```

Results:

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported no errors for the repo units; the only
  output remained the unrelated host warning for
  `/etc/systemd/system/hindsight.service`.
- A manual watchdog tick at `2026-06-09T12:26:40Z` observed
  `deep_page_loop` dead and relaunched it successfully.
- Before the fix took effect, that tick still left
  `data/buy30854-keep-alive-state.json` with `"deep_page_loop": 2`, which would
  have incorrectly counted a recovered lane toward escalation.
- After the patch, I killed the live deep-page loop once and reran the watchdog.
  The new tick at `2026-06-09T12:27:19Z` restarted the lane again and left the
  state file fully reset:

```text
===== keep-alive tick 2026-06-09T12:27:19Z =====
[2026-06-09T12:27:19Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=3)
[2026-06-09T12:27:21Z] deep_page_loop restarted pid=2755754 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2755751
[2026-06-09T12:27:21Z] sustained_loop OK pid=2139271
[2026-06-09T12:27:22Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T12:27:22Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T12:27:22Z] keep-alive tick complete
```

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Disposition

`BUY-37858` can close `done`: the Oracle lane keep-alive watchdog still restarts
dead lanes on the 5-minute path, and the consecutive-dead state now clears after
a successful recovery instead of escalating a lane that is already healthy again.
