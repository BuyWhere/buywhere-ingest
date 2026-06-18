# Daily Product Target Shortfall Report

Date: 2026-06-02 UTC
Issue: BUY-28795
Owner: Oracle
Collected at: 2026-06-02 00:11:55 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is treated as the inclusive window from
`2026-06-02` through `2026-06-30`, which is `29` calendar days.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url`
- URL used: `postgresql://buywhere_ingest@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- Query time: `2026-06-02 00:11:55.394568 UTC`
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

## Daily Result

- Current active products: `16,795,557`
- Current real products: `16,816,466`
- Last observable catalog mutation on the canonical DB: `2026-05-29 06:26:05.894316 UTC`
- Active-product growth observed across the fully covered `2026-06-01` UTC day: `0`
- Remaining active products to target: `83,204,443`
- Required products per day from `2026-06-02` forward: `2,869,119`
- Variance for the closed `2026-06-01` day versus the prior day's required pace (`2,773,482`): `-2,773,482`
- Opening variance for `2026-06-02` at the first live snapshot: `-2,869,119`

Clarification:

- The `20,909` difference between `real products` and `active products` is expected because this shortfall rule tracks active rows only.
- Because the source table shows no product-row creates or updates after `2026-05-29 06:26:05 UTC`, the active count was frozen for the entire closed `2026-06-01` UTC day.
- The `2026-06-02` variance is an opening snapshot rather than an end-of-day declaration, but it shows the required pace steepened again after another zero-growth day.

## Why The Miss Happened

1. The canonical catalog DB shows a frozen `products` table, with no product-row creates or updates after `2026-05-29 06:26:05 UTC`.
2. That means `2026-06-01` closed with `0` active products added against a required pace of `2,773,482`.
3. With the catalog frozen again, the remaining daily requirement increased to `2,869,119/day` for the final `29` calendar days through `2026-06-30`.

## Idle Time Or Execution Gap

- This is not a metric-collection lag. It is a direct source-table freeze on the canonical catalog DB.
- The live source-of-truth table shows no row churn at all across the closed day, so the gap is execution throughput, not reporting ambiguity.
- Because the last observable mutation predates `2026-05-30`, the business has now carried multiple consecutive zero-throughput UTC days into June.

## Corrective Assignments In Place

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently gates recovery.

## Conclusion

`2026-06-01` closed as a target-shortfall day on the canonical BuyWhere catalog DB. The active product count
remained at `16,795,557` through the first `2026-06-02` snapshot, leaving the business at `0` active products
added for the closed day versus a required pace of `2,773,482`, and raising the new required run rate to
`2,869,119` active products per day for the remaining `29` days through `2026-06-30`.
