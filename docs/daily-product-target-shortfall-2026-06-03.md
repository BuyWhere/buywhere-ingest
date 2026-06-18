# Daily Product Target Shortfall Report

Date: 2026-06-03 UTC
Issue: BUY-29316
Owner: Oracle
Collected at: 2026-06-03 00:11:41 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is treated as the inclusive window from
`2026-06-03` through `2026-06-30`, which is `28` calendar days.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url`
- URL used: `postgresql://buywhere_ingest@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- Query time: `2026-06-03 00:11:41.904567 UTC`
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
    timestamp '2026-06-02 00:00:00' as start_utc,
    timestamp '2026-06-03 00:00:00' as end_utc
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
- Active-product growth observed across the fully covered `2026-06-02` UTC day: `45`
- Remaining active products to target: `83,204,398`
- Required products per day from `2026-06-03` forward: `2,971,586`
- Variance for the closed `2026-06-02` day versus the prior day's required pace (`2,869,119`): `-2,869,074`
- Opening variance for `2026-06-03` at the first live snapshot: `-2,971,586`

Clarification:

- The `20,909` difference between `real products` and `active products` is expected because this shortfall rule tracks active rows only.
- This is no longer a full table freeze: the canonical DB shows `45` product creates and `45` updates during the closed `2026-06-02` UTC day.
- The problem is still a severe execution shortfall because `45` active products is effectively zero against a required `2,869,119` for the day that just closed.

## Why The Miss Happened

1. Catalog writes resumed on `2026-06-02`, but only at token throughput: `45` created active rows across the full UTC day.
2. The closed `2026-06-02` day therefore missed the required pace of `2,869,119` by `2,869,074` active products.
3. Because the business now has only `28` calendar days left after `2026-06-02`, the required pace steepened again to `2,971,586/day`.

## Idle Time Or Execution Gap

- This is not a reporting lag. The canonical source table itself shows the exact closed-day row activity.
- The catalog is no longer completely stalled, but the observed write rate is still operationally equivalent to zero relative to the target path.
- The execution gap changed shape from "no writes at all" to "writes resumed at negligible volume," which still leaves the goal path materially off track.

## Corrective Assignments In Place

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently gates recovery.

## Conclusion

`2026-06-02` closed as another target-shortfall day on the canonical BuyWhere catalog DB. The active product count
rose from `16,795,557` to `16,795,602`, which proves writes resumed, but only by `45` active products against a
required pace of `2,869,119`. That miss leaves `83,204,398` active products still needed and raises the required
run rate to `2,971,586` active products per day for the remaining `28` days through `2026-06-30`.
