# BUY-37808 — Oracle lane keep-alive closeout (2026-06-09T12:02:45Z)

Scope: verify that the `BUY-30854` 5-minute Oracle lane keep-alive still
restarts dead Oracle lanes, and correct any state mismatch that would leave the
watchdog advertising stale failures for lanes it no longer owns.

## What changed

- Updated `scripts/buy30854-lane-keep-alive.sh` to prune legacy dead-count
  state for:
  - `buy30745_substrate_supervisor`
  - `buy33243_custom_domain_supervisor`
- The current watchdog only manages `deep_page_loop`, `sustained_loop`,
  `woocommerce_discover`, and `lane_supervisor`, so those stale counters were
  misleading after the scope narrowed.

## Verification

Commands run:

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c bash scripts/buy30854-lane-keep-alive.sh
tail -n 12 /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/logs/buy30854_keep_alive.log
sed -n '1,160p' /paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/buy30854-keep-alive-state.json
```

Results:

- `bash -n` passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` reported no keep-alive unit errors; the only output
  was the known unrelated host warning from `/etc/systemd/system/hindsight.service`.
- The manual tick appended a fresh success block at `2026-06-09T12:02:27Z`:

```text
===== keep-alive tick 2026-06-09T12:02:27Z =====
[2026-06-09T12:02:27Z] deep_page_loop OK pid=2138816
[2026-06-09T12:02:27Z] sustained_loop OK pid=2139271
[2026-06-09T12:02:28Z] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)
[2026-06-09T12:02:28Z] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)
[2026-06-09T12:02:28Z] keep-alive tick complete
```

- Shared watchdog state now matches the active Oracle scope and no longer keeps
  stale legacy lane counters:

```json
{
  "deep_page_loop": 0,
  "disk_last_sampled_at": "2026-06-09T10:08:48Z",
  "disk_pressure_pauses": 186,
  "disk_use_pct": "93",
  "lane_supervisor": 0,
  "last_disk_pressure_marker": "{\"created_at\": \"2026-06-07T01:15:10Z\", \"use_pct\": 95, \"threshold_pct\": 95, \"root\": \"/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c\", \"note\": \"write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)\"}",
  "last_disk_pressure_pause_at": "2026-06-07T06:02:37Z",
  "sustained_loop": 0,
  "woocommerce_discover": 0
}
```

## Conclusion

`BUY-37808` can close `done`: the 5-minute Oracle lane keep-alive still runs in
the active workspace, the current Oracle lanes are healthy on a fresh tick, and
the state file now accurately reflects only the lanes this watchdog owns.
