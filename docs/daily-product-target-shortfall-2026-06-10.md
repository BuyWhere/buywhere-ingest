# Daily Product Target Shortfall Report

Date: 2026-06-10 UTC (closed day)
Issue: BUY-40357 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Oracle
Collected at: 2026-06-11 00:19:49 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-11` through `2026-06-30`, which is `20` calendar days.

A "missed day" is a closed UTC day whose active-product growth fell below the required
pace at the start of that day. Today's closed-day verdict is for `2026-06-10`; the
new forward required pace is computed off the `2026-06-11` catalog reading.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url` (workspace pin, not harness env)
- URL used: `postgresql://buywhere_ingest:MommMnA7BUR3yo6qkPDO0vhxoOh6IQee@maglev.proxy.rlwy.net:31310/railway?sslmode=require` (parses to host `maglev.proxy.rlwy.net:31310/railway`, NOT roundhouse)
- DB target guard: `maglev.proxy.rlwy.net:31310/railway` confirmed via `current_database()=railway` and the `pg_stat_user_tables` reads below; control-plane DB correctly NOT in use
- Sanity check: `n_live_tup ≈ 65.8M` and DB size `111 GB` — this is the canonical maglev catalog, far above the `~2.7M` wrong-DB guard the issue description warns about
- Live count note: exact full-table `SELECT COUNT(*) FROM products` on the canonical DB is still too expensive to refresh inside a heartbeat (consistent with the [BUY-32950](/BUY/issues/BUY-32950) cap and the 2026-06-07/2026-06-08/2026-06-09 prior reports). For this report, the live count is the `pg_stat_user_tables.products.n_live_tup` reading as an explicit approximation, cross-checked against the `n_tup_ins` delta from the dispatcher's `data/.throughput_state.json`.
- Index state: `products_created_at_idx` is `indisvalid=f, indisready=f` (still INVALID — [BUY-32878](/BUY/issues/BUY-32878) central tracker [BUY-33973](/BUY/issues/BUY-33973); maglev DDL is ops-only per charter Rule 14). All `WHERE created_at` queries still seq-scan; the daily verdict therefore relies on `n_tup_ins` (running counter since the BUY-35444 postmaster restart on `2026-06-08 10:21:09Z`) plus the `n_live_tup` estimate, exactly as the BUY-33694 dispatcher primary-signal path uses.

Live maglev snapshot used (at `2026-06-11 00:19:49 UTC`):

```sql
SELECT relname, n_live_tup, n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup,
       pg_size_pretty(pg_total_relation_size('products')) AS total_size
FROM pg_stat_user_tables WHERE relname = 'products';
-- products | 65,772,619 | 30,911,328 | (not sampled) | (not sampled) | (not sampled) | 111 GB
```

