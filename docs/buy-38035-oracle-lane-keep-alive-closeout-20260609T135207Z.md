# BUY-38035 — Oracle lane keep-alive closeout (2026-06-09T13:52:07Z)

Issue scope: verify that the `BUY-30854` Oracle lane watchdog still provides a
5-minute restart path for dead lanes and that the current runtime state matches
the intended stop/completion markers.

## Evidence

- `scripts/buy30854-lane-keep-alive.sh:217-263` still contains the dead-lane
  restart path, including detached relaunch and escalation tracking.
- `scripts/buy30854-lane-keep-alive.sh:288-342` still wraps the watchdog in a
  non-blocking flock and applies the current stop/completion marker rules for
  `deep_page_loop`, `woocommerce_discover`, and `lane_supervisor`.
- `systemd/paperclip-lane-keep-alive.service:9-19` runs the watchdog as a
  `Type=oneshot` service.
- `systemd/paperclip-lane-keep-alive.timer:4-7` preserves the 5-minute cadence
  with `OnUnitActiveSec=5min` and `Persistent=true`.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
WORKSPACE_ROOT=/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default bash scripts/buy30854-lane-keep-alive.sh
sed -n '1,160p' data/buy30854-keep-alive-state.json
tail -n 20 logs/buy30854_keep_alive.log
stat -c '%y %n' \
  data/buy30590-deep-page-loop.stopped \
  data/buy30727-supervisor.stopped \
  data/checkpoints/buy30590_woocommerce.completed \
  data/buy30854-keep-alive-state.json \
  logs/buy30854_keep_alive.log
```

## Results

- `bash -n` passed for `scripts/buy30854-lane-keep-alive.sh`.
- `systemd-analyze verify` reported only the known unrelated
  `/etc/systemd/system/hindsight.service` warning; there was no keep-alive unit
  or timer error.
- A fresh manual keep-alive tick completed at `2026-06-09T13:51:58Z`.
- The fresh tick reported:
  - `deep_page_loop` intentionally skipped because
    `data/buy30590-deep-page-loop.stopped` exists and was last updated at
    `2026-06-09 12:32:23 +0000`.
  - `sustained_loop` healthy at pid `2775043`.
  - `woocommerce_discover` intentionally skipped because
    `data/checkpoints/buy30590_woocommerce.completed` exists.
  - `lane_supervisor` intentionally skipped because
    `data/buy30727-supervisor.stopped` exists.
- `data/buy30854-keep-alive-state.json` was updated at
  `2026-06-09 13:51:58 +0000` and shows zero dead counts for all tracked lanes:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `logs/buy30854_keep_alive.log` was updated at `2026-06-09 13:51:58 +0000`
  and the latest block ends with `keep-alive tick complete`.

## Disposition

`BUY-38035` can close `done`: the Oracle keep-alive remains wired as a
5-minute systemd watchdog, the dead-lane restart path is present in the script,
and the latest manual tick confirmed the active lane and intentional stop paths
are behaving as expected.
