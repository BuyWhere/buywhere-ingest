# Daily Product Target Shortfall Report

Date: 2026-06-16 UTC (daily report, ~15 minutes into the new day)
Issue: BUY-52124 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Oracle (3ec8f6dd)
Collected at: 2026-06-16 00:15:16 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-16` through `2026-06-30`, which is `15` calendar days.

A "missed day" is a closed UTC day whose active-product growth fell below the required
pace at the start of that day. Today's report covers:

- Closed-day `2026-06-15` verdict
- Forward required pace off the `2026-06-16 00:15:16Z` catalog reading
- Why the closed-day proof uses `n_live_tup` instead of a full-day `n_tup_ins` delta

## Source Of Truth

- Canonical catalog Postgres via `data/.catalog_db_url`
- URL used: `postgresql://buywhere_ingest:...@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- DB target guard: `current_database()=railway` confirmed; harness `DATABASE_URL` was not used
- Wrong-DB sanity check passed: live product proxy is `~95.24M`, not the stale `~2.7M` control-plane residue

Live catalog sample at `2026-06-16 00:15:16 UTC`:

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
-- 2026-06-16 00:15:16.452303 | railway | 2026-06-15 09:56:28.874687
-- 95240314 | 4204829 | 33975326 | 17 | 3053607 | 252962267136 | 95175744
```

Cross-checks from the same heartbeat:

- `merchants.count(*) = 75,046`
- Invalid or not-ready `products` indexes still present:
  - `idx_products_deals_discount_pct`
  - `idx_products_deals_discount_pct_v2`
  - `idx_products_deals_discount_pct_v3`
  - `idx_products_deals_discount_pct_v5`
  - `idx_products_search_vector_ccnew`

## Daily Result

**Closed-day `2026-06-15` conservative growth proof**

- Start-of-day live anchor: `n_live_tup = 89,029,378` at `2026-06-15T00:14:07.419123+00:00`
  - Source: prior daily report [`docs/daily-product-target-shortfall-2026-06-15.md`](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-15.md)
- End-of-day live anchor: `n_live_tup = 95,240,314` at `2026-06-16T00:15:16.452303+00:00`
  - Source: current maglev sample
- Conservative live growth across closed-day `2026-06-15`: `95,240,314 - 89,029,378 = 6,210,936`
- Lower-bound average across the closed day: `258,789/hr`
- Start-of-day required pace for `2026-06-15`: `685,664/day`
- Closed-day performance versus start-of-day required pace: `905.8%`

**Closed-day `2026-06-15` verdict: NOT A MISS.**

The day beat the daily shortfall threshold by a wide margin. Even the conservative
live-count lower bound shows `+6,210,936` active products across the closed UTC day,
which is more than `9x` the required pace published at the start of `2026-06-15`.

## Why `n_tup_ins` Is Not The Primary Closed-Day Proof Today

Maglev restarted during the closed day:

- `pg_postmaster_start_time = 2026-06-15 09:56:28.874687+00`

That restart reset the `pg_stat_user_tables.n_tup_ins` counter inside the `2026-06-15`
window, so an end-to-end `n_tup_ins` delta would undercount the day. The previous daily
report's midnight-adjacent anchor showed:

- `n_tup_ins = 57,823,798` at `2026-06-15T00:14:07.419123+00:00`

while the current post-restart sample shows:

- `n_tup_ins = 4,204,829` at `2026-06-16T00:15:16.452303+00:00`

Because the counter reset mid-day, today's closed-day verdict relies on `n_live_tup`
as the conservative signal and states that limitation explicitly.

## Forward Pace (2026-06-16 Forward)

- Approximate current active products (`n_live_tup`): `95,240,314`
- Remaining active products to target: `4,759,686`
- Required products per day from `2026-06-16` forward: `317,313/day`
- Required products per hour from `2026-06-16` forward: `13,221/hr`

This is a further reduction from the prior published pace:

- `2026-06-15` report: `685,664/day`
- `2026-06-16` report: `317,313/day`
- Reduction day-over-day: `368,351/day` (`53.7%`)

## Conclusion

`2026-06-15` does **not** support a new daily shortfall failure report. The canonical
maglev catalog grew by at least `+6,210,936` active products across the closed UTC day,
versus a required pace of `685,664/day`. As of `2026-06-16 00:15:16 UTC`, the catalog
stands at approximately `95.24M` live products, leaving `4.76M` to reach `100M` by
`2026-06-30`, which implies a new forward pace requirement of `317,313/day`
(`13,221/hr`). The only material nuance is the `2026-06-15 09:56:28 UTC` maglev restart,
which reset `n_tup_ins` mid-day and forced today's closed-day proof onto the conservative
`n_live_tup` path instead of the usual full-day `n_tup_ins` delta.
