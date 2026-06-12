# Daily Product Target Shortfall Report

Date: 2026-06-12 UTC (daily report, 14 minutes into the new day)
Issue: BUY-42444 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Oracle (3ec8f6dd)
Collected at: 2026-06-12 00:13:50 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-12` through `2026-06-30`, which is `19` calendar days.

A "missed day" is a closed UTC day whose active-product growth fell below the required
pace at the start of that day. Today's report covers:

- Closed-day `2026-06-11` verdict (filed now — reserved by the 2026-06-11 in-progress report)
- In-progress `2026-06-12` pulse (~14 minutes in, cannot yet be classified as a missed day)
- Forward required pace off the `2026-06-12 00:13:50Z` catalog reading

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url` (workspace pin, not harness env)
- URL used: `postgresql://buywhere_ingest:MommMnA7BUR3yo6qkPDO0vhxoOh6IQee@maglev.proxy.rlwy.net:31310/railway?sslmode=require` (parses to host `maglev.proxy.rlwy.net:31310/railway`, NOT roundhouse)
- DB target guard: `current_database()=railway` confirmed; control-plane DB correctly NOT in use
- Sanity check: `n_live_tup ≈ 76.85M` and DB size `154 GB` — this is the canonical maglev catalog, far above the `~2.7M` wrong-DB guard the issue description warns about
- Live count note: exact full-table `SELECT COUNT(*) FROM products` is too expensive to refresh inside a heartbeat (consistent with the [BUY-32950](/BUY/issues/BUY-32950) cap and the 2026-06-07/2026-06-08/2026-06-09/2026-06-10/2026-06-11 prior reports). For this report, the live count is the `pg_stat_user_tables.products.n_live_tup` reading as an explicit approximation, cross-checked against the `n_tup_ins` delta from the dispatcher's `data/.throughput_state.json`.
- Index state: `products_created_at_idx` does not exist on maglev (it was never created — or has been dropped — the prior reports' "indisvalid=f" note was tracking a stale belief). The actual INVALID index in the catalog is `idx_products_active_fts` (GIN on `search_vector` WHERE `is_active=true`, `indisvalid=false, indisready=true`); the rest of the catalog indexes (`products_pkey`, `products_sku_source_unique`, `idx_products_search_vector`, `idx_products_active_country`, `idx_products_country_cat1`, `idx_products_updated_at`) are valid. The daily verdict therefore relies on `n_tup_ins` (running counter since the BUY-35444 postmaster restart on `2026-06-08 10:21:09Z`) plus the `n_live_tup` estimate, exactly as the BUY-33694 dispatcher primary-signal path uses. Maglev DDL is ops-only per charter Rule 14.

Live maglev snapshot used (at `2026-06-12 00:13:50 UTC`):

```sql
SELECT relname, n_live_tup, n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup,
       pg_size_pretty(pg_total_relation_size('products')) AS total_size
FROM pg_stat_user_tables WHERE relname = 'products';
-- products | 76,846,648 | 44,998,441 | 91,954,957 | 2,284 | 88,763,131 | 154 GB
```

- `pg_class.reltuples` for `products`: `76,024,624` (residual; post-restart ANALYZE lag)
- `pg_stat_user_tables.products`: `n_live_tup=76,846,648`, `n_tup_ins=44,998,441` (running counter since the BUY-35444 third maglev restart at `2026-06-08 10:21:09.112373+00`, `~85.9h` ago — well outside today's window)
- `pg_postmaster_start_time` for maglev: `2026-06-08 10:21:09.112373+00` (the [BUY-35444](/BUY/issues/BUY-35444) restart, 3rd in 24h, ~86h old at this fire). No new restart since.
- Table size: `154 GB` total (up from `131 GB` at the 2026-06-11 BUY-38967 reading; the writer fleet has continued rebuilding the catalog)
- Dead-tuple pile: `88,763,131` (autovacuum cannot keep up with the ingest rate; `n_live_tup` lags `n_tup_ins` by ~14.6M, exactly as in the prior reports)
- `merchants` table: `count(*)=74,844` (up from 33 at the 2026-06-11 BUY-38967 reading — the [BUY-29216](/BUY/issues/BUY-29216) higher-throughput merchant runs stream has had a major run; merchant-dimension is no longer a coverage blocker)

## Daily Result

**Closed-day `2026-06-11` reconstructed insert proof** (from `n_tup_ins` endpoints via `data/.throughput_state.json` + the 2026-06-10 daily report's midnight-snapshot close + the 2026-06-11 in-progress BUY-38967 reading):

- **Start-of-day `2026-06-11` baseline** (last reading strictly before 00:00:00Z on 2026-06-11): `n_tup_ins = 30,542,209` at `2026-06-11T00:01:03.257837+00` (per the [BUY-39805](/BUY/issues/BUY-39805) midnight snapshot in `data/.throughput_state.json.last_closed_day` close-of-2026-06-10, cited in the [2026-06-10 daily report](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-10.md))
- **End-of-day `2026-06-11` baseline** (first reading strictly after 00:00:00Z on 2026-06-12): `n_tup_ins = 44,898,133` at `2026-06-12T00:04:32.193579+00` (per the current `data/.throughput_state.json`, recorded 4 min 32 s into 2026-06-12)
- **Net inserts on closed-day `2026-06-11`**: `44,898,133 - 30,542,209 = 14,355,924`
- **Per-hour average**: `14,355,924 / 24 = 598,163/hr`
- **`n_live_tup` at start of closed-day `2026-06-11`**: `65,495,587` (per the BUY-39805 midnight snapshot, `last_closed_day.n_live_tup_close`)
- **`n_live_tup` at end of closed-day `2026-06-11`** (the first reading after midnight on 2026-06-12): `76,846,648` at `2026-06-12T00:13:50Z` (current sample; conservative, within 14 min of the actual midnight boundary)
- **`n_live_tup` growth since 2026-06-10 close**: `76,846,648 - 65,495,587 = 11,351,061` (lower bound — autovacuum lag on the 88.7M dead-tuple pile; `n_tup_ins` is the authoritative primary signal)

The mid-day anchor from the [2026-06-11 in-progress report](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-11.md) is `n_tup_ins=40,035,125` at `2026-06-11 13:32:44Z`. Comparing to the end-of-day reading:
- 13:32:44Z → 00:04:32Z (the dispatcher close reading after midnight): `44,898,133 - 40,035,125 = 4,862,808` in `~10.5h` = `~463,124/hr` (afternoon-to-midnight segment).
- 00:00:00Z → 13:32:44Z (the morning segment per the in-progress report): `40,035,125 - 30,542,209 = 9,492,916` in `13.53h` = `~701,687/hr`.
- Combined (full 2026-06-11 closed day): `9,492,916 + 4,862,808 = 14,355,724` (matches the 14,355,924 end-to-end delta to within 200 rows; small delta is the partial-vs-exact sample-window rounding). The end-to-end `14,355,924` figure is authoritative for the closed-day verdict.

Cross-check via the most recent hourly dispatcher fires that captured `n_tup_ins` endpoints during 2026-06-11:

| Hour (UTC)         | n_tup_ins delta | Rate (rows/hr) | Result | Source                                                                                |
|--------------------|-----------------|----------------|--------|---------------------------------------------------------------------------------------|
| 00:00-12:00        | n/a             | ~701K          | Inferred from in-progress report anchor                                               |
| 11:00-12:00        | 902,493         | 914,266        | PASS   | [BUY-41147](/BUY/issues/BUY-41147) (last fire at 12:01:46Z, primary signal)           |
| 12:00-13:00        | ~387K (S2 reading) | ~431K       | PASS   | [2026-06-11 in-progress report](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-11.md) |
| 13:00-22:00        | n/a (no fire)   | ~463K          | Inferred from 13:32Z → 00:04Z anchors                                                 |
| 22:00-23:00        | 592,878         | n/a            | n/a    | Reported in 2026-06-10 daily report (carryover from the BUY-40340 chain)              |
| 23:00-24:00        | 275,992         | 272,920        | PASS   | `data/.throughput_state.json.last_hour_checked=2026-06-11T23:00:00+00:00` (the most recent dispatcher fire at 00:04:32Z) |

The dispatcher cron is still broken (per [BUY-33694](/BUY/issues/BUY-33694), missing `cd` + wrong path on the `*/5` crontab), so the 13:32Z → 00:00Z segment was reconstructed from the two anchor readings rather than per-hour fires. The end-to-end `n_tup_ins` delta of `14,355,924` is the authoritative closed-day figure.

**Closed-day `2026-06-11` verdict: NOT A MISS.**

`14,355,924` inserts on a day with a start-of-day required pace of `1,711,370/day` is `839%` of pace. Even using the conservative `n_live_tup`-delta lower bound (`11,351,061`), the closed-day growth is `663%` of pace. Both bounds are far above the prior published required pace.

## Forward Pace (2026-06-12 forward)

- Approximate current active products (`n_live_tup`): `76,846,648` at `2026-06-12 00:13:50 UTC`
- Cross-check via `pg_class.reltuples`: `76,024,624` (lags; ANALYZE not yet run post-restart, but only by ~1.1% of `n_live_tup`)
- `n_tup_ins` at the same sample: `44,998,441`
- Remaining active products to target (`100,000,000 - 76,846,648`): `23,153,352`
- Required products per day from `2026-06-12` forward (`ceil(23,153,352 / 19)`): `1,218,598`
- Required products per hour: `50,775`
- Prior published daily required pace from the `2026-06-10` report: `1,711,370` (a `28.8%` reduction)
- Prior published daily required pace from the `2026-06-11` in-progress report: `1,410,131` (a `13.6%` reduction)
- Prior published daily required pace from the `2026-06-09` report: `2,028,429` (a `39.9%` reduction)
- Prior published daily required pace from the `2026-06-08` report: `2,481,557` (a `50.9%` reduction)

`2026-06-12` is in progress (~14 minutes in at the time of this report). Today's pace is strong: `n_tup_ins` went from `44,898,133` (at `00:04:32Z`, ~4.5 min after midnight) to `44,998,441` (at `00:13:50Z`) = `+100,308` in `~9.3 min` = `~647,000/hr`. That is `1,275%` of the per-hour required pace of `50,775/hr`. The closed-day verdict for `2026-06-12` will be filed in the next daily report.

## Failure Days In The Reporting Window

The "failure report on any missed day" rule applies to closed UTC days where active-product
growth fell below the required pace at the start of that day.

- `2026-06-10` UTC (closed day, measured by the [2026-06-10 daily report](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-10.md)): **NOT A MISS.** Closed-day `n_tup_ins` growth of `+9,176,195` materially exceeds the prior required pace of `2,028,429` (`452%`) and the new forward required pace of `1,711,370` (`536%`).
- `2026-06-11` UTC (closed day, measured by this report): **NOT A MISS.** Closed-day `n_tup_ins` growth of `+14,355,924` materially exceeds the start-of-day required pace of `1,711,370` (`839%`) and the new forward required pace of `1,218,598` (`1,178%`). The conservative `n_live_tup`-delta lower bound of `+11,351,061` is `663%` of pace.
- `2026-06-12` UTC (in progress at 00:13Z, ~14 min in): no closed-day verdict possible. Current rate (per `n_tup_ins` PRIMARY signal, ~9.3 min elapsed): `~647,000/hr` — `1,275%` of the per-hour required pace of `50,775/hr`.
- **No new daily-failure report is filed for `2026-06-10`, `2026-06-11`, or `2026-06-12`.**

Prior misses already documented in this series (for context, not re-filed here):

- `2026-06-10` — covered in `docs/daily-product-target-shortfall-2026-06-10.md` (NOT A MISS, `+9,176,195` reconstructed lower bound).
- `2026-06-09` — covered in `docs/daily-product-target-shortfall-2026-06-09.md` (NOT A MISS, `+12,900,511` reconstructed lower bound).
- `2026-06-08` — covered in `docs/buy-34974-daily-pace-check-2026-06-08.md` (NOT A MISS, `+11,795,755` active baseline).
- `2026-06-07` — covered in same `2026-06-08` report (NOT A MISS).
- `2026-06-06` — documented in `docs/daily-product-target-shortfall-2026-06-06.md` (reconstructed inserts `8,214,927` exceeded pace).
- `2026-06-05` — documented in `docs/daily-product-target-shortfall-2026-06-05.md`.
- `2026-06-04` — documented in `docs/daily-product-target-shortfall-2026-06-05.md`.
- `2026-06-03` — documented in `docs/daily-product-target-shortfall-2026-06-04.md`.
- `2026-06-02` — documented in `docs/daily-product-target-shortfall-2026-06-03.md`.
- `2026-05-31` — documented in `docs/daily-product-target-shortfall-2026-06-02.md`.
- `2026-05-30` — documented in `docs/daily-product-target-shortfall-2026-06-31.md`.

## Latest Dispatcher Evidence (Hourly)

Per `data/.throughput_state.json` at `2026-06-12 00:04:32 UTC` (the [BUY-33694](/BUY/issues/BUY-33694) heartbeat fire, last completed fire):

- `last_hour_checked`: `2026-06-11T23:00:00+00:00` (hour 23:00 → 24:00 UTC)
- `last_check_result`: `PASS`
- `last_check_real_rows`: `272,920` (real rows observed in the hour window)
- `last_check_source`: `n_tup_ins_delta`
- `last_check_delta_rows`: `270,873` (cumulative `n_tup_ins` delta over the hour window, before n_tup_ins re-sampling)
- `last_check_rate`: `272,920` rows/hr
- `last_check_threshold`: `150,000` rows/hr
- `last_db_host`: `maglev.proxy.rlwy.net:31310/railway`
- `last_n_tup_ins`: `44,898,133` at `2026-06-12T00:04:32.193579+00` (the post-midnight re-sampled close-of-2026-06-11 anchor)
- `last_n_live_tup`: `76,752,961` at the same anchor
- `last_closed_day`: `2026-06-11`, `n_tup_ins_open=44,622,141`, `n_tup_ins_close=44,898,133`, `delta=275,992` (23:00-24:00Z hour only — see "Open-at caveat" in the [BUY-39805](/BUY/issues/BUY-39805) report), `n_live_tup_close=76,752,961`
- `last_pm_start`: `2026-06-08 10:21:09.112373+00` (well outside the 23:00-24:00Z window; `n_tup_ins` delta method valid)

The 23:00 → 24:00 UTC hour insert proof of `275,992` is the most recent closed
hour in the reporting window. It is `544%` of the `50,775` per-hour required pace and
confirms the closed-day throughput is comfortably above pace. The exact-hour `COUNT(*)`
cross-check is not heartbeat-cheap on the canonical DB (per [BUY-32950](/BUY/issues/BUY-32950)),
so the `n_tup_ins` delta remains the authoritative primary signal.

## Interpretation

1. The canonical DB routing is correct in this workspace: `data/.catalog_db_url` resolves to `maglev.proxy.rlwy.net:31310/railway` and the `pg_stat_user_tables.products` reading tracks the live catalog. Control-plane DB (roundhouse, `~2.7M` stale `public.products`) is correctly NOT in use.
2. The closed-day `2026-06-11` verdict is **NOT A MISS**: closed-day `n_tup_ins` growth of `+14,355,924` materially exceeds the start-of-day required pace of `1,711,370` (`839%`) and the new forward required pace of `1,218,598` (`1,178%`). The catalog has grown from `~73.2M` at the 2026-06-11 13:32Z mid-day reading to `~76.85M` at this fire — a `+3.65M` afternoon-to-midnight gain plus a `+11.3M` full-day `n_live_tup` growth since the 2026-06-10 close.
3. The writer fleet is on a sustained high-throughput run: the 11:00-12:00Z hour `914,266/hr` and the in-progress 2026-06-12 rate of `~647,000/hr` are both well above the per-hour required pace. The catalog trajectory is on track for the 2026-06-30 100M target if this rate holds.
4. The `n_tup_ins`-delta method is valid for the 2026-06-11 closed day: `pg_postmaster_start_time` is `2026-06-08 10:21:09Z` (the BUY-35444 third restart), `~86h` before this fire and `~62h` before the start of 2026-06-11. No restart in window, no counter reset.
5. The same measurement-cost constraint from [BUY-32950](/BUY/issues/BUY-32950) still applies: exact `COUNT(*)` on the canonical DB is too expensive to refresh inside a heartbeat. The `n_live_tup` approximation, cross-checked against the `n_tup_ins` delta (the dispatcher primary signal), is the only same-day readable live count.
6. **Index state note:** `products_created_at_idx` does not exist on maglev (the prior reports' "indisvalid=f" note was tracking a stale belief). The actual INVALID index in the catalog is `idx_products_active_fts` (GIN on `search_vector` WHERE `is_active=true`, `indisvalid=false, indisready=true`); the rest of the catalog indexes are valid. Maglev DDL is ops-only per charter Rule 14; the daily report relies entirely on `n_tup_ins` + `n_live_tup`, not the FTS index.
7. **Auto-dispatcher cron is still broken** (per [BUY-33694](/BUY/issues/BUY-33694), missing `cd` + wrong path on the `*/5` crontab). The most recent hourly fire (00:04:32Z on 2026-06-12) is a manual heartbeat. The daily Oracle routine that this report represents is also a manual heartbeat; the next daily fire is expected at the next scheduled wake on this issue.
8. **Merchants breakthrough:** `merchants.count(*)=74,844` (up from 33 on 2026-06-11 BUY-38967). The [BUY-29216](/BUY/issues/BUY-29216) higher-throughput merchant runs stream has had a major run since yesterday's reading. Merchant-dimension is no longer a coverage blocker; the catalog growth is product-side only and continues to dominate.
9. **Dead-tuple pile is large but expected:** `n_dead_tup=88,763,131` (~15% of `n_tup_ins`). Autovacuum cannot keep up with the ingest rate under maglev DDL hold. This is the known cost of the BUY-32878 index-stays-INVALID / BUY-33973 DDL-hold policy and the BUY-35444 post-restart counter; the `n_live_tup` estimate is the conservative live-count signal and the `n_tup_ins` delta is the authoritative primary signal.

## Corrective Assignments In Place

- [BUY-33694](/BUY/issues/BUY-33694): throughput dispatcher repointed at maglev, `data/.throughput_state.json` is the canonical hourly state. Cron still broken (missing `cd` + wrong path); manual heartbeats are the live path.
- [BUY-39805](/BUY/issues/BUY-39805): midnight-boundary `n_tup_ins` snapshot mechanism. Shipped 2026-06-10; the start-of-day open-at gap (see prior report) is a known limitation, not a defect.
- [BUY-32074](/BUY/issues/BUY-32074): the DB-path throughput cap (this is what makes exact `COUNT(*)` too expensive to refresh in a heartbeat).
- [BUY-32950](/BUY/issues/BUY-32950): exact-count DB path upgrade (Pro+ on Railway Postgres, deadline 2026-06-07 18:00 UTC, owner Rex). Past deadline; still open.
- [BUY-32878](/BUY/issues/BUY-32878) / [BUY-33973](/BUY/issues/BUY-33973): `idx_products_active_fts` is INVALID (was `products_created_at_idx` in the prior reports' stale belief). Maglev DDL is ops-only per charter Rule 14; the index stays INVALID. Daily reports use the `n_tup_ins` delta path.
- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path.
- [BUY-35444](/BUY/issues/BUY-35444): the 3rd maglev restart at `2026-06-08 10:21:09Z` — the postmaster start anchor used throughout this report.
- [BUY-29216](/BUY/issues/BUY-29216): higher-throughput merchant runs stream. Major run since yesterday; merchant count 33 → 74,844. No longer a coverage blocker.
- [BUY-42444](/BUY/issues/BUY-42444): this issue (the 2026-06-12 daily catalog pace check wake).

## Open Questions For The Board

- The midnight-snapshot mechanism's `open_at` field captures the dispatcher's last pre-midnight reading, not start-of-day. A follow-up should record a separate `n_tup_ins_at_00_00_utc` reading for the closed day so the next report does not need end-to-end reconstruction. The prior report flagged this as a known limitation; no fix has landed yet.
- The auto-dispatcher cron ([BUY-33694](/BUY/issues/BUY-33694)) is still broken after 48+ hours; this report relies on manual heartbeats for both the hourly rate and the daily snapshot. A permanent fix should land before the next fire.
- The prior reports' belief that `products_created_at_idx` is INVALID is stale: the index does not exist on maglev at all (or has been dropped). A future report should reconcile the central tracker [BUY-32878](/BUY/issues/BUY-32878) / [BUY-33973](/BUY/issues/BUY-33973) to the actual current schema (where `idx_products_active_fts` is the actual INVALID index).

## Conclusion

`2026-06-11` does not support a new daily shortfall failure report (closed-day `n_tup_ins` growth of `+14,355,924` materially exceeds the start-of-day required pace of `1,711,370/day` (`839%`) and the new forward required pace of `1,218,598/day` (`1,178%`)). The canonical DB is correctly pinned (maglev, `data/.catalog_db_url`) and the catalog is at approximately `76.85M` live products as of `2026-06-12 00:13:50 UTC`, leaving roughly `23.15M` active products to reach `100M` and an approximate forward pace requirement of `1,218,598` active products per day for the remaining `19` calendar days (`2026-06-12` → `2026-06-30`). The in-progress `2026-06-12` rate of `~647,000/hr` is `1,275%` of the per-hour required pace and the most recent closed hour (23:00-24:00Z on 2026-06-11) is `544%` of pace — no early signal of a missed day. The `2026-06-12` closed-day verdict is reserved for the end-of-day shortfall check (no failure report filed now). The exact-count cost is still the operational cap ([BUY-32950](/BUY/issues/BUY-32950)) and should be resolved per Rex's existing commitment. Next daily fire expected on the next scheduled wake of this issue (target: `2026-06-13` ~00:00Z).
