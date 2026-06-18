# Daily Product Target Shortfall Report

Date: 2026-05-31 UTC
Issue: BUY-27783
Owner: Oracle
Collected at: 2026-05-31 00:14:43 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is treated as the inclusive window from
`2026-05-31` through `2026-06-30`, which is `31` calendar days.

## Source of Truth

- Railway Postgres via `DATABASE_URL`
- Query time: `2026-05-31 00:14:43.319265 UTC`
- Metric note: this issue's rule is defined on `current_active_products`, which is different from the CEO report's broader `real products` total.
- Query used:

```sql
select
  now() at time zone 'utc' as collected_at_utc,
  count(*) filter (where is_active) as active_products,
  count(*) as real_products
from products;
```

## Daily Result

- Current active products: `2,752,385`
- Current real products: `2,767,644`
- Last confirmed active baseline before the `2026-05-30` UTC day: `2,752,385` as of `2026-05-30 00:14:35 UTC`
- Active-product growth observed across the fully covered `2026-05-30` UTC day: `0`
- Remaining active products to target: `97,247,615`
- Required products per day from `2026-05-31` forward: `3,137,020`
- Variance for the closed `2026-05-30` day versus the prior day's required pace (`3,038,988`): `-3,038,988`
- Opening variance for `2026-05-31` at the first live snapshot: `-3,137,020`

Clarification:

- The `15,259` difference between `real products` and `active products` is expected because the CEO report tracks all real catalog rows, while this shortfall rule explicitly tracks rows where `is_active = true`.
- Because the active count was unchanged from the `2026-05-30 00:14 UTC` baseline through `2026-05-31 00:14 UTC`, `2026-05-30` closed as a missed day on the source-of-truth metric.
- The `2026-05-31` variance is an opening snapshot rather than an end-of-day declaration, but it shows the required pace steepened again after another missed day.

## Why The Miss Happened

1. Active-product growth remained flat through the observed window from `2026-05-30 00:14:35 UTC` to `2026-05-31 00:14:43 UTC`.
2. The catalog growth path still depends on the ingestion-restart recovery chain documented in prior reporting: [BUY-22739](/BUY/issues/BUY-22739) and [BUY-24283](/BUY/issues/BUY-24283).
3. With no new active products landing, the remaining daily requirement increased from `3,038,988/day` to `3,137,020/day`.

## Idle Time Or Execution Gap

- No active-product growth is visible across a full source-of-truth day window.
- This reverts the prior day's small recovery and confirms the catalog engine did not sustain even minimal positive active-row throughput across `2026-05-30` UTC.
- The issue is therefore not a reporting variance. It is direct evidence that the catalog growth engine failed to add new active rows during the measured interval.

## Corrective Assignments In Place

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently gates recovery.

## Conclusion

`2026-05-30` closed as a target-shortfall day on the live source-of-truth metric. The active product count
remained at `2,752,385` from the last `2026-05-30` baseline through the first `2026-05-31` snapshot, leaving the
business at `0` active products added for the closed day versus a required pace of `3,038,988`, and raising the
new required run rate to `3,137,020` active products per day for the remaining `31` days through `2026-06-30`.
