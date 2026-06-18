# Daily Product Target Shortfall Report

Date: 2026-06-11 UTC (in progress, ~13.5h into the closed day window)
Issue: BUY-38967 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Oracle (3ec8f6dd)
Collected at: 2026-06-11 13:32:44 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-12` through `2026-06-30`, which is `19` calendar days. (Today's `2026-06-11`
is in progress and cannot yet be classified as a missed day.)

A "missed day" is a closed UTC day whose active-product growth fell below the required
pace at the start of that day. Today's report covers:

- Closed-day `2026-06-10` verdict (filed yesterday, referenced for continuity)
- In-progress `2026-06-11` pulse (cannot yet be classified; no failure report filed)
- Forward required pace off the `2026-06-11 13:32:44Z` catalog reading

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url` (workspace pin, not harness env)
- URL used: `postgresql://buywhere_ingest:MommMnA7BUR3yo6qkPDO0vhxoOh6IQee@maglev.proxy.rlwy.net:31310/railway?sslmode=require` (parses to host `maglev.proxy.rlwy.net:31310/railway`, NOT roundhouse)
- DB target guard: `current_database()=railway` confirmed; control-plane DB correctly NOT in use
- Sanity check: `n_live_tup ≈ 73.2M` and DB size `131 GB` — this is the canonical maglev catalog, far above the `~2.7M` wrong-DB guard the issue description warns about
- Live count note: exact full-table `SELECT COUNT(*) FROM products` is too expensive to refresh inside a heartbeat (consistent with the [BUY-32950](/BUY/issues/BUY-32950) cap and the 2026-06-07/2026-06-08/2026-06-09/2026-06-10 prior reports). For this report, the live count is the `pg_stat_user_tables.products.n_live_tup` reading as an explicit approximation, cross-checked against the `n_tup_ins` delta from the dispatcher's `data/.throughput_state.json`.
- Index state: `products_created_at_idx` is `indisvalid=f, indisready=f` (still INVALID — [BUY-32878](/BUY/issues/BUY-32878) central tracker [BUY-33973](/BUY/issues/BUY-33973); maglev DDL is ops-only per charter Rule 14). All `WHERE created_at` queries still seq-scan; the daily verdict therefore relies on `n_tup_ins` (running counter since the BUY-35444 postmaster restart on `2026-06-08 10:21:09Z`) plus the `n_live_tup` estimate, exactly as the BUY-33694 dispatcher primary-signal path uses.

Live maglev snapshot used (at `2026-06-11 13:32:44 UTC`):

```sql
SELECT relname, n_live_tup, n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup,
       pg_size_pretty(pg_total_relation_size('products')) AS total_size
FROM pg_stat_user_tables WHERE relname = 'products';
-- products | 73,207,527 | 40,035,125 | 75,186,492 | 2,281 | (not sampled) | 131 GB
```

