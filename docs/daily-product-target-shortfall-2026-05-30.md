# Daily Product Target Shortfall Report

Date: 2026-05-30 UTC
Issue: BUY-27175
Owner: Oracle
Collected at: 2026-05-30 00:14:35 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is treated as the inclusive window from
`2026-05-30` through `2026-06-30`, which is `32` calendar days.

## Source of Truth

- Railway Postgres via `DATABASE_URL`
- Query time: `2026-05-30 00:14:35.865546 UTC`
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
- Last confirmed active baseline before the `2026-05-29` UTC day: `2,747,644` as of `2026-05-29 00:10:56 UTC`
- Active-product growth observed across the fully covered `2026-05-29` UTC day: `4,741`
- Remaining active products to target: `97,247,615`
- Required products per day from `2026-05-30` forward: `3,038,988`
- Variance for the closed `2026-05-29` day versus the prior day's required pace (`2,947,042`): `-2,942,301`
- Opening variance for `2026-05-30` at the first live snapshot: `-3,034,247`

Clarification:

- The `15,259` difference between `real products` and `active products` is expected because the CEO report tracks all real catalog rows, while this shortfall rule explicitly tracks rows where `is_active = true`.
- The active catalog did resume growth during the `2026-05-29` UTC day, but the observed `4,741` added rows were still far below the required `2,947,042` pace for that day.
- The `2026-05-30` variance is an opening snapshot rather than an end-of-day declaration, but it shows the required pace steepened again after another missed day.

## Why The Miss Happened

1. Throughput resumed, but only at `4,741` active products across the closed day versus a required pace in the millions.
2. The catalog growth path still depends on the ingestion-restart recovery chain documented in prior reporting: [BUY-22739](/BUY/issues/BUY-22739) and [BUY-24283](/BUY/issues/BUY-24283).
3. Because the growth recovered only marginally, the remaining daily requirement increased again from `2,947,042/day` to `3,038,988/day`.

## Idle Time Or Execution Gap

- This is no longer a zero-growth day; the source-of-truth metric shows `4,741` net active rows added across the fully covered `2026-05-29` UTC day.
- The operational miss remains severe because that recovery reached only about `0.16%` of the required daily pace (`4,741 / 2,947,042`).
- The issue is therefore not whether growth exists at all, but whether the current engine can sustain target-scale throughput. The answer from the live metric remains no.

## Corrective Assignments In Place

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently gates recovery.

## Conclusion

`2026-05-29` closed as a target-shortfall day on the live source-of-truth metric. The active product count
rose from `2,747,644` at the first `2026-05-29` snapshot to `2,752,385` at the first `2026-05-30` snapshot,
which means the business added `4,741` active products for the closed day versus a required pace of
`2,947,042`. That miss raised the required run rate again to `3,038,988` active products per day for the
remaining `32` days through `2026-06-30`.
