# BUY-37583 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T10:16:54Z)

Issue scope: verify that the Oracle lane keep-alive still restarts dead lanes on
a 5-minute cadence and leaves the active workspace healthy enough to close this
lane keep-alive execution issue.

## Verification run

- `bash -n scripts/buy30854-lane-keep-alive.sh`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`

## Fresh runtime evidence

The manual keep-alive tick appended this block to
`logs/buy30854_keep_alive.log`:

```text
===== keep-alive tick 2026-06-09T10:16:54Z =====
[2026-06-09T10:16:54Z] deep_page_loop OK pid=2138816
[2026-06-09T10:16:54Z] sustained_loop OK pid=2139271
[2026-06-09T10:16:54Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T10:16:54Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T10:16:54Z] keep-alive tick complete
```

The same log also proves the dead-lane restart path fired today before this
verification pass:

```text
===== keep-alive tick 2026-06-09T10:09:25Z =====
[2026-06-09T10:09:25Z] deep_page_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:09:27Z] deep_page_loop restarted pid=2119031 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2119028
[2026-06-09T10:09:27Z] sustained_loop DEAD — restarting (consecutive_dead_ticks=1)
[2026-06-09T10:09:29Z] sustained_loop restarted pid=2119205 root=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c spawned=2119202
```

Current state in `data/buy30854-keep-alive-state.json`:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

## Notes

- `systemd/paperclip-lane-keep-alive.timer` still sets `OnUnitActiveSec=5min`
  with `Persistent=true`.
- `systemd-analyze verify` reported only the known unrelated host warning for
  `/etc/systemd/system/hindsight.service`; no keep-alive service or timer errors
  were reported.

## Disposition

This execution issue can close `done`: the watchdog remains installed in-repo,
the restart path executed successfully on `2026-06-09`, and the latest manual
tick ended with both tracked Oracle lanes healthy.