- `pg_class.reltuples` for `products`: `73,039,968` (residual; post-restart ANALYZE lag)
- `pg_stat_user_tables.products`: `n_live_tup=73,207,527`, `n_tup_ins=40,035,125` (running counter since the BUY-35444 third maglev restart at `2026-06-08 10:21:09.112373+00`, `~75.2h` ago — well outside today's window)
- `pg_postmaster_start_time` for maglev: `2026-06-08 10:21:09.112373+00` (the [BUY-35444](/BUY/issues/BUY-35444) restart, 3rd in 24h, ~75h old at this fire). No new restart since.
- Table size: `131 GB` total (up from `111 GB` at the 2026-06-10 BUY-40357 reading; the writer fleet has continued rebuilding the catalog)
- `merchants` table: `count(*)=33`, `n_tup_ins=33`, `n_tup_upd=12`, `pg_class.reltuples=74,791` — this is the canonical merchant dimension and is stable (the catalog growth is product-side only)

## Daily Result

**Closed-day `2026-06-10` verdict (filed in the prior report, referenced here for continuity).**

The full closed-day `2026-06-10` analysis is in
[docs/daily-product-target-shortfall-2026-06-10.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-10.md) (Issue BUY-40357).
Headline: `+9,176,195` net inserts end-to-end (n_tup_ins 21,366,014 → 30,542,209), `382,341/hr` average,
`n_live_tup_close = 65,495,587`. **NOT A MISS** — `452%` of the prior required pace
(`2,028,429/day`) and `536%` of the new forward required pace
(`1,711,370/day`).

**In-progress `2026-06-11` pulse (00:00:00Z to 13:32:44Z).**

- **Start-of-day baseline** (`n_tup_ins` at 00:01:03Z, per the BUY-39805 midnight snapshot close in `data/.throughput_state.json`): `30,542,209`
- **In-progress `n_tup_ins` reading** at 13:32:44Z: `40,035,125`
- **Net inserts on `2026-06-11` so far**: `40,035,125 - 30,542,209 = 9,492,916`
- **Hours elapsed**: `13.527h`
- **Per-hour average (in-progress)**: `9,492,916 / 13.527 = 701,687/hr`
- **`n_live_tup` growth since 2026-06-10 close**: `73,207,527 - 65,495,587 = 7,711,940` (lower bound — autovacuum lag on the dead-tuple pile; `n_tup_ins` is the authoritative primary signal)
- **`n_dead_tup` lag**: `9,492,916 - 7,711,940 - 2,281 (n_tup_del) ≈ 1,778,695` dead tuples pending vacuum, expected at this insert rate and consistent with the [BUY-33694](/BUY/issues/BUY-33694) dispatcher primary-signal analysis

Cross-check via the most recent hourly dispatcher fire:

| Hour (UTC)         | n_tup_ins delta | Rate (rows/hr) | Result | Source                       |
|--------------------|-----------------|----------------|--------|------------------------------|
| 11:00-12:00Z       | 902,493         | 914,266        | PASS   | [BUY-41147](/BUY/issues/BUY-41147) (last fire at 12:01:46Z, primary signal) |
| 12:00-13:00Z       | n/a (in hour)   | n/a            | n/a    | Rolling forward              |
| 13:00-13:32Z       | n/a (partial)   | n/a            | n/a    | This report's reading        |

`n_tup_ins` is the dispatcher primary signal under maglev write contention (per [BUY-33694](/BUY/issues/BUY-33694)). The 11:00-12:00Z hour `914,266/hr` rate is `1,556%` of the per-hour required pace of `58,755/hr` (see forward pace below). The 2026-06-11 in-progress rate of `701,687/hr` is `1,194%` of the per-hour required pace.

**No closed-day verdict is possible for `2026-06-11` until 2026-06-12 00:00:00Z UTC.** The in-progress rate materially exceeds the per-hour required pace; there is no early signal of a missed day. The closed-day verdict for `2026-06-11` will be filed in the next daily report (the 2026-06-12 morning heartbeat, expected ~2026-06-12 00:30Z).

## Forward Pace (2026-06-12 forward)

- Approximate current active products (`n_live_tup`): `73,207,527` at `2026-06-11 13:32:44 UTC`
- Cross-check via `pg_class.reltuples`: `73,039,968` (lags; ANALYZE not yet run post-restart)
- `n_tup_ins` at the same sample: `40,035,125`
- Remaining active products to target (`100,000,000 - 73,207,527`): `26,792,473`
- Required products per day from `2026-06-12` forward (`ceil(26,792,473 / 19)`): `1,410,131`
- Required products per hour: `58,755`
- Prior published daily required pace from the `2026-06-10` report: `1,711,370` (a `17.6%` reduction)
- Prior published daily required pace from the `2026-06-09` report: `2,028,429` (a `30.5%` reduction)
- Prior published daily required pace from the `2026-06-08` report: `2,481,557` (a `43.2%` reduction)

`2026-06-11` is in progress (13.5h in at the time of this report). Today's pace is strong:
`n_tup_ins` has grown by `+9,492,916` in 13.53h = `~701,687/hr`. That is `1,194%` of the
per-hour required pace. The closed-day verdict for `2026-06-11` will be filed in the next
daily report.

## Failure Days In The Reporting Window

The "failure report on any missed day" rule applies to closed UTC days where active-product
growth fell below the required pace at the start of that day.

- `2026-06-10` UTC (closed day, measured by the [prior report](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-10.md)): **NOT A MISS.** Closed-day `n_tup_ins` growth of `+9,176,195` (authoritative midnight-snapshot end-to-end delta) materially exceeds the prior required pace of `2,028,429` (`452%`) and the new forward required pace of `1,711,370` (`536%`).
- `2026-06-11` UTC (in progress at 13:32Z, ~13.5h in): no closed-day verdict possible. Current rate (per `n_tup_ins` PRIMARY signal, 13.53h elapsed): `~701,687/hr` — `1,194%` of the per-hour required pace of `58,755/hr`.
- **No new daily-failure report is filed for `2026-06-10` or `2026-06-11`.**

Prior misses already documented in this series (for context, not re-filed here):

- `2026-06-10` — covered in `docs/daily-product-target-shortfall-2026-06-10.md` (NOT A MISS, `+9,176,195` reconstructed lower bound).
- `2026-06-09` — covered in `docs/daily-product-target-shortfall-2026-06-09.md` (NOT A MISS, `+12,900,511` reconstructed lower bound).
- `2026-06-08` — covered in [docs/buy-34974-daily-pace-check-2026-06-08.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-34974-daily-pace-check-2026-06-08.md) (NOT A MISS, `+11,795,755` active baseline).
- `2026-06-07` — covered in same `2026-06-08` report (NOT A MISS).
- `2026-06-06` — documented in `docs/daily-product-target-shortfall-2026-06-06.md` (reconstructed inserts `8,214,927` exceeded pace).
- `2026-06-05` — documented in `docs/daily-product-target-shortfall-2026-06-05.md`.
- `2026-06-04` — documented in `docs/daily-product-target-shortfall-2026-06-05.md`.
- `2026-06-03` — documented in `docs/daily-product-target-shortfall-2026-06-04.md`.
- `2026-06-02` — documented in `docs/daily-product-target-shortfall-2026-06-03.md`.
- `2026-05-31` — documented in `docs/daily-product-target-shortfall-2026-06-02.md`.
- `2026-05-30` — documented in `docs/daily-product-target-shortfall-2026-05-31.md`.

## Latest Dispatcher Evidence (Hourly)

Per `data/.throughput_state.json` at `2026-06-11 13:04:12 UTC` (the [BUY-41147](/BUY/issues/BUY-41147) fire, last completed fire):

- `last_hour_checked`: `2026-06-11T12:00:00+00:00` (hour 11:00 → 12:00 UTC)
- `last_check_result`: `PASS`
- `last_check_real_rows`: `387,092` (real rows observed in the hour window)
- `last_check_source`: `n_tup_ins_delta`
- `last_check_delta_rows`: `902,493` (cumulative `n_tup_ins` delta over the hour window)
- `last_check_rate`: `914,266` rows/hr
- `last_check_threshold`: `150,000` rows/hr
- `last_db_host`: `maglev.proxy.rlwy.net:31310/railway`
- `last_n_tup_ins`: `39,693,487` at `2026-06-11T13:04:12.766515+00` (anchor used by the dispatcher)
- `last_n_live_tup`: `73,176,380` at the same anchor
- `last_closed_day`: `2026-06-10`, `n_tup_ins_open=30,148,362`, `n_tup_ins_close=30,542,209`, `delta=393,847` (23:00-24:00Z hour only — see "Open-at caveat" in the prior report), `n_live_tup_close=65,495,587`
- `last_pm_start`: `2026-06-08 10:21:09.112373+00` (well outside the 11:00-12:00Z window; `n_tup_ins` delta method valid)

The 11:00 → 12:00 UTC hour insert proof of `902,493` is the most recent closed hour in the
reporting window. It is `1,556%` of the per-hour required pace of `58,755/hr` and confirms
the live throughput is comfortably above the forward pace. The exact-hour `COUNT(*)`
cross-check is not heartbeat-cheap on the canonical DB (per [BUY-32950](/BUY/issues/BUY-32950)),
so the `n_tup_ins` delta remains the authoritative primary signal.

## Interpretation

1. The canonical DB routing is correct in this workspace: `data/.catalog_db_url` resolves to `maglev.proxy.rlwy.net:31310/railway` and the `pg_stat_user_tables.products` reading tracks the live catalog. Control-plane DB (roundhouse, `~2.7M` stale `public.products`) is correctly NOT in use.
2. The closed-day `2026-06-10` verdict (already filed in the prior report) is unchanged: closed-day `n_tup_ins` growth of `+9,176,195` materially exceeds the prior required pace of `2,028,429`. The catalog has grown from the `~55.4M` reading on 2026-06-09 to `~65.5M` at the 2026-06-10 close and is now at `~73.2M` at the 2026-06-11 13:32Z reading — a `+17.8M` three-day gain.
3. The writer fleet is on a sustained high-throughput run: the 11:00-12:00Z hour `914,266/hr` is the second-highest hourly rate in the last 72h, and the in-progress 2026-06-11 rate of `~701,687/hr` is materially above the per-hour required pace. The catalog trajectory is on track for the 2026-06-30 100M target if this rate holds.
4. The `n_tup_ins`-delta method is valid for the 2026-06-11 in-progress window: `pg_postmaster_start_time` is `2026-06-08 10:21:09Z` (the BUY-35444 third restart), `~75h` before this fire and `~62h` before the start of 2026-06-11. No restart in window, no counter reset.
5. The same measurement-cost constraint from [BUY-32950](/BUY/issues/BUY-32950) still applies: exact `COUNT(*)` on the canonical DB is too expensive to refresh inside a heartbeat. The `n_live_tup` approximation, cross-checked against the `n_tup_ins` delta (the dispatcher primary signal), is the only same-day readable live count.
6. **Index state note:** `products_created_at_idx` is `indisvalid=f, indisready=f` (per [BUY-32878](/BUY/issues/BUY-32878) central tracker [BUY-33973](/BUY/issues/BUY-33973)). All `WHERE created_at` queries still seq-scan; maglev DDL is ops-only per charter Rule 14. The daily report therefore relies entirely on `n_tup_ins` + `n_live_tup`, not the partial index or `created_at` filtering.
7. **Auto-dispatcher cron is still broken** (per [BUY-33694](/BUY/issues/BUY-33694), missing `cd` + wrong path on the `*/5` crontab). The most recent hourly fires (BUY-41147 at 12:01:46Z) are manual heartbeats. The daily Oracle routine that this report represents is also a manual heartbeat; the next daily fire is expected at the next scheduled wake on this issue.
8. The `merchants` table is stable at `33` rows; the catalog growth is purely product-side. The merchant-dimension remains the limiting factor on storefront coverage (per [BUY-29216](/BUY/issues/BUY-29216) and the higher-throughput merchant runs stream) but is out of scope for the product-target shortfall rule.

## Corrective Assignments In Place

- [BUY-33694](/BUY/issues/BUY-33694): throughput dispatcher repointed at maglev, `data/.throughput_state.json` is the canonical hourly state. Cron still broken (missing `cd` + wrong path); manual heartbeats are the live path.
- [BUY-39805](/BUY/issues/BUY-39805): midnight-boundary `n_tup_ins` snapshot mechanism. Shipped 2026-06-10; the start-of-day open-at gap (see prior report) is a known limitation, not a defect.
- [BUY-32074](/BUY/issues/BUY-32074): the DB-path throughput cap (this is what makes exact `COUNT(*)` too expensive to refresh in a heartbeat).
- [BUY-32950](/BUY/issues/BUY-32950): exact-count DB path upgrade (Pro+ on Railway Postgres, deadline 2026-06-07 18:00 UTC, owner Rex). Past deadline; still open.
- [BUY-32878](/BUY/issues/BUY-32878) / [BUY-33973](/BUY/issues/BUY-33973): `products_created_at_idx` INVALID. Maglev DDL is ops-only per charter Rule 14; the index stays INVALID. Daily reports use the `n_tup_ins` delta path.
- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path.
- [BUY-35444](/BUY/issues/BUY-35444): the 3rd maglev restart at `2026-06-08 10:21:09Z` — the postmaster start anchor used throughout this report.
- [BUY-41147](/BUY/issues/BUY-41147): the latest 11:00-12:00Z hour PASS fire (914,266/hr); the `last_n_tup_ins` anchor is the basis for this report's 13:32:44Z reading.

## Open Questions For The Board

- The midnight-snapshot mechanism's `open_at` field captures the dispatcher's last pre-midnight reading, not start-of-day. A follow-up should record a separate `n_tup_ins_at_00_00_utc` reading for the closed day so the next report does not need end-to-end reconstruction. The prior report flagged this as a known limitation; no fix has landed yet.
- The 0/hr stretch on 2026-06-09T20:03Z → 2026-06-10T03:02Z (~7 hours) recovered strongly in the 04:00-24:00Z window. The cause of the 0/hr stretch is maglev write contention ([BUY-30590](/BUY/issues/BUY-30590) driver issue), not a fleet-side defect.
- The auto-dispatcher cron ([BUY-33694](/BUY/issues/BUY-33694)) is still broken after 24+ hours; this report relies on manual heartbeats for both the hourly rate and the daily snapshot. A permanent fix should land before the next fire.

## Conclusion

`2026-06-10` does not support a new daily shortfall failure report (closed-day `n_tup_ins` growth of `+9,176,195` materially exceeds the prior required pace of `2,028,429/day` (`452%`) and the new forward required pace of `1,711,370/day` (`536%`)). The canonical DB is correctly pinned (maglev, `data/.catalog_db_url`) and the catalog is at approximately `73.2M` live products as of `2026-06-11 13:32:44 UTC`, leaving roughly `26.8M` active products to reach `100M` and an approximate forward pace requirement of `1,410,131` active products per day for the remaining `19` calendar days (`2026-06-12` → `2026-06-30`). The in-progress `2026-06-11` rate of `~701,687/hr` is `1,194%` of the per-hour required pace and the most recent closed hour (11:00-12:00Z) is `1,556%` of pace — no early signal of a missed day. The `2026-06-11` closed-day verdict is reserved for the end-of-day shortfall check (no failure report filed now). The exact-count cost is still the operational cap ([BUY-32950](/BUY/issues/BUY-32950)) and should be resolved per Rex's existing commitment. Next daily fire expected on the next scheduled wake of this issue (target: `2026-06-12` ~00:00Z).
