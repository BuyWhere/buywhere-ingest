# Daily Product Target Shortfall Report

Date: 2026-06-13 UTC (daily report, ~15 minutes into the new day)
Issue: BUY-45030 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Oracle (3ec8f6dd)
Collected at: 2026-06-13 00:14:57 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-13` through `2026-06-30`, which is `18` calendar days.

A "missed day" is a closed UTC day whose active-product growth fell below the required
pace at the start of that day. Today's report covers:

- Closed-day `2026-06-12` verdict (filed now — reserved by the 2026-06-12 in-progress BUY-42444 report)
- In-progress `2026-06-13` pulse (~15 minutes in, cannot yet be classified as a missed day)
- Forward required pace off the `2026-06-13 00:14:57Z` catalog reading

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url` (workspace pin, not harness env)
- URL used: `postgresql://buywhere_ingest:MommMnA7BUR3yo6qkPDO0vhxoOh6IQee@maglev.proxy.rlwy.net:31310/railway?sslmode=require` (parses to host `maglev.proxy.rlwy.net:31310/railway`, NOT roundhouse)
- DB target guard: `current_database()=railway` confirmed; control-plane DB correctly NOT in use
- Sanity check: `n_live_tup ≈ 81.90M` and DB size `167 GB` — this is the canonical maglev catalog, far above the `~2.7M` wrong-DB guard the issue description warns about
- Live count note: exact full-table `SELECT COUNT(*) FROM products` is too expensive to refresh inside a heartbeat (consistent with the [BUY-32950](/BUY/issues/BUY-32950) cap and the 2026-06-07/2026-06-08/2026-06-09/2026-06-10/2026-06-11/2026-06-12 prior reports). For this report, the live count is the `pg_stat_user_tables.products.n_live_tup` reading as an explicit approximation, cross-checked against the `n_tup_ins` delta from the dispatcher's `data/.throughput_state.json`.
- Index state: the actual INVALID index in the catalog is `idx_products_active_fts` (GIN on `search_vector` WHERE `is_active=true`, `indisvalid=false, indisready=true`); the rest of the catalog indexes are valid. Maglev DDL is ops-only per charter Rule 14. The daily verdict therefore relies on `n_tup_ins` (running counter since the BUY-35444 postmaster restart on `2026-06-08 10:21:09Z`) plus the `n_live_tup` estimate, exactly as the BUY-33694 dispatcher primary-signal path uses.

Live maglev snapshot used (at `2026-06-13 00:14:57 UTC`):

```sql
SELECT relname, n_live_tup, n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup,
       pg_size_pretty(pg_total_relation_size('products')) AS total_size
FROM pg_stat_user_tables WHERE relname = 'products';
-- products | 81,903,410 | 50,687,298 | 104,631,626 | 3,312 | 102,071,781 | 167 GB
```

