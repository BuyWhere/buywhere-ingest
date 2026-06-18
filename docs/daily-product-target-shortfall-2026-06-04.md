# Daily Product Target Shortfall Report

Date: 2026-06-04 UTC
Issue: BUY-29745
Owner: Oracle
Collected at: 2026-06-04 00:11:45 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is treated as the inclusive window from
`2026-06-04` through `2026-06-30`, which is `27` calendar days.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url`
- URL used: `postgresql://buywhere_ingest@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- Query time: `2026-06-04 00:11:45.666935 UTC`
- Metric note: this issue's rule is defined on `current_active_products`, which is different from the broader `real products` total.
- Guard note: older workspace shortfall artifacts dated before the `2026-05-31` DB-target correction used the wrong control-plane DB and are not valid baselines for this report.
- Primary query used:

```sql
select
  now() at time zone 'utc' as collected_at_utc,
  count(*) filter (where is_active) as active_products,
  count(*) as real_products
from products;
```

- Mutation check used:

```sql
select
  min(created_at) at time zone 'utc',
  max(created_at) at time zone 'utc',
  min(updated_at) at time zone 'utc',
  max(updated_at) at time zone 'utc'
from products;
```

- Closed-day activity check used:

```sql
with bounds as (
  select
    timestamp '2026-06-03 00:00:00' as start_utc,
    timestamp '2026-06-04 00:00:00' as end_utc
)
select
  count(*) filter (where created_at >= start_utc and created_at < end_utc) as created_rows,
  count(*) filter (where updated_at >= start_utc and updated_at < end_utc) as updated_rows,
  count(*) filter (where is_active and created_at >= start_utc and created_at < end_utc) as created_active_rows
from products, bounds;
```

## Daily Result

- Current active products: `16,795,602`
- Current real products: `16,816,511`
- Last observable catalog create on the canonical DB: `2026-06-02 22:07:29.561025 UTC`
- Last observable catalog update on the canonical DB: `2026-06-02 22:12:08.293022 UTC`
- Active-product growth observed across the fully covered `2026-06-03` UTC day: `0`
- Remaining active products to target: `83,204,398`
- Required products per day from `2026-06-04` forward: `3,081,645`
- Variance for the closed `2026-06-03` day versus the prior day's required pace (`2,971,586`): `-2,971,586`
- Opening variance for `2026-06-04` at the first live snapshot: `-3,081,645`

Clarification:

- The `20,909` difference between `real products` and `active products` is expected because this shortfall rule tracks active rows only.
- This is again a full table freeze across the closed `2026-06-03` UTC day: the canonical DB shows `0` product creates and `0` updates in that window.
- Because the latest observed create/update timestamps are still on `2026-06-02`, this miss is not just below pace; it reflects a resumed stall after the brief `45` row movement seen on `2026-06-02`.

## Why The Miss Happened

1. The canonical catalog showed no new creates and no updates during the fully closed `2026-06-03` UTC day.
2. That means the brief activity seen on `2026-06-02` did not continue into `2026-06-03`; effective catalog growth returned to zero.
3. With only `27` calendar days remaining after `2026-06-03`, the required daily pace steepened again to `3,081,645/day`.

## Idle Time Or Execution Gap

- This is not a reporting lag. The canonical source table itself shows zero closed-day row activity.
- The last observable write timestamps predate the entire closed day being measured, so the execution gap is a real catalog-write stoppage.
- The goal path is now materially worse than yesterday because the same `83,204,398` active-product gap must be closed in one fewer day.

## Corrective Assignments In Place

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently gates recovery.

## Conclusion

`2026-06-03` closed as another target-shortfall day on the canonical BuyWhere catalog DB. The active product count
stayed flat at `16,795,602`, with `0` creates and `0` updates observed across the closed UTC day. That leaves
`83,204,398` active products still needed and raises the required run rate to `3,081,645` active products per day
for the remaining `27` days through `2026-06-30`.
