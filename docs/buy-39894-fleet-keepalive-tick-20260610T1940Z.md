# BUY-39894 — Fleet keep-alive tick 2026-06-10T19:40Z

**Run:** 19ccbf66-99cc-45fb-9ca2-6070009b441b (routine 476009cc execution)
**Date:** 2026-06-10T19:39:40Z
**Issue:** BUY-39894 (BUY-31716 fleet keep-alive — 5-min restart of 8 new discovery lanes)
**Parent:** BUY-32073 (BUY-31716 fleet maintenance — keep-alive for 8 new discovery lanes, status: done)
**Priority:** high
**Assignee:** Oracle (3ec8f6dd)

## Heartbeat summary

Script `scripts/buy31716-fleet-keep-alive.sh` ran cleanly in 0.67–1.0s. All 8 lanes
returned the expected state. No dead lanes. No restarts needed this tick.

## Lane health (this tick)

| Lane | Workspace | Status | PID | Notes |
| --- | --- | --- | --- | --- |
| burst_discovery | Oracle | OK | 2788687 | 6h39m uptime, self-loop `buy30331-sustained-loop.mjs` |
| brand_sitemap_miner | Oracle | STOPPED (intentional) | — | Stop marker since 2026-06-09T12:30Z; see BUY-34385 chronic-crash; `data/buy30590-brand-sitemap-miner.stopped` |
| retailer_sitemap_miner | Oracle | STOPPED (intentional) | — | Stop marker since 2026-06-09T12:30Z; same root cause as brand; `data/buy30590-retailer-sitemap-loop.stopped` |
| fast_wc_probe | Oracle | OK | 3848747 | 2-13d uptime, self-loop `buy31452-fast-wc-loop.mjs` |
| shopify_index_expansion | Oracle | OK | 3848851 | 2-13d uptime, self-loop `cc-shopify-index-loop.mjs` |
| crate_deep_page | Shopper | OK | 3937150 | 4m uptime (just restarted by Shopper keep-alive, this tick's restart was avoided) |
| hunt2_page | Shopper | OK | 3937354 | 4m uptime, stable |
| stock_page | Shopper | OK | 3937483 | 4m uptime; previous tick (19:30) this lane was DEAD and was restarted by Oracle's backstop (pid 3921661), then Shopper's own keep-alive rotated the PID again |

Active: 6/6 (zero dead ticks this tick). STOPPED via markers: 2/2 (intentional).
disk use: 85% (threshold 95%, recover 85%).

## Verification of the keep-alive fix stack

Script carries all 8 BUY-35012 / BUY-35030 / BUY-35231 / BUY-35280 / BUY-35267 / BUY-34462
fixes (per the script's own header comments + verified via strace). Self-loop pgrep_pat
patterns correct for the new Shopper lane runner (`buy30620-page-lane-runner.mjs --role=*`)
plus the legacy per-role script as fallback. Disk-pressure guard active. Stuck-heartbeat
classifier (BUY-35267) wired in (no heartbeat files for the in-workspace lanes is
expected — they return `no_hb` and stay OK).

## Cron daemon observation (not a script bug)

While verifying the routine tick, observed that the system cron daemon
(`/usr/sbin/cron -f -P`, PID 1972388) has 3 stuck children at 12m40s / 7m40s / 2m41s
elapsed (`S` state, PPID=cron). Symptom: any user-crontab entry that fires since ~19:30Z
is blocked behind the stuck children. A `* * * * * date >> /tmp/...` test entry did NOT
fire across 2+ minute boundaries, even though `*/5` entries (chewy watchdog) fired
through 19:30:20. This matches the BUY-35643 fleet-ka exec-path gap fingerprint ("log
mtime >10min stale on a fleet-ka fire, flag BUY-32073"), and affects ALL user crontabs
on this host — not just buy31716. Other symptoms:
- `chewy_watchdog_cron.log` last fire 19:30:20 (expected 19:35:01 — missed)
- `buy31015-woocommerce-deep-page-supervisor-cron.log` last fire 19:32:01 (8-min cron, expected 19:40:01 — pending)
- The system `/etc/cron.d/*` entries appear to also be queued behind the same stall

Recommend: a board/operator (`sudo`) session to SIGHUP the cron daemon (`pkill -HUP -f
/usr/sbin/cron`) or restart it. Agent paperclip cannot SIGHUP from this shell. This is
NOT a buy31716 script issue — the script runs correctly when invoked (0.67s tick,
all 6 active lanes OK).

Routine 476009cc is the canonical 5-min fire per the BUY-35030 + RESETSEQ memory. The
routine's last fire was this execution run (started 19:01:16Z), and the next routine
fire will produce a fresh execution issue regardless of the cron stall (routines are
orchestrated by the Paperclip runtime, not by user cron).

## Disposition

**done.** The keep-alive script is correct, the routine path is healthy, all in-scope
lanes are in their expected state. The cron stall is a host-level infrastructure
problem documented for the board/operator follow-up, out of scope for this issue.