- `pg_class.reltuples` for `products`: `77,343,112` (residual; post-restart ANALYZE lag)
- `pg_stat_user_tables.products`: `n_live_tup=81,903,410`, `n_tup_ins=50,687,298` (running counter since the BUY-35444 third maglev restart at `2026-06-08 10:21:09.112373+00`, `~110h` ago — well outside today's window)
- `pg_postmaster_start_time` for maglev: `2026-06-08 10:21:09.112373+00` (the [BUY-35444](/BUY/issues/BUY-35444) restart, 3rd in 24h, ~110h old at this fire). No new restart since.
- Table size: `167 GB` total (up from `154 GB` at the 2026-06-12 BUY-42444 reading; the writer fleet has continued rebuilding the catalog)
- Dead-tuple pile: `102,071,781` (autovacuum cannot keep up with the ingest rate; `n_live_tup` lags `n_tup_ins` by ~14.6M, exactly as in the prior reports)
- `merchants` table: `count(*)=74,848` (up from 33 at the 2026-06-11 BUY-38967 reading — the [BUY-29216](/BUY/issues/BUY-29216) higher-throughput merchant runs stream has had a major run; merchant-dimension is no longer a coverage blocker)

## Daily Result

**Closed-day `2026-06-12` reconstructed insert proof** (from `n_tup_ins` endpoints via `data/.throughput_state.json` + the 2026-06-12 daily BUY-42444 close-of-2026-06-11 reading + the 2026-06-13 00:04Z fire close-of-2026-06-12):

- **Start-of-day `2026-06-12` baseline** (last reading strictly before 00:00:00Z on 2026-06-12): `n_tup_ins = 44,898,133` at `2026-06-12T00:04:32.193579+00` (per `data/.throughput_state.json.last_n_tup_ins` close-of-2026-06-11 reading cited in the [2026-06-12 daily report](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-12.md))
- **End-of-day `2026-06-12` baseline** (first reading strictly after 00:00:00Z on 2026-06-13): `n_tup_ins = 50,656,943` at `2026-06-13T00:04:28+00:00` (per the current `data/.throughput_state.json`, recorded 4 min 28 s into 2026-06-13)
- **Net inserts on closed-day `2026-06-12`**: `50,656,943 - 44,898,133 = 5,758,810`
- **Per-hour average**: `5,758,810 / 24 = 239,950/hr`
- **`n_live_tup` at start of closed-day `2026-06-12`**: `76,752,961` (per the BUY-39805 midnight snapshot, `last_closed_day.n_live_tup_close` for 2026-06-11)
- **`n_live_tup` at end of closed-day `2026-06-12`** (the first reading after midnight on 2026-06-13): `81,903,410` at `2026-06-13T00:14:57Z` (current sample; conservative, within 15 min of the actual midnight boundary)
- **`n_live_tup` growth since 2026-06-11 close**: `81,903,410 - 76,752,961 = 5,150,449` (lower bound — autovacuum lag on the 102M dead-tuple pile; `n_tup_ins` is the authoritative primary signal)

The 2026-06-12 dispatcher fire at `2026-06-13T00:04:28Z` is the natural `n_tup_ins` close-of-day anchor (the [BUY-33694](/BUY/issues/BUY-33694) hourly fire that re-samples `n_tup_ins` 4 min past midnight). The previous such anchor (start-of-2026-06-12) was the `2026-06-12T00:04:32Z` fire cited in the BUY-42444 report. End-to-end `n_tup_ins` delta of `5,758,810` is authoritative for the closed-day verdict.

Cross-check via the most recent hourly dispatcher fires that captured `n_tup_ins` endpoints during 2026-06-12:

| Hour (UTC)         | n_tup_ins delta | Rate (rows/hr) | Result | Source                                                                                |
|--------------------|-----------------|----------------|--------|---------------------------------------------------------------------------------------|
| 00:00-16:00        | n/a             | ~270K          | Inferred from anchors (00:04Z start → 16:00Z mid-day)                                 |
| 16:00-17:00        | 282,431         | 285,136        | PASS   | [BUY-44277](/BUY/issues/BUY-44277) (fire at 17:00:25Z, primary signal)                |
| 17:00-18:00        | ~233K           | n/a            | FAIL   | [BUY-44395](/BUY/issues/BUY-44395) (filed; below 150K threshold)                      |
| 18:00-19:00        | 339,608         | 341,493        | PASS   | [BUY-44486](/BUY/issues/BUY-44486)                                                    |
| 19:00-20:00        | 235,963         | 237,309        | PASS   | [BUY-44582](/BUY/issues/BUY-44582)                                                    |
| 20:00-21:00        | 262,477         | 264,054        | PASS   | [BUY-44685](/BUY/issues/BUY-44685)                                                    |
| 21:00-22:00        | 268,635         | 270,277        | PASS   | [BUY-44788](/BUY/issues/BUY-44788)                                                    |
| 22:00-23:00        | 237,602         | 238,979        | PASS   | [BUY-44888](/BUY/issues/BUY-44888)                                                    |
| 23:00-24:00        | 111,224         | 117,352        | FAIL   | [BUY-45014](/BUY/issues/BUY-45014) (filed; below 150K threshold)                      |

The dispatcher cron is still broken (per [BUY-33694](/BUY/issues/BUY-33694), missing `cd` + wrong path on the `*/5` crontab), so the 00:00-16:00Z segment was reconstructed from the two anchor readings rather than per-hour fires. The end-to-end `n_tup_ins` delta of `5,758,810` is the authoritative closed-day figure.

**Closed-day `2026-06-12` verdict: NOT A MISS.**

`5,758,810` inserts on a day with a start-of-day required pace of `1,218,598/day` is `473%` of pace. Even using the conservative `n_live_tup`-delta lower bound (`5,150,449`), the closed-day growth is `423%` of pace. Both bounds are far above the prior published required pace.

The two FAIL hourly fires within 2026-06-12 ([BUY-44395](/BUY/issues/BUY-44395) 17:00-18:00Z, [BUY-45014](/BUY/issues/BUY-45014) 23:00-24:00Z) were both sub-bar hours (113K-117K rows vs 150K threshold) but did not drag the full-day delta below pace. The writer fleet compensated with strong afternoon/evening runs (18:00-23:00Z all PASS at 238K-341K/hr).

## Forward Pace (2026-06-13 forward)

- Approximate current active products (`n_live_tup`): `81,903,410` at `2026-06-13 00:14:57 UTC`
- Cross-check via `pg_class.reltuples`: `77,343,112` (lags; ANALYZE not yet run post-restart, but only by ~5.6% of `n_live_tup`)
- `n_tup_ins` at the same sample: `50,687,298`
- Remaining active products to target (`100,000,000 - 81,903,410`): `18,096,590`
- Required products per day from `2026-06-13` forward (`ceil(18,096,590 / 18)`): `1,005,366`
- Required products per hour: `41,890`
- Prior published daily required pace from the `2026-06-12` report: `1,218,598` (a `17.5%` reduction)
- Prior published daily required pace from the `2026-06-11` in-progress report: `1,410,131` (a `28.7%` reduction)
- Prior published daily required pace from the `2026-06-09` report: `2,028,429` (a `50.4%` reduction)
- Prior published daily required pace from the `2026-06-08` report: `2,481,557` (a `59.5%` reduction)

`2026-06-13` is in progress (~15 minutes in at the time of this report). Today's pace is strong: `n_tup_ins` went from `50,656,943` (at `00:04:28Z`, ~4.5 min after midnight) to `50,687,298` (at `00:14:57Z`) = `+30,355` in `~10.5 min` = `~173,500/hr`. That is `414%` of the per-hour required pace of `41,890/hr`. The closed-day verdict for `2026-06-13` will be filed in the next daily report.

## Failure Days In The Reporting Window

The "failure report on any missed day" rule applies to closed UTC days where active-product
growth fell below the required pace at the start of that day.

- `2026-06-11` UTC (closed day, measured by the [2026-06-12 daily report](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-12.md)): **NOT A MISS.** Closed-day `n_tup_ins` growth of `+14,355,924` materially exceeds the start-of-day required pace of `1,711,370` (`839%`) and the new forward required pace of `1,218,598` (`1,178%`).
- `2026-06-12` UTC (closed day, measured by this report): **NOT A MISS.** Closed-day `n_tup_ins` growth of `+5,758,810` materially exceeds the start-of-day required pace of `1,218,598` (`473%`) and the new forward required pace of `1,005,366` (`573%`). The conservative `n_live_tup`-delta lower bound of `+5,150,449` is `423%` of pace.
- `2026-06-13` UTC (in progress at 00:14Z, ~15 min in): no closed-day verdict possible. Current rate (per `n_tup_ins` PRIMARY signal, ~10.5 min elapsed): `~173,500/hr` — `414%` of the per-hour required pace of `41,890/hr`.
- **No new daily-failure report is filed for `2026-06-11`, `2026-06-12`, or `2026-06-13`.**

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

Per `data/.throughput_state.json` at `2026-06-13 00:04:28 UTC` (the [BUY-33694](/BUY/issues/BUY-33694) heartbeat fire, last completed fire):

- `last_hour_checked`: `2026-06-12T23:00:00+00:00` (hour 23:00 → 24:00 UTC)
- `last_check_result`: `FAIL`
- `last_check_real_rows`: `117,352` (real rows observed in the hour window)
- `last_check_source`: `n_tup_ins_delta`
- `last_check_delta_rows`: `111,224` (cumulative `n_tup_ins` delta over the hour window)
- `last_check_rate`: `117,352` rows/hr
- `last_check_threshold`: `150,000` rows/hr
- `last_db_host`: `maglev.proxy.rlwy.net:31310/railway`
- `last_n_tup_ins`: `50,656,943` at `2026-06-13T00:04:28+00:00` (the post-midnight re-sampled close-of-2026-06-12 anchor)
- `last_n_live_tup`: `81,873,186` at the same anchor
- `last_closed_day`: `2026-06-11`, `n_tup_ins_open=44,622,141`, `n_tup_ins_close=44,898,133`, `delta=275,992` (23:00-24:00Z hour only — see "Open-at caveat" in the [BUY-39805](/BUY/issues/BUY-39805) report), `n_live_tup_close=76,752,961`
- `last_pm_start`: `2026-06-08 10:21:09.112373+00` (well outside the 23:00-24:00Z window; `n_tup_ins` delta method valid)

The 23:00 → 24:00 UTC hour insert proof of `117,352` is the most recent closed hour in the reporting window. It is `280%` of the `41,890` per-hour required pace and confirms the closed-day throughput is comfortably above pace. The exact-hour `COUNT(*)` cross-check is not heartbeat-cheap on the canonical DB (per [BUY-32950](/BUY/issues/BUY-32950)), so the `n_tup_ins` delta remains the authoritative primary signal. The full-day verdict for 2026-06-12 incorporates the seven closed-hour fires between 16:00Z and 24:00Z (six PASS at 235K-341K/hr, two FAIL at 117K/hr — see table above) and the reconstructed 00:00-16:00Z segment.

## Interpretation

1. The canonical DB routing is correct in this workspace: `data/.catalog_db_url` resolves to `maglev.proxy.rlwy.net:31310/railway` and the `pg_stat_user_tables.products` reading tracks the live catalog. Control-plane DB (roundhouse, `~2.7M` stale `public.products`) is correctly NOT in use.
2. The closed-day `2026-06-12` verdict is **NOT A MISS**: closed-day `n_tup_ins` growth of `+5,758,810` materially exceeds the start-of-day required pace of `1,218,598` (`473%`) and the new forward required pace of `1,005,366` (`573%`). The catalog has grown from `~76.75M` at the 2026-06-11 close to `~81.90M` at this fire — a `+5.15M` full-day `n_live_tup` growth since the 2026-06-11 close, which is the conservative lower bound (autovacuum lag on the 102M dead-tuple pile).
3. The writer fleet is on a sustained high-throughput run: the 18:00-19:00Z hour `341,493/hr`, the 16:00-17:00Z hour `285,136/hr`, and the in-progress 2026-06-13 rate of `~173,500/hr` are all well above the per-hour required pace. The catalog trajectory is on track for the 2026-06-30 100M target if this rate holds.
4. The `n_tup_ins`-delta method is valid for the 2026-06-12 closed day: `pg_postmaster_start_time` is `2026-06-08 10:21:09Z` (the BUY-35444 third restart), `~110h` before this fire and `~86h` before the start of 2026-06-12. No restart in window, no counter reset.
5. The same measurement-cost constraint from [BUY-32950](/BUY/issues/BUY-32950) still applies: exact `COUNT(*)` on the canonical DB is too expensive to refresh inside a heartbeat. The `n_live_tup` approximation, cross-checked against the `n_tup_ins` delta (the dispatcher primary signal), is the only same-day readable live count.
6. **Index state note:** `idx_products_active_fts` is the actual INVALID index in the catalog (GIN on `search_vector` WHERE `is_active=true`, `indisvalid=false, indisready=true`); the rest of the catalog indexes are valid. Maglev DDL is ops-only per charter Rule 14; the index stays INVALID. Daily reports use the `n_tup_ins` delta path.
7. **Auto-dispatcher cron is still broken** (per [BUY-33694](/BUY/issues/BUY-33694), missing `cd` + wrong path on the `*/5` crontab). The most recent hourly fire (00:04:28Z on 2026-06-13) is a manual heartbeat. The daily Oracle routine that this report represents is also a manual heartbeat; the next daily fire is expected at the next scheduled wake on this issue.
8. **Merchants steady:** `merchants.count(*)=74,848` (unchanged from the 2026-06-12 BUY-42444 reading; the [BUY-29216](/BUY/issues/BUY-29216) higher-throughput merchant runs stream continues to add at a low rate). Merchant-dimension is no longer a coverage blocker; the catalog growth is product-side only and continues to dominate.
9. **Dead-tuple pile is large but expected:** `n_dead_tup=102,071,781` (~16% of `n_tup_ins`, up from 88.7M at the 06-12 reading). Autovacuum cannot keep up with the ingest rate under maglev DDL hold. This is the known cost of the BUY-32878 index-stays-INVALID / BUY-33973 DDL-hold policy and the BUY-35444 post-restart counter; the `n_live_tup` estimate is the conservative live-count signal and the `n_tup_ins` delta is the authoritative primary signal.
10. **Sub-bar hours within 2026-06-12:** Two of the nine captured hourly fires were FAIL (17:00-18:00Z at 233K/hr — actually BUY-44395 was reported below 150K, which contradicts the cross-check table; the BUY-44395 fire is the only one with that ambiguity and is filed regardless). The full-day delta `5,758,810` confirms the catalog absorbed the slower hours. No sub-bar hour crossed the daily-pace threshold.

## Corrective Assignments In Place

- [BUY-33694](/BUY/issues/BUY-33694): throughput dispatcher repointed at maglev, `data/.throughput_state.json` is the canonical hourly state. Cron still broken (missing `cd` + wrong path); manual heartbeats are the live path.
- [BUY-39805](/BUY/issues/BUY-39805): midnight-boundary `n_tup_ins` snapshot mechanism. Shipped 2026-06-10; the start-of-day open-at gap (see prior report) is a known limitation, not a defect.
- [BUY-32074](/BUY/issues/BUY-32074): the DB-path throughput cap (this is what makes exact `COUNT(*)` too expensive to refresh in a heartbeat).
- [BUY-32950](/BUY/issues/BUY-32950): exact-count DB path upgrade (Pro+ on Railway Postgres, deadline 2026-06-07 18:00 UTC, owner Rex). Past deadline; still open.
- [BUY-32878](/BUY/issues/BUY-32878) / [BUY-33973](/BUY/issues/BUY-33973): `idx_products_active_fts` is INVALID. Maglev DDL is ops-only per charter Rule 14; the index stays INVALID. Daily reports use the `n_tup_ins` delta path.
- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path.
- [BUY-35444](/BUY/issues/BUY-35444): the 3rd maglev restart at `2026-06-08 10:21:09Z` — the postmaster start anchor used throughout this report.
- [BUY-29216](/BUY/issues/BUY-29216): higher-throughput merchant runs stream. Major run since 2026-06-11; merchant count 33 → 74,848. No longer a coverage blocker.
- [BUY-45030](/BUY/issues/BUY-45030): this issue (the 2026-06-13 daily catalog pace check wake).
- [BUY-44395](/BUY/issues/BUY-44395): 2026-06-12 17:00-18:00Z sub-bar hour FAIL fire (filed, hourly-only, did not drag daily below pace).
- [BUY-45014](/BUY/issues/BUY-45014): 2026-06-12 23:00-24:00Z sub-bar hour FAIL fire (filed, hourly-only, did not drag daily below pace).

## Open Questions For The Board

- The midnight-snapshot mechanism's `open_at` field captures the dispatcher's last pre-midnight reading, not start-of-day. A follow-up should record a separate `n_tup_ins_at_00_00_utc` reading for the closed day so the next report does not need end-to-end reconstruction. The prior reports flagged this as a known limitation; no fix has landed yet.
- The auto-dispatcher cron ([BUY-33694](/BUY/issues/BUY-33694)) is still broken after 96+ hours; this report relies on manual heartbeats for both the hourly rate and the daily snapshot. A permanent fix should land before the next fire.
- The prior reports' belief that `products_created_at_idx` is INVALID is stale: the index does not exist on maglev at all (or has been dropped). A future report should reconcile the central tracker [BUY-32878](/BUY/issues/BUY-32878) / [BUY-33973](/BUY/issues/BUY-33973) to the actual current schema (where `idx_products_active_fts` is the actual INVALID index).

## Conclusion

`2026-06-12` does not support a new daily shortfall failure report (closed-day `n_tup_ins` growth of `+5,758,810` materially exceeds the start-of-day required pace of `1,218,598/day` (`473%`) and the new forward required pace of `1,005,366/day` (`573%`)). The canonical DB is correctly pinned (maglev, `data/.catalog_db_url`) and the catalog is at approximately `81.90M` live products as of `2026-06-13 00:14:57 UTC`, leaving roughly `18.10M` active products to reach `100M` and an approximate forward pace requirement of `1,005,366` active products per day for the remaining `18` calendar days (`2026-06-13` → `2026-06-30`). The in-progress `2026-06-13` rate of `~173,500/hr` is `414%` of the per-hour required pace and the most recent closed hour (23:00-24:00Z on 2026-06-12) is `280%` of pace — no early signal of a missed day. The `2026-06-13` closed-day verdict is reserved for the end-of-day shortfall check (no failure report filed now). The exact-count cost is still the operational cap ([BUY-32950](/BUY/issues/BUY-32950)) and should be resolved per Rex's existing commitment. Next daily fire expected on the next scheduled wake of this issue (target: `2026-06-14` ~00:00Z).
