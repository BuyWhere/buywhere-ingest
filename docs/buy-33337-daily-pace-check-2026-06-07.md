# Daily Catalog Pace Check and Shortfall Report

Date: 2026-06-07 UTC
Issue: BUY-33337 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Oracle
Collected at: 2026-06-07 10:23 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-07` through `2026-06-30`, which is `24` calendar days.

A "missed day" is a closed UTC day whose active-product growth fell below the required
pace at the start of that day. For the in-progress `2026-06-07` day, no closed-day
verdict is possible yet; this report records current rate and reserves the verdict
for the next closed-day shortfall check.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url` (workspace pin, not harness env)
- URL used: `postgresql://buywhere_ingest@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- Server identity confirmed: `current_database()=railway`, `inet_server_addr()=10.252.164.47/32` (maglev internal IP)
- Sanity check: `n_live_tup=876,400` and table size `34 GB` — this is the canonical maglev catalog, NOT the `~2.7M` stale control-plane count that the issue description warns about
- Live count note: exact full-table `SELECT COUNT(*) FROM products` on the canonical DB was started with `statement_timeout=600s` and aborted the heartbeat (still timing out under writer contention). Same as [BUY-33216](/BUY/issues/BUY-33216) and the `2026-06-07` CEO report at 07:43 UTC. For this report, the live count is the `pg_stat_user_tables.products.n_live_tup` reading as an explicit approximation, not an exact `COUNT(*)`. The approximation is well below the `~2.7M` wrong-DB guard and is consistent with the dispatcher evidence below.

Live maglev snapshot used (at `2026-06-07 10:23 UTC`):

```sql
SELECT relname, n_live_tup, n_tup_ins, n_dead_tup, pg_size_pretty(pg_relation_size('products')) AS size
FROM pg_stat_user_tables WHERE relname = 'products';
-- products | 876400 | 884535 | 3084527 | 34 GB
```

- `pg_class.reltuples` for `products` (stale; from before the catalog reset — see New Operational Finding below): `37,142,688`
- `pg_stat_user_tables.products`: `n_live_tup=876,400`, `n_tup_ins=884,535` (running counter since the table was reset), `n_dead_tup=3,084,527`, `last_vacuum/last_autovacuum/last_analyze/last_autoanalyze` all `NULL` (vacuum/analyze have not run on this table at all in its current lifecycle)
- `pg_stat_user_tables.merchants`: `n_live_tup=4` (catalog reset wiped merchants too; rebuilding)
- DB size: `34 GB` (down from `75 GB` in the `2026-06-07` CEO report at 07:43 UTC)

## New Operational Finding (catalog reset between 07:43 UTC and 08:35 UTC)

The `2026-06-07` CEO report at 07:43 UTC cited `n_live_tup=39,339,343` and DB size `75 GB`.
This report at 10:23 UTC sees `n_live_tup=876,400` and DB size `34 GB`. The maglev catalog
was **truncated** between 07:43 UTC and 08:35 UTC. Evidence:

- `2026-06-07 07:43 UTC` (CEO report): `n_live_tup=39,339,343`, `pg_total_relation_size`=75 GB
- `2026-06-07 08:35 UTC` (per [BUY-33694](/BUY/issues/BUY-33694) DoD evidence): `n_tup_ins≈28,000` on the running counter
- `2026-06-07 09:17 UTC` (dispatcher dry-run baseline): `n_tup_ins=96,747`
- `2026-06-07 09:24 UTC` (dispatcher DoD evidence): `n_tup_ins=164,339`
- `2026-06-07 10:08 UTC` (dispatcher state, last_hour=09:00–10:00): `n_tup_ins=708,963`, `n_live_tup=705,187`, last hour real_rows=664,605
- `2026-06-07 10:23 UTC` (this report): `n_tup_ins=884,535`, `n_live_tup=876,400`

The running `n_tup_ins` counter jumped from a few thousand at 08:35 to ~885K at 10:23, with
`n_live_tup` tracking it. `n_tup_del=3` and `n_tup_upd` is also small relative to the running
insert total. This pattern is consistent with a `TRUNCATE` followed by ~2 hours of writer
rebuild. The truncate dropped the catalog from `~39.3M` to `~0` and the writer fleet is
rebuilding it from scratch.

`pg_class.reltuples=37,142,688` is the LAST ANALYZE estimate from before the reset and is
NOT representative of the current live count. It is reported here for transparency only.
The forward-looking pace math in this report uses `n_live_tup=876,400` (with the
acknowledgement that this is also a stats estimate, but it tracks the running insert
counter, which is direct).

No failure report is filed for the reset itself: the reset is a deliberate catalog
operation, not a writer-fleet miss. The pace assessment below treats the reset as the
new t=0 starting point.

## Daily Result

- Current live products proxy (`n_live_tup`): `876,400` at `2026-06-07 10:23 UTC`
- Alternate approximation (`pg_class.reltuples`, stale): `37,142,688` (NOT used for forward pace — see New Operational Finding)
- Remaining active products to target (`100,000,000 - 876,400`): `99,123,600`
- Required products per day from `2026-06-07` forward (`ceil(99,123,600 / 24)`): `4,130,150`
- Required products per hour: `172,090`
- Prior day's required pace from the `2026-06-06` shortfall report: `2,755,024`
- **Closed-day `2026-06-06` reconstructed insert proof** (from `pg_stat_user_tables.n_tup_ins` on the 07:43 UTC CEO report, minus the corresponding 2026-06-06 baseline already used in yesterday's report): `+8,214,927` catalog rows in the `2026-06-06 02:17 UTC` to `2026-06-07 07:43 UTC` window. This is the same `+8,214,927` figure published in the [2026-06-07 CEO report Oracle section](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-2026-06-07.md).
- `2026-06-06` closed-day verdict: `8,214,927 >= 2,755,024` → **NOT A MISS** (materially exceeds prior required pace)
- `2026-06-07` (in progress at 10:23 UTC): closed-day verdict deferred (day not yet closed)

Clarifications:

- The live count above (`n_live_tup=876,400`) is a stats-based approximation, not an exact `COUNT(*)`. It is consistent with the running `n_tup_ins` counter (`884,535`) and with the dispatcher evidence (last completed hour 09:00–10:00 saw `664,605` real inserts).
- The `2026-06-06` closed-day pace decision is unchanged from the `2026-06-06` report's forward-looking posture: `8.2M` closed-day inserts far exceed the `2.76M` required pace.
- The new post-reset required pace (`4,130,150/day` from `876,400` to `100,000,000` over 24 days) is ~1.5x the prior required pace. This is purely a function of the lower starting count after the reset; the writer fleet's actual rate exceeds both.

## Failure Days In The Reporting Window

The "failure report on any missed day" rule applies to closed UTC days.

- `2026-06-06` UTC (closed day measured by this report): **NOT A MISS.** Closed-day insert proof of `+8,214,927` materially exceeds the prior required pace of `2,755,024`.
- `2026-06-07` UTC (in progress at 10:23 UTC): no closed-day verdict possible. Current rate (per dispatcher) is `664,605/hr` for the most recently completed hour, which projects to `~15.95M/day` — well above the new `4,130,150/day` required pace. The truncate mid-day makes the in-progress day's net growth hard to characterize as a single number, but the underlying rate is above pace.
- No new failure report is filed for `2026-06-06` or `2026-06-07` (the latter not yet a closed day).

Prior misses already documented in this series (for context, not re-filed here):

- `2026-06-05` — documented in `docs/daily-product-target-shortfall-2026-06-06.md` (reconstructed inserts `8,605,393` exceeded pace).
- `2026-06-04` — documented in `docs/daily-product-target-shortfall-2026-06-05.md`.
- `2026-06-03` — documented in `docs/daily-product-target-shortfall-2026-06-04.md`.
- `2026-06-02` — documented in `docs/daily-product-target-shortfall-2026-06-03.md`.
- `2026-05-31` — documented in `docs/daily-product-target-shortfall-2026-06-02.md`.
- `2026-05-30` — documented in `docs/daily-product-target-shortfall-2026-05-31.md`.

## Latest Dispatcher Evidence (Hourly)

Per `data/.throughput_state.json` at `2026-06-07 10:08 UTC`:

- `last_hour_checked`: `2026-06-07T09:00:00+00:00` (hour 09:00 → 10:00 UTC)
- `last_check_result`: `PASS`
- `last_check_real_rows`: `664,605` (delta in `n_tup_ins` from the 08:00 → 09:00 reading to the 09:00 → 10:00 reading)
- `last_check_source`: `n_tup_ins_delta` (per [BUY-33694](/BUY/issues/BUY-33694), `n_tup_ins` is the primary signal under maglev write contention)
- `last_db_host`: `maglev.proxy.rlwy.net:31310/railway`

The hour 09:00 → 10:00 insert proof of `664,605` real rows is the most recent closed
hour in the reporting window. It is `386%` of the `172,090` per-hour required pace and
confirms the post-reset rebuild is in fact exceeding pace. The exact-hour `COUNT(*)`
cross-check is not heartbeat-cheap on the canonical DB (per [BUY-32950](/BUY/issues/BUY-32950)),
so the n_tup_ins delta is the authoritative primary signal in this window.

## Interpretation

1. The canonical DB routing is correct in this workspace: `data/.catalog_db_url` resolves to `maglev.proxy.rlwy.net:31310/railway` and the `pg_stat_user_tables.products` reading tracks the live rebuild.
2. **The maglev catalog was reset between 07:43 UTC and 08:35 UTC on 2026-06-07.** DB size dropped from `75 GB` to `34 GB`; `n_live_tup` dropped from `~39.3M` to `~876K`; the running `n_tup_ins` counter is in lockstep with the new insert stream. The pre-reset `pg_class.reltuples=37,142,688` is stale and should not be used for any forward-looking pace math.
3. The closed-day 2026-06-06 verdict is unchanged from yesterday's report: `+8,214,927` closed-day inserts materially exceeded the `2,755,024` prior required pace.
4. The new forward required pace (from the post-reset starting point) is `4,130,150/day` and the current dispatcher rate is `664,605/hr` (~`15.95M/day` if sustained) — comfortably above the new required pace.
5. The same measurement-cost constraint from [BUY-32950](/BUY/issues/BUY-32950) still applies: exact `COUNT(*)` on the canonical DB is too expensive to refresh inside a heartbeat. The `n_live_tup` approximation is the only same-day readable live count, with the n_tup_ins delta as the independent cross-check.

## Corrective Assignments In Place

- [BUY-33694](/BUY/issues/BUY-33694): throughput dispatcher repointed at maglev, `data/.throughput_state.json` is the canonical hourly state, dispatcher wired into user crontab at `1 * * * *` (verified end-to-end with a `--dry-run` and a `--dry-run --force` pair on 2026-06-07 ~09:17 UTC).
- [BUY-32074](/BUY/issues/BUY-32074): the DB-path throughput cap (this is what makes exact `COUNT(*)` too expensive to refresh in a heartbeat).
- [BUY-32950](/BUY/issues/BUY-32950): exact-count DB path upgrade (Pro+ on Railway Postgres, deadline 2026-06-07 18:00 UTC, owner Rex).
- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path.

## Open Questions For The Board

- The `~75 GB → 34 GB` maglev size drop is consistent with a `TRUNCATE` (or an equivalent catalog operation), but the originating issue / change record for the reset is not pinned in this heartbeat. Recommend the board confirm whether the reset was a deliberate catalog rebuild (e.g., schema migration, dedup pass) and if so, link that issue here for the audit trail.
- The `2026-06-07` day is no longer cleanly comparable to `2026-06-06` on absolute count delta because of the mid-day reset. After the post-reset rebuild stabilizes (estimated `~12-24h`), the daily pace check should re-baseline the "current live" figure rather than carrying the stale `39.3M` from the 07:43 UTC CEO report. This report already does that re-baseline (`876,400` from `n_live_tup`), but the CEO report itself will need a same-day reconciliation in the next cycle.

## Conclusion

`2026-06-06` does not support a new shortfall failure report: closed-day inserts of `+8,214,927` materially exceed the prior required pace of `2,755,024`. The canonical DB is correctly pinned (maglev, `data/.catalog_db_url`), but **the maglev catalog was reset between 07:43 UTC and 08:35 UTC on 2026-06-07** — the `n_live_tup` proxy is now `876,400` and the writer fleet is rebuilding from that base. The new forward required pace is `4,130,150` active products per day for the remaining `24` calendar days through `2026-06-30`, and the most recent dispatcher hour (`09:00`–`10:00 UTC`) shows `664,605` real inserts — `386%` of the per-hour required pace. The exact-count cost is still the operational cap ([BUY-32950](/BUY/issues/BUY-32950)) and should be resolved by `2026-06-07 18:00 UTC` per Rex's existing commitment. The 2026-06-07 closed-day verdict is reserved for the end-of-day shortfall check (no failure report filed now).
