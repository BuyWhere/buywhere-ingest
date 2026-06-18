# Daily Product Target Shortfall Report

Date: 2026-06-15 UTC (daily report, ~14 minutes into the new day)
Issue: BUY-50302 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Oracle (3ec8f6dd)
Collected at: 2026-06-15 00:14:07 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-15` through `2026-06-30`, which is `16` calendar days.

A "missed day" is a closed UTC day whose active-product growth fell below the required
pace at the start of that day. Today's report covers:

- Closed-day `2026-06-14` verdict
- In-progress `2026-06-15` pulse (~14 minutes in)
- Forward required pace off the `2026-06-15 00:14:07Z` catalog reading

## Source Of Truth

- Canonical catalog Postgres via `data/.catalog_db_url`
- URL used: `postgresql://buywhere_ingest:...@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- DB target guard: `current_database()=railway` confirmed; harness `DATABASE_URL` was not used
- Wrong-DB sanity check passed: live product proxy is `~89.03M`, not the stale `~2.7M` control-plane residue

Live catalog sample at `2026-06-15 00:14:07 UTC`:

```sql
SELECT now() AT TIME ZONE 'UTC',
       current_database(),
       pg_postmaster_start_time() AT TIME ZONE 'UTC',
       n_live_tup, n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup,
       pg_total_relation_size('public.products'),
       reltuples::bigint
FROM pg_stat_user_tables
JOIN pg_class ON pg_class.oid = 'public.products'::regclass
WHERE relname = 'products';
-- 2026-06-15 00:14:07.419123 | railway | 2026-06-08 10:21:09.112373
-- 89029378 | 57823798 | 153692260 | 4912 | 151142944 | 238490812416 | 77343112
```

Cross-checks from the same heartbeat:

- `merchants.count(*) = 74,848`
- Midnight-adjacent dispatcher state from `data/.throughput_state.json` at `2026-06-15T00:08:14.979873Z`:
  - `n_tup_ins = 57,823,398`
  - `n_live_tup = 89,028,978`
  - `last_db_host = maglev.proxy.rlwy.net:31310/railway`
- Invalid or not-ready `products` indexes still present:
  - `idx_products_deals_discount_pct`
  - `idx_products_deals_discount_pct_v2`
  - `idx_products_deals_discount_pct_v3`
  - `idx_products_deals_discount_pct_v5`
  - `idx_products_search_vector_ccnew`

## Daily Result

**Closed-day `2026-06-14` reconstructed insert proof**

- Start-of-day anchor: `n_tup_ins = 53,881,693` at `2026-06-14T00:05:47.643299+00:00`
  - Source: prior daily report [`docs/daily-product-target-shortfall-2026-06-14.md`](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-14.md)
- End-of-day anchor: `n_tup_ins = 57,823,398` at `2026-06-15T00:08:14.979873+00:00`
  - Source: current `data/.throughput_state.json` midnight-adjacent maglev reading
- Net inserts on closed-day `2026-06-14`: `57,823,398 - 53,881,693 = 3,941,705`
- Per-hour average for the closed day: `164,238/hr`
- Start-of-day required pace for `2026-06-14`: `876,715/day`
- Closed-day performance versus start-of-day required pace: `449.6%`

Conservative live-count lower bound:

- `n_live_tup` at `2026-06-14 00:18:41 UTC`: `85,095,847`
- `n_live_tup` at `2026-06-15 00:08:14 UTC`: `89,028,978`
- Lower-bound live growth across the closed day boundary: `+3,933,131`

**Closed-day `2026-06-14` verdict: NOT A MISS.**

The day beat the daily shortfall threshold comfortably. The canonical catalog added
`3,941,705` inserted rows across the closed UTC day against a required pace of
`876,715/day`, and even the conservative `n_live_tup` lower bound (`+3,933,131`)
is well above pace.

## Forward Pace (2026-06-15 Forward)

- Approximate current active products (`n_live_tup`): `89,029,378`
- Remaining active products to target: `10,970,622`
- Required products per day from `2026-06-15` forward: `685,664/day`
- Required products per hour from `2026-06-15` forward: `28,569/hr`

This is a further reduction from the prior published pace:

- `2026-06-14` report: `876,715/day`
- `2026-06-15` report: `685,664/day`
- Reduction day-over-day: `191,051/day` (`21.8%`)

## In-Progress Pulse (2026-06-15)

The first post-midnight samples show the new day opened far below the new required pace:

- `n_tup_ins = 57,823,398` at `2026-06-15T00:08:14.979873+00:00`
- `n_tup_ins = 57,823,798` at `2026-06-15T00:14:07.419123+00:00`
- Delta: `+400` rows in `5m52s`
- Instantaneous rate across that interval: `~4,091/hr`

That is only about `14.3%` of the current required pace of `28,569/hr`. It is too
early to classify `2026-06-15` as a missed day, but there is a clear early-day stall
signal and the next hourly checks should confirm whether throughput recovers.

## Conclusion

`2026-06-14` does **not** support a new daily shortfall failure report. The canonical
maglev catalog grew by `+3,941,705` inserted rows across the closed UTC day, versus a
required pace of `876,715/day`. As of `2026-06-15 00:14:07 UTC`, the catalog stands at
approximately `89.03M` live products, leaving `10.97M` to reach `100M` by `2026-06-30`,
which implies a new forward pace requirement of `685,664/day` (`28,569/hr`). The new day
opened slowly (`+400` inserted rows in `5m52s`, about `4,091/hr`), so the next hourly and
daily checks need to confirm whether that early stall clears or becomes a real shortfall.
