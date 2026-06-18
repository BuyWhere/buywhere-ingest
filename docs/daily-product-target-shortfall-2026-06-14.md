# Daily Product Target Shortfall Report

Date: 2026-06-14 UTC (daily report, ~18 minutes into the new day)
Issue: BUY-47533 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Oracle (3ec8f6dd)
Collected at: 2026-06-14 00:18:41 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-14` through `2026-06-30`, which is `17` calendar days.

A "missed day" is a closed UTC day whose active-product growth fell below the required
pace at the start of that day. Today's report covers:

- Closed-day `2026-06-13` verdict
- In-progress `2026-06-14` pulse (~18 minutes in)
- Forward required pace off the `2026-06-14 00:18:41Z` catalog reading

## Source Of Truth

- Canonical catalog Postgres via `data/.catalog_db_url`
- URL used: `postgresql://buywhere_ingest:...@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- DB target guard: `current_database()=railway` confirmed; harness `DATABASE_URL` was not used
- Live sample at `2026-06-14 00:18:41 UTC` from `pg_stat_user_tables.products`:

```sql
SELECT n_live_tup, n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup,
       pg_total_relation_size('products')
FROM pg_stat_user_tables
WHERE relname = 'products';
-- 85095847 | 53881695 | 125880572 | 4835 | 123322687 | 206047191040
```

- Cross-checks from the same heartbeat:
  - `pg_class.reltuples(products) = 77,343,112`
  - `merchants.count(*) = 74,848`
  - `pg_postmaster_start_time = 2026-06-08 10:21:09.112373+00`
- Current invalid `products` index from direct `pg_index` read: `idx_products_search_vector_ccnew` (`indisvalid=false`, `indisready=false`)

## Daily Result

**Closed-day `2026-06-13` reconstructed insert proof**

- Start-of-day anchor: `n_tup_ins = 50,656,943` at `2026-06-13T00:04:28+00:00`
  - Source: prior daily report [`docs/daily-product-target-shortfall-2026-06-13.md`](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-13.md)
- End-of-day anchor: `n_tup_ins = 53,881,693` at `2026-06-14T00:05:47.643299+00:00`
  - Source: current `data/.throughput_state.json` midnight-adjacent maglev reading
- Net inserts on closed-day `2026-06-13`: `53,881,693 - 50,656,943 = 3,224,750`
- Per-hour average for the closed day: `134,364.58/hr`
- Start-of-day required pace for `2026-06-13`: `1,005,366/day`
- Closed-day performance versus start-of-day required pace: `320.8%`

Conservative live-count lower bound:

- `n_live_tup` at `2026-06-13 00:14:57 UTC`: `81,903,410`
- `n_live_tup` at `2026-06-14 00:18:41 UTC`: `85,095,847`
- Lower-bound live growth across the closed day boundary: `+3,192,437`

**Closed-day `2026-06-13` verdict: NOT A MISS.**

The day averaged below the separate hourly failure threshold of `150,000/hr`, but the daily shortfall rule for this routine is whether the closed UTC day beat the required daily pace to `100M` by `2026-06-30`. It did so comfortably: `3,224,750` inserted rows is more than `3.2x` the required daily pace.

## Forward Pace (2026-06-14 Forward)

- Approximate current active products (`n_live_tup`): `85,095,847`
- Remaining active products to target: `14,904,153`
- Required products per day from `2026-06-14` forward: `876,715/day`
- Required products per hour from `2026-06-14` forward: `36,530/hr`

This is a further reduction from the prior published pace:

- `2026-06-13` report: `1,005,366/day`
- `2026-06-14` report: `876,715/day`
- Reduction day-over-day: `128,651/day` (`12.8%`)

## In-Progress Pulse (2026-06-14)

The first post-midnight samples show the new day started nearly flat:

- `n_tup_ins = 53,881,693` at `2026-06-14T00:05:47.643299+00:00`
- `n_tup_ins = 53,881,695` at `2026-06-14T00:18:41.390838+00:00`
- Delta: `+2` rows in `0.2149h`
- Instantaneous rate across that interval: `~9.3/hr`

That is far below the current required pace of `36,530/hr`, so there is an early-day stall signal. It is too early to classify `2026-06-14` as a missed day, but the first `13` minutes after the midnight-adjacent anchor were effectively flat.

## Conclusion

`2026-06-13` does **not** support a new daily shortfall failure report. The canonical maglev catalog grew by `+3,224,750` inserted rows across the closed UTC day, versus a required pace of `1,005,366/day`. As of `2026-06-14 00:18:41 UTC`, the catalog stands at approximately `85.10M` live products, leaving `14.90M` to reach `100M` by `2026-06-30`, which implies a new forward pace requirement of `876,715/day` (`36,530/hr`). The new day (`2026-06-14`) opened with an apparent stall (`+2` inserted rows across ~13 minutes), so the next hourly and daily checks need to confirm whether that flat start clears or becomes a real shortfall.
