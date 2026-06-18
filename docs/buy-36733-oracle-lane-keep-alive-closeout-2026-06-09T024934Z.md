# BUY-36733 — Oracle lane keep-alive closeout (2026-06-09T02:49:34Z)

Issue scope: verify the `BUY-30854` Oracle lane keep-alive still restarts dead
lanes on the 5-minute cadence and remains healthy after the latest recovery.

## Commands

```bash
bash -n scripts/buy30854-lane-keep-alive.sh
bash scripts/buy30854-lane-keep-alive.sh
systemd-analyze verify systemd/paperclip-lane-keep-alive.service systemd/paperclip-lane-keep-alive.timer
tail -n 20 logs/buy30854_keep_alive.log
cat data/buy30854-keep-alive-state.json
pgrep -af 'buy30590-deep-page-loop.mjs|buy30331-sustained-loop.mjs|buy30590-woocommerce-discover.mjs'
```

## Results

- `bash -n` passed.
- A fresh watchdog tick completed at `2026-06-09T02:49:34Z`.
- The live log shows a real recovery earlier in the same run window:
  - `2026-06-09T02:19:33Z` restarted `deep_page_loop`
  - `2026-06-09T02:19:35Z` restarted `sustained_loop`
- Subsequent 5-minute ticks remained healthy through `2026-06-09T02:49:34Z`.
- `data/buy30854-keep-alive-state.json` remained:

```json
{
  "deep_page_loop": 0,
  "sustained_loop": 0,
  "woocommerce_discover": 0,
  "lane_supervisor": 0
}
```

- `pgrep` confirmed both active Oracle lane processes:

```text
3907026 node scripts/buy30590-deep-page-loop.mjs
3907215 node scripts/buy30331-sustained-loop.mjs
```

- `systemd-analyze verify` reported no errors for the Oracle watchdog units. The
  only output was an unrelated warning from `/etc/systemd/system/hindsight.service`
  about `StartLimitIntervalSec` being in the wrong section.

## Conclusion

`BUY-36733` can close `done`: the Oracle keep-alive watchdog is live, proved an
actual dead-lane restart on 2026-06-09, and continued healthy 5-minute ticks
after recovery.
