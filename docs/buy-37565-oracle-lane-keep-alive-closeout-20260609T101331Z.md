# BUY-37565 — BUY-30854 Oracle lane keep-alive closeout (2026-06-09T10:13:31Z)

Issue scope: verify that the Oracle 5-minute keep-alive path still detects dead
lanes and restarts them successfully for `BUY-30854`.

## Commands

- `bash scripts/buy30854-lane-keep-alive.sh`
- `bash scripts/buy30854-lane-keep-alive.sh`
- `systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer`
- `cat data/buy30854-keep-alive-state.json`
- `pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs'`

## Observations

- The keep-alive tick at `2026-06-09T10:12:57Z` detected both active Oracle
  lanes dead and restarted them:
  - `deep_page_loop` restarted as pid `2138816`
  - `sustained_loop` restarted as pid `2139271`
- The follow-up keep-alive tick at `2026-06-09T10:13:31Z` observed both
  replacement processes healthy:
  - `deep_page_loop OK pid=2138816`
  - `sustained_loop OK pid=2139271`
- `data/buy30854-keep-alive-state.json` reset all tracked dead counters to zero
  after the healthy tick:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `woocommerce_discover` remained intentionally skipped because
  `data/checkpoints/buy30590_woocommerce.completed` is present.
- `lane_supervisor` remained intentionally skipped because
  `data/buy30727-supervisor.stopped` is present for `BUY-31452`.
- `pgrep` immediately after the healthy tick showed both relaunched workers
  still resident:

```text
2138813 bash -lc exec 9>&-; node scripts/buy30590-deep-page-loop.mjs & wait
2138816 node scripts/buy30590-deep-page-loop.mjs
2139268 bash -lc exec 9>&-; node scripts/buy30331-sustained-loop.mjs & wait
2139271 node scripts/buy30331-sustained-loop.mjs
```

- `systemd-analyze verify` reported only the known unrelated warning from
  `/etc/systemd/system/hindsight.service` and no error for
  `paperclip-lane-keep-alive.service` or `.timer`.

## Conclusion

`BUY-37565` can close `done`. This heartbeat produced a direct proof of the
required behavior: the Oracle keep-alive detected dead lanes on the watchdog
cadence, restarted both of them, and the next tick confirmed the replacements
were alive with watchdog state cleared back to zero.
