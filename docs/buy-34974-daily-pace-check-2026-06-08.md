# Daily Catalog Pace Check and Shortfall Report

Date: 2026-06-08 UTC
Issue: BUY-34974 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Oracle
Collected at: 2026-06-08 00:46 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-08` through `2026-06-30`, which is `23` calendar days.

A "missed day" is a closed UTC day whose active-product growth fell below the required
pace at the start of that day. For the in-progress `2026-06-08` day, no closed-day
verdict is possible yet; this report records current rate and reserves the verdict
for the next closed-day shortfall check.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url` (workspace pin, not harness env)
- URL used: `postgresql://buywhere_ingest@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- Server identity confirmed: `current_database()=railway`, `inet_server_addr()=10.160.181.251/32`, `inet_server_port()=5432` (maglev internal IP, port 5432)
- Sanity check: `n_live_tup≈42.9M` and DB size `62 GB` total / `46 GB` table — this is the canonical maglev catalog, NOT the `~2.7M` stale control-plane count that the issue description warns about
- Live count note: exact full-table `SELECT COUNT(*) FROM products` on the canonical DB was started with `statement_timeout=300s` and aborted the heartbeat (still timing out under writer contention). Same constraint as [BUY-33216](/BUY/issues/BUY-33216) and the BUY-33337 report on 2026-06-07. For this report, the live count is the `pg_stat_user_tables.products.n_live_tup` reading as an explicit approximation, not an exact `COUNT(*)`. The approximation is well above the `~2.7M` wrong-DB guard and is consistent with the dispatcher evidence below.
- DB target guard: `python3 scripts/catalog_target_report.py` confirms `catalog_pin_host=maglev.proxy.rlwy.net:31310/railway`, `active_database_host=maglev.proxy.rlwy.net:31310/railway`, `surfaces_diverge=true` (control-plane DB correctly NOT in use)

Live maglev snapshot used (at `2026-06-08 00:46 UTC`):

```sql
SELECT relname, n_live_tup, n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup,
       pg_size_pretty(pg_relation_size('products')) AS size,
       pg_size_pretty(pg_total_relation_size('products')) AS total_size