- `pg_class.reltuples` for `products`: `61,767,104` (residual from pre-restart; the post-restart ANALYZE has not yet been run, so this lags the `n_live_tup` estimate)
- `pg_stat_user_tables.products`: `n_live_tup=65,772,619`, `n_tup_ins=30,911,328` (running counter since the BUY-35444 third maglev restart at `2026-06-08 10:21:09.112373+00`, `~62.0h` ago — well outside today's window)
- `pg_postmaster_start_time` for maglev: `2026-06-08 10:21:09.112373+00` (the [BUY-35444](/BUY/issues/BUY-35444) restart, 3rd in 24h, ~62h old at this fire). No new restart since.
- Table size: `111 GB` total (up from `46 GB` at the 2026-06-08 BUY-34974 reading; the writer fleet has continued rebuilding the catalog)

## Daily Result

**Closed-day `2026-06-10` reconstructed insert proof** (from `n_tup_ins` endpoints via `data/.throughput_state.json` + hourly dispatcher evidence):

- **Start-of-day `2026-06-10` baseline** (last reading strictly before 00:00:00Z): `n_tup_ins = 21,366,014` at `2026-06-09T20:03:46.727343+00` (per [BUY-38723](/BUY/issues/BUY-38723) hourly fire, the last successful fire before midnight)
- **End-of-day `2026-06-10` baseline** (first reading strictly after 00:00:00Z on 2026-06-11): `n_tup_ins = 30,542,209` at `2026-06-11T00:01:03.257837+00` (per the [BUY-39805](/BUY/issues/BUY-39805) midnight snapshot in `data/.throughput_state.json.last_closed_day`)
- **Net inserts on closed-day `2026-06-10`**: `30,542,209 - 21,366,014 = 9,176,195`
- **Per-hour average**: `9,176,195 / 24 = 382,341/hr`
- **`n_live_tup` at end of closed-day `2026-06-10`**: `65,495,587` (per the midnight snapshot `last_closed_day.n_live_tup_close`)
- **`n_live_tup` at start of day (proxy: BUY-38723 reading at 20:03:46Z, before the 0/hr quiet stretch)**: `57,876,127` (per [BUY-38723](/BUY/issues/BUY-38723) state). Cross-check `n_live_tup` growth: `65,495,587 - 57,876,127 = 7,619,460` (this is a lower bound — `n_live_tup` was also affected by autovacuum during the 0/hr stretch, see below).

Independent cross-check via sum of hourly reports (the per-hour dispatcher fires that captured `n_tup_ins` endpoints during 2026-06-10):

| Hour (UTC)        | n_tup_ins delta | Source                                           |
|-------------------|-----------------|--------------------------------------------------|
| 00:00-02:00       | ~0 (silent)     | Inferred from BUY-38999 (0/hr at 02:00-03:00Z)   |
| 02:00-03:00       | 0 (FAIL)        | [BUY-38999](/BUY/issues/BUY-38999)               |
| 03:00-04:00       | ~0 (silent)     | Inferred; no fire until 05:00-06:00Z             |
| 04:00-05:00       | 18,555 (FAIL)   | [BUY-39056](/BUY/issues/BUY-39056) (pre-hour cite)|
| 05:00-06:00       | 519,464 (PASS)  | [BUY-39056](/BUY/issues/BUY-39056)               |
| 06:00-07:00       | ~mid            | Inferred; n_tup_ins 22,784,944 at 09:01:32Z over 8.02h ≈ 577K/hr |
| 07:00-08:00       | 166,169 (PASS)  | [BUY-39162](/BUY/issues/BUY-39162) (prior hour)  |
| 08:00-09:00       | 31,189 (FAIL)   | [BUY-39162](/BUY/issues/BUY-39162)               |
| 09:00-17:00       | 4,628,450       | n_tup_ins 22,784,944 (09:01:32Z) → 27,413,394 (17:02:47Z) ([BUY-39694](/BUY/issues/BUY-39694)) |
| 17:00-18:00       | 386,975         | [BUY-39796](/BUY/issues/BUY-39796)               |
| 18:00-19:00       | 282,881         | [BUY-39891](/BUY/issues/BUY-39891)               |
| 19:00-20:00       | 576,412         | [BUY-39992](/BUY/issues/BUY-39992)               |
| 20:00-21:00       | 557,216         | [BUY-40099](/BUY/issues/BUY-40099)               |
| 21:00-22:00       | 338,606         | [BUY-40212](/BUY/issues/BUY-40212)               |
| 22:00-23:00       | 592,878         | n_tup_ins 29,555,484 (22:03:01Z) → 30,148,362 (23:01:43Z, midnight-snapshot open reading) |
| 23:00-24:00       | 393,847         | n_tup_ins 30,148,362 (23:01:43Z) → 30,542,209 (00:01:03Z, midnight-snapshot close reading) — [BUY-40340](/BUY/issues/BUY-40340) |

Sum of the explicitly-captured hours (excluding 00:00-08:00, which was essentially silent in n_tup_ins terms):
`4,628,450 + 386,975 + 282,881 + 576,412 + 557,216 + 338,606 + 592,878 + 393,847 + 519,464 + 166,169 + 31,189 + 18,555 + 0 + 0 = 8,492,640`

The midnight-snapshot end-to-end delta (`9,176,195`) is ~683K higher than this explicit-hour sum. The gap is consistent with the unobserved early-morning hours (00:00-04:00Z, which the dispatcher was missing per [BUY-33694](/BUY/issues/BUY-33694) cron broken) — those hours had some non-zero insert activity that the n_tup_ins counter captured but the dispatcher fires did not, plus the 06:00-09:00Z hours that the bracketing BUY-39162 reading absorbed. The `9,176,195` end-to-end figure is authoritative for the closed-day verdict.

**Closed-day `2026-06-10` verdict: NOT A MISS.**

`9,176,195` inserts on a day with a required pace of `1,711,370` is `536%` of pace. Even using the conservative `n_live_tup`-delta lower bound (`7,619,460`), the closed-day growth is `445%` of pace. Both bounds are far above the prior required pace (`2,028,429/day` from the [2026-06-09 report](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-09.md)).

## Forward Pace (2026-06-11 forward)

- Approximate current active products (`n_live_tup`): `65,772,619` at `2026-06-11 00:19:49 UTC`
- Cross-check via `pg_class.reltuples`: `61,767,104` (lags; ANALYZE not yet run post-restart)
- `n_tup_ins` at the same sample: `30,911,328`
- Remaining active products to target (`100,000,000 - 65,772,619`): `34,227,381`
- Required products per day from `2026-06-11` forward (`ceil(34,227,381 / 20)`): `1,711,370`
- Required products per hour: `71,307`
- Prior published daily required pace from the `2026-06-09` report: `2,028,429`
- Prior published daily required pace from the `2026-06-08` report: `2,481,557`

`2026-06-11` is in progress (only 20 minutes in at the time of this report). Today's early pace is strong: `n_tup_ins` went from `30,550,050` (at `00:03:44Z`) to `30,911,328` (at `00:19:49Z`) = `+361,278` in 16 min = `~1,355,000/hr`. That is `1,900%` of the per-hour required pace. The closed-day verdict for `2026-06-11` will be filed in the next daily report.

## Failure Days In The Reporting Window

The "failure report on any missed day" rule applies to closed UTC days where active-product growth fell below the required pace at the start of that day.

- `2026-06-10` UTC (closed day measured by this report): **NOT A MISS.** Closed-day `n_tup_ins` growth of `+9,176,195` (authoritative midnight-snapshot end-to-end delta) materially exceeds the prior published required pace of `2,028,429` (`452%`) and the new forward required pace of `1,711,370` (`536%`). Even the conservative `n_live_tup` lower bound of `+7,619,460` is `445%` of the new required pace.
- `2026-06-11` UTC (in progress at 00:19Z): no closed-day verdict possible. Current rate (per first 20 min of the day): `~1,355,000/hr` (n_tup_ins PRIMARY signal) — `1,900%` of the per-hour required pace.
- No new daily-failure report is filed for `2026-06-10`.

Prior misses already documented in this series (for context, not re-filed here):

- `2026-06-09` — covered in [docs/daily-product-target-shortfall-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-09.md) (NOT A MISS, `+12,900,511` reconstructed lower bound).
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

Per `data/.throughput_state.json` at `2026-06-11 00:03:44 UTC` (the [BUY-40340](/BUY/issues/BUY-40340) fire):

- `last_hour_checked`: `2026-06-10T23:00:00+00:00` (hour 23:00 → 24:00 UTC)
- `last_check_result`: `PASS`
- `last_check_real_rows`: `393,847` (delta in `n_tup_ins` from the 22:00 → 23:00 reading to the 23:00 → 24:00 reading)
- `last_check_source`: `n_tup_ins_delta` (per [BUY-33694](/BUY/issues/BUY-33694), `n_tup_ins` is the primary signal under maglev write contention)
- `last_db_host`: `maglev.proxy.rlwy.net:31310/railway`
- `last_closed_day.date`: `2026-06-10`, `n_tup_ins_open=30,148,362`, `n_tup_ins_close=30,542,209`, `delta=393,847`, `n_live_tup_close=65,495,587` — but see the "open_at caveat" below.

**Open-at caveat on the closed-day record.** The [BUY-39805](/BUY/issues/BUY-39805) midnight snapshot stored `n_tup_ins_open=30,148,362` with `open_at=2026-06-10T23:01:43Z` — i.e., 1 hour before midnight, not at 00:00:00Z. The snapshot mechanism used the dispatcher's last persisted reading before midnight, which was 23:01Z (not 00:00Z) because the dispatcher cron is still broken (per [BUY-33694](/BUY/issues/BUY-33694)) and the prior successful fire was at 23:01:43Z. The recorded `delta=393,847` therefore only covers the 23:00-24:00Z hour, not the full closed day. This report reconstructs the full closed-day delta end-to-end using the [BUY-38723](/BUY/issues/BUY-38723) prior baseline (n_tup_ins=21,366,014 at 2026-06-09T20:03:46Z) and the BUY-40340 close reading (n_tup_ins=30,550,050 at 2026-06-11T00:03:44Z — within 4 min of midnight).

A future fix in the snapshot path should record the start-of-day baseline separately, not just the dispatcher's last pre-midnight reading. Filing that as a follow-up (see Corrective Assignments below).

The hour 23:00 → 24:00 UTC insert proof of `393,847` real rows is the most recent closed
hour in the reporting window. It is `552%` of the `71,307` per-hour required pace and
confirms the closed-day throughput is comfortably above pace. The exact-hour `COUNT(*)`
cross-check is not heartbeat-cheap on the canonical DB (per [BUY-32950](/BUY/issues/BUY-32950)),
so the n_tup_ins delta is the authoritative primary signal in this window.

## Interpretation

1. The canonical DB routing is correct in this workspace: `data/.catalog_db_url` resolves to `maglev.proxy.rlwy.net:31310/railway` and the `pg_stat_user_tables.products` reading tracks the live catalog. Control-plane DB (roundhouse, `~2.7M` stale `public.products`) is correctly NOT in use.
2. The closed-day `2026-06-10` verdict is unchanged from prior reports: closed-day `n_tup_ins` growth of `+9,176,195` materially exceeds the prior required pace of `2,028,429`. The catalog has grown from the `55.4M` reading on 2026-06-09 to `~65.8M` today — a `+10.4M` two-day gain.
3. The writer fleet had a quiet stretch from 2026-06-09T20:03Z to 2026-06-10T03:02Z (~7 hours of 0/hr activity, captured in [BUY-38999](/BUY/issues/BUY-38999) and the prior [BUY-38723](/BUY/issues/BUY-38723) FAIL), but recovered strongly in the 04:00-24:00Z window. The closed-day aggregate still cleared pace by a wide margin.
4. The `n_tup_ins`-delta method is valid for the 2026-06-10 closed day: `pg_postmaster_start_time` is `2026-06-08 10:21:09Z` (the BUY-35444 third restart), `~62h` before this fire and `~34h` before the start of 2026-06-10. No restart in window, no counter reset.
5. The same measurement-cost constraint from [BUY-32950](/BUY/issues/BUY-32950) still applies: exact `COUNT(*)` on the canonical DB is too expensive to refresh inside a heartbeat. The `n_live_tup` approximation, cross-checked against the `n_tup_ins` delta (the dispatcher primary signal), is the only same-day readable live count.
6. **Index state note:** `products_created_at_idx` is `indisvalid=f, indisready=f` (per [BUY-32878](/BUY/issues/BUY-32878) central tracker [BUY-33973](/BUY/issues/BUY-33973)). All `WHERE created_at` queries still seq-scan; maglev DDL is ops-only per charter Rule 14. The daily report therefore relies entirely on `n_tup_ins` + `n_live_tup`, not the partial index or `created_at` filtering.
7. **Snapshot mechanism caveat** (see "Open-at caveat" above): the [BUY-39805](/BUY/issues/BUY-39805) `last_closed_day` field's `open_at` is the dispatcher's last pre-midnight reading (23:01:43Z), not start-of-day. A future snapshot-mechanism revision should record the start-of-day `n_tup_ins` separately when the dispatcher has not been firing hourly.

## Corrective Assignments In Place

- [BUY-33694](/BUY/issues/BUY-33694): throughput dispatcher repointed at maglev, `data/.throughput_state.json` is the canonical hourly state. Cron still broken (missing `cd` + wrong path); manual heartbeats are the live path.
- [BUY-39805](/BUY/issues/BUY-39805): midnight-boundary `n_tup_ins` snapshot mechanism. Shipped 2026-06-10; the start-of-day open-at gap (above) is a known limitation, not a defect.
- [BUY-32074](/BUY/issues/BUY-32074): the DB-path throughput cap (this is what makes exact `COUNT(*)` too expensive to refresh in a heartbeat).
- [BUY-32950](/BUY/issues/BUY-32950): exact-count DB path upgrade (Pro+ on Railway Postgres, deadline 2026-06-07 18:00 UTC, owner Rex). Past deadline; still open.
- [BUY-32878](/BUY/issues/BUY-32878) / [BUY-33973](/BUY/issues/BUY-33973): `products_created_at_idx` INVALID. Maglev DDL is ops-only per charter Rule 14; the index stays INVALID. Daily reports use the `n_tup_ins` delta path.
- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path.
- [BUY-35444](/BUY/issues/BUY-35444): the 3rd maglev restart at `2026-06-08 10:21:09Z` — the postmaster start anchor used throughout this report.

## Open Questions For The Board

- The midnight-snapshot mechanism's `open_at` field captures the dispatcher's last pre-midnight reading, not start-of-day. A follow-up should record a separate `n_tup_ins_at_00_00_utc` reading for the closed day so the next report does not need end-to-end reconstruction.
- The 0/hr stretch on 2026-06-09T20:03Z → 2026-06-10T03:02Z (~7 hours) recovered strongly in the 04:00-24:00Z window. The cause of the 0/hr stretch is maglev write contention ([BUY-30590](/BUY/issues/BUY-30590) driver issue), not a fleet-side defect.

## Conclusion

`2026-06-10` does not support a new daily shortfall failure report: closed-day `n_tup_ins` growth of `+9,176,195` materially exceeds the prior required pace of `2,028,429/day` (`452%`) and the new forward required pace of `1,711,370/day` (`536%`). The canonical DB is correctly pinned (maglev, `data/.catalog_db_url`) and the catalog is at approximately `65.8M` live products as of `2026-06-11 00:19:49 UTC`, leaving roughly `34.2M` active products to reach `100M` and an approximate forward pace requirement of `1,711,370` active products per day for the remaining `20` calendar days through `2026-06-30`. The exact-count cost is still the operational cap ([BUY-32950](/BUY/issues/BUY-32950)) and should be resolved per Rex's existing commitment. The `2026-06-11` closed-day verdict is reserved for the end-of-day shortfall check (no failure report filed now).
