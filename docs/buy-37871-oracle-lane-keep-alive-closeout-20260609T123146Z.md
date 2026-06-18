# BUY-37871 — Oracle lane keep-alive closeout (2026-06-09T12:31:46Z)

Scope: verify that the `BUY-30854` 5-minute Oracle lane keep-alive is still
active, still restarts dead Oracle lanes, and still returns to a clean state
after a fresh watchdog tick in this heartbeat.

## Verification

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default bash scripts/buy30854-lane-keep-alive.sh
tail -n 40 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
cat data/buy30854-keep-alive-escalation.json
```

Results:

- `bash -n scripts/buy30854-lane-keep-alive.sh` passed.
- `systemd-analyze verify` reported no keep-alive unit or timer errors; the
  only output was the known unrelated host warning from
  `/etc/systemd/system/hindsight.service`.
- The manual watchdog run in this heartbeat completed successfully and the live
  log advanced through a healthy tick at `2026-06-09T12:31:24Z`:

```text
===== keep-alive tick 2026-06-09T12:31:24Z =====
[2026-06-09T12:31:24Z] deep_page_loop OK pid=2776061
[2026-06-09T12:31:24Z] sustained_loop OK pid=2775043
[2026-06-09T12:31:24Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T12:31:24Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T12:31:24Z] keep-alive tick complete
```

- This heartbeat also captured fresh live restart proof for the dead-lane path.
  `deep_page_loop` died and was successfully relaunched multiple times before
  recovering cleanly:

```text
[2026-06-09T12:23:46Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T12:23:48Z] deep_page_loop restarted pid=2733361 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2733358
[2026-06-09T12:26:40Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=2)
[2026-06-09T12:26:42Z] deep_page_loop restarted pid=2751471 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2751468
[2026-06-09T12:27:19Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=3)
[2026-06-09T12:27:21Z] deep_page_loop restarted pid=2755754 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2755751
[2026-06-09T12:30:38Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T12:30:40Z] deep_page_loop restarted pid=2776061 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2776058
```

- `data/buy30854-keep-alive-state.json` is clean after the successful recovery
  and healthy tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `data/buy30854-keep-alive-escalation.json` did not gain a new escalation in
  this heartbeat; it still contains only the earlier historical entries from
  `2026-06-08`.

## Conclusion

`BUY-37871` can close `done`: the Oracle watchdog remains on its 5-minute
cadence, it actively restarted a dead Oracle lane multiple times during this
heartbeat, and it returned the tracked lane state to zero after the lane
recovered.