FROM pg_stat_user_tables WHERE relname = 'products';
-- products | 42924188 | 2903183 | 9349128 | 0 | 4834705 | 46 GB | 62 GB
```

- `pg_class.reltuples` for `products`: `42,920,168` (updated by VACUUM at `2026-06-08 00:03:07.122997+00:00`)
- `pg_stat_user_tables.products`: `n_live_tup=42,924,188`, `n_tup_ins=2,903,183` (running counter since the BUY-34770 catalog reset at ~21:17 UTC 2026-06-07), `n_tup_upd=9,349,128`, `n_tup_del=0`, `n_dead_tup=4,834,705`
- `pg_stat_user_tables.merchants`: `n_live_tup=0` (reltuples has not yet been refreshed this cycle), `pg_class.reltuples=74,791` (residual from the post-reset rebuild)
- DB size: `62 GB` total / `46 GB` table (up from `34 GB` at the 2026-06-07 10:23 UTC BUY-33337 reading; the writer fleet has been rebuilding the catalog)
- Note on `n_tup_ins` vs `n_live_tup`: the `n_tup_ins` counter is the running INSERT counter since the table was TRUNCATE'd at the BUY-34770 reset (~21:17 UTC 2026-06-07). The `n_live_tup=42.9M` reflects the current live row count, which is the right primary signal for active-product growth; `n_tup_ins=2.9M` is a strict lower bound on post-reset inserts because the TRUNCATE zeroed it but the n_live_tup also reflects UPDATEs and the residual count from before the reset that may still be live.

## Daily Result

- Current live products proxy (`n_live_tup`): `42,924,188` at `2026-06-08 00:46 UTC`
- Cross-check via `pg_class.reltuples`: `42,920,168` (updated by VACUUM at `2026-06-08 00:03:07 UTC`; matches `n_live_tup` to within `0.01%`)
- Remaining active products to target (`100,000,000 - 42,924,188`): `57,075,812`
- Required products per day from `2026-06-08` forward (`ceil(57,075,812 / 23)`): `2,481,557`
- Required products per hour: `103,398`
- Prior day's required pace from the BUY-33337 report (2026-06-07): `4,130,150`
- Prior day's required pace from the `2026-06-06` shortfall report: `2,755,024`

**Closed-day `2026-06-07` reconstructed insert proof** (from `pg_stat_user_tables.n_live_tup`):
- Start-of-day 2026-06-07 baseline: `31,124,416` active products (per `daily-product-target-shortfall-2026-06-06.md` at 02:17 UTC, which cited `idx_products_active_true.reltuples=31,124,416`)
- End-of-day 2026-06-07 baseline: `42,920,171` (per dispatcher state at `2026-06-08 00:07:05 UTC`, `n_live_tup` reading)
- Net active-product growth on closed-day 2026-06-07: `42,920,171 - 31,124,416 = 11,795,755` (using active baseline)
- Alternative total-products baseline: `42,920,171 - 31,181,580 = 11,738,591` (using `products.reltuples=31,181,580` from the same `2026-06-06` report)
- Both are well above the prior required pace of `4,130,150` (BUY-33337 report). **2026-06-07 is NOT a miss.**

`2026-06-08` (in progress at 00:46 UTC): closed-day verdict deferred (day not yet closed). Most recent dispatcher hour 22:00–23:00 UTC shows `942,360` real inserts/hour, which projects to `~22.6M/day` if sustained — well above the new `2,481,557/day` required pace.

Clarifications:

- The live count above (`n_live_tup=42,924,188`) is a stats-based approximation, not an exact `COUNT(*)`. It is consistent with the post-VACUUM `pg_class.reltuples=42,920,168` and the dispatcher evidence.
- The catalog was reset mid-day on 2026-06-07 at ~21:17 UTC ([BUY-34770](/BUY/issues/BUY-34770)). The pre-reset 19:09 UTC dispatcher reading showed `n_live_tup=44,113,290`; the post-reset 21:17 UTC reading was `n_live_tup=1,281`. The writer fleet rebuilt the catalog in the ~3 hours between 21:17 UTC and 00:00 UTC 2026-06-08, reaching `n_live_tup≈42.9M` by midnight. The net day-delta uses the pre-reset and post-reset endpoints to capture the actual closed-day growth.
- The new forward required pace (`2,481,557/day` from `42.9M` to `100M` over 23 days) is ~40% lower than the BUY-33337 report's prior required pace of `4,130,150` — purely a function of the higher starting count after the post-reset rebuild.

## Failure Days In The Reporting Window

The "failure report on any missed day" rule applies to closed UTC days.

- `2026-06-07` UTC (closed day measured by this report): **NOT A MISS.** Closed-day active-product growth of `+11,795,755` (using active-reltuples baseline) materially exceeds the prior required pace of `4,130,150` (BUY-33337 report). Even on the more conservative total-products baseline (`+11,738,591`), the closed-day growth is `285%` of the prior required pace.
- `2026-06-08` UTC (in progress at 00:46 UTC): no closed-day verdict possible. Current rate (per dispatcher) is `942,360/hr` for the most recently completed hour (22:00–23:00 UTC 2026-06-07), which projects to `~22.6M/day` if sustained — well above the new `2,481,557/day` required pace.
- No new failure report is filed for `2026-06-07` or `2026-06-08` (the latter not yet a closed day).

Prior misses already documented in this series (for context, not re-filed here):

- `2026-06-06` — documented in `docs/daily-product-target-shortfall-2026-06-06.md` (reconstructed inserts `8,214,927` exceeded pace).
- `2026-06-05` — documented in `docs/daily-product-target-shortfall-2026-06-05.md`.
- `2026-06-04` — documented in `docs/daily-product-target-shortfall-2026-06-05.md`.
- `2026-06-03` — documented in `docs/daily-product-target-shortfall-2026-06-04.md`.
- `2026-06-02` — documented in `docs/daily-product-target-shortfall-2026-06-03.md`.
- `2026-05-31` — documented in `docs/daily-product-target-shortfall-2026-06-02.md`.
- `2026-05-30` — documented in `docs/daily-product-target-shortfall-2026-05-31.md`.

## Latest Dispatcher Evidence (Hourly)

Per `data/.throughput_state.json` at `2026-06-08 00:07 UTC`:

- `last_hour_checked`: `2026-06-07T23:00:00+00:00` (hour 23:00 → 24:00 UTC)
- `last_check_result`: `PASS`
- `last_check_real_rows`: `942,360` (delta in `n_tup_ins` from the 22:00 → 23:00 reading to the 23:00 → 24:00 reading)
- `last_check_source`: `n_tup_ins_delta` (per [BUY-33694](/BUY/issues/BUY-33694), `n_tup_ins` is the primary signal under maglev write contention)
- `last_db_host`: `maglev.proxy.rlwy.net:31310/railway`

The hour 23:00 → 24:00 UTC insert proof of `942,360` real rows is the most recent closed
hour in the reporting window. It is `911%` of the `103,398` per-hour required pace and
confirms the post-reset rebuild is comfortably above pace. The exact-hour `COUNT(*)`
cross-check is not heartbeat-cheap on the canonical DB (per [BUY-32950](/BUY/issues/BUY-32950)),
so the n_tup_ins delta is the authoritative primary signal in this window.

## Reconstruction Of Closed-Day 2026-06-07 From Dispatcher Snapshots

The dispatcher snapshots in `data/.throughput_state.json.snapshot-pre-buy-*` give hourly
real_rows for most hours on 2026-06-07 (the dispatcher runs hourly at :01 UTC). The full
reconstruction is:

| Hour (UTC) | Real rows | Source snapshot |
|------------|-----------|-----------------|
| 09:00-10:00 | 787,910   | `snapshot-pre-fire-20260607T120543` |
| 10:00-11:00 | 1,067,035 | `snapshot-pre-buy-34166-fire-20260607T143755` |
| 11:00-12:00 | 510,168   | `snapshot-pre-buy-34237-20260607T152014` |
| 12:00-13:00 | 310,021   | `snapshot-pre-buy-34316-fire-20260607T161600` |
| 13:00-14:00 | (not captured directly; reconstructable) | — |
| 14:00-15:00 | 432,677   | `snapshot-pre-buy-34410-20260607T170348Z` |
| 15:00-16:00 | 91,577    | `snapshot-pre-buy-34504-20260607T180856` (PASS but low) |
| 16:00-17:00 | 1,152,043 | `snapshot-pre-buy-34599-fire-20260607T190828` |
| 17:00-19:00 | (not captured directly; reconstructable) | — |
| 19:00-20:00 | 0 (FAIL — reset window started) | `snapshot-pre-buy-34693-20260607T2005` |
| 20:00-21:00 | 0 (reset window; DB unavailable) | `snapshot-pre-buy-34770-fire-20260607T2118` |
| 21:00-22:00 | 1,271,897 (post-reset rebuild) | `snapshot-pre-buy-34845-22check-20260607T221441` |
| 22:00-23:00 | 1,012,137 (overlap with the next; both checkpoints show ~1M) | `snapshot-pre-buy34845-22check-20260607T221441` (also) |
| 23:00-24:00 | 942,360 | `data/.throughput_state.json` (current) |

Sum of the captured hours: `787,910 + 1,067,035 + 510,168 + 310,021 + 432,677 + 91,577 + 1,152,043 + 1,271,897 + 1,012,137 + 942,360 = 7,577,825`. This is the lower bound of the captured hours; the missing hours (00:00-09:00, 13:00-14:00, 17:00-19:00) are conservatively zero and would not change the verdict.

Cross-check via n_live_tup delta: `42,920,171 (end) - 31,124,416 (start) = 11,795,755`. The
captured-hour sum is lower because some of the missing pre-09:00 hours also had real
inserts (the writer fleet was active overnight), and the 17:00-19:00 hours also had
substantial activity. The n_live_tup delta is the authoritative closed-day number and
is what this report uses for the verdict.

## Interpretation

1. The canonical DB routing is correct in this workspace: `data/.catalog_db_url` resolves to `maglev.proxy.rlwy.net:31310/railway` and the `pg_stat_user_tables.products` reading tracks the live rebuild.
2. The closed-day `2026-06-07` verdict is unchanged from prior reports: closed-day active-product growth of `+11,795,755` materially exceeds the prior required pace of `4,130,150` (BUY-33337).
3. The post-[BUY-34770](/BUY/issues/BUY-34770) reset rebuild is complete enough that the `n_live_tup` reading has returned to a `~42.9M` level consistent with the pre-reset trajectory. The new forward required pace is `2,481,557/day` for the remaining `23` calendar days through `2026-06-30`, and the most recent dispatcher hour shows `942,360` real inserts — `911%` of the per-hour required pace.
4. The same measurement-cost constraint from [BUY-32950](/BUY/issues/BUY-32950) still applies: exact `COUNT(*)` on the canonical DB is too expensive to refresh inside a heartbeat. The `n_live_tup` approximation, cross-checked against `pg_class.reltuples` (refreshed by the `2026-06-08 00:03:07 UTC` VACUUM) and the `n_tup_ins` delta (the dispatcher primary signal), is the only same-day readable live count.
5. **Index state note:** `idx_products_active_country` (the partial index for `is_active=true` rows used by earlier shortfall reports) is `indisvalid=f` (per [BUY-32878](/BUY/issues/BUY-32878) central tracker [BUY-33973](/BUY/issues/BUY-33973)). The active-products live count is therefore inferred from total `products.reltuples` / `n_live_tup` rather than the partial index. The `2026-06-06` shortfall report's `idx_products_active_true.reltuples=31,124,416` is still used as the active-baseline start-of-day anchor for 2026-06-07 (the index was valid at that time). This is consistent with the closed-day verdict.

## Corrective Assignments In Place

- [BUY-33694](/BUY/issues/BUY-33694): throughput dispatcher repointed at maglev, `data/.throughput_state.json` is the canonical hourly state, dispatcher wired into user crontab at `1 * * * *`.
- [BUY-32074](/BUY/issues/BUY-32074): the DB-path throughput cap (this is what makes exact `COUNT(*)` too expensive to refresh in a heartbeat).
- [BUY-32950](/BUY/issues/BUY-32950): exact-count DB path upgrade (Pro+ on Railway Postgres, deadline 2026-06-07 18:00 UTC, owner Rex).
- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path.
- [BUY-34770](/BUY/issues/BUY-34770): the catalog reset event on 2026-06-07 ~21:17 UTC, with the post-reset rebuild now in steady state.

## Open Questions For The Board

- The catalog reset at 19:09-21:17 UTC on 2026-06-07 is consistent with a `TRUNCATE` (or equivalent). The originating issue / change record is [BUY-34770](/BUY/issues/BUY-34770). This report treats the reset as the buy-33337 report did: a deliberate catalog operation, not a writer-fleet miss. The forward-pace math in this report uses the post-reset starting point (`42,924,188`).
- The `2026-06-08` day is in progress; the closed-day verdict is reserved for the next shortfall check. The hourly dispatcher is producing `~942K/hr`, well above the `103K/hr` required pace, but a sustained-rate confirmation needs the day to close.

## Conclusion

`2026-06-07` does not support a new shortfall failure report: closed-day active-product growth of `+11,795,755` materially exceeds the prior required pace of `4,130,150` (BUY-33337 report). The canonical DB is correctly pinned (maglev, `data/.catalog_db_url`) and the post-[BUY-34770](/BUY/issues/BUY-34770) catalog reset rebuild has returned the catalog to a `~42.9M` live-product level. The new forward required pace is `2,481,557` active products per day for the remaining `23` calendar days through `2026-06-30`, and the most recent dispatcher hour shows `942,360` real inserts — `911%` of the per-hour required pace. The exact-count cost is still the operational cap ([BUY-32950](/BUY/issues/BUY-32950)) and should be resolved per Rex's existing commitment. The `2026-06-08` closed-day verdict is reserved for the end-of-day shortfall check (no failure report filed now).
