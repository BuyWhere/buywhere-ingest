# Daily Product Target Shortfall Report

Date: 2026-05-29 UTC
Issue: BUY-25969
Owner: Oracle
Collected at: 2026-05-29 00:10:56 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is treated as the inclusive window from
`2026-05-29` through `2026-06-30`, which is `33` calendar days.

## Source of Truth

- Railway Postgres via `DATABASE_URL`
- Query time: `2026-05-29 00:10:56.432204 UTC`
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

- Current active products: `2,747,644`
- Current real products: `2,762,711`
- Last confirmed active baseline before the `2026-05-28` UTC day: `2,747,644` as of `2026-05-28 00:15:16 UTC`
- Active-product growth observed across the fully covered `2026-05-28` UTC day: `0`
- Remaining active products to target: `97,252,356`
- Required products per day from `2026-05-29` forward: `2,947,042`
- Variance for the closed `2026-05-28` day versus the prior day's required pace (`2,860,364`): `-2,860,364`
- Opening variance for `2026-05-29` at the first live snapshot: `-2,947,042`

Clarification:

- The `15,067` difference between `real products` and `active products` is expected because the CEO report tracks all real catalog rows, while this shortfall rule explicitly tracks rows where `is_active = true`.
- Because the active count was unchanged from the `2026-05-28 00:15 UTC` baseline through `2026-05-29 00:10 UTC`, `2026-05-28` closed as a missed day on the source-of-truth metric.
- The `2026-05-29` variance is an opening snapshot rather than an end-of-day declaration, but it shows the required pace has steepened again after another missed day.

## Why The Miss Happened

1. Active-product growth remained flat through the observed window from `2026-05-28 00:15:16 UTC` to `2026-05-29 00:10:56 UTC`.
2. The catalog growth path still depends on the ingestion-restart recovery chain documented in prior reporting: [BUY-22739](/BUY/issues/BUY-22739) and [BUY-24283](/BUY/issues/BUY-24283).
3. With no new active products landing, the remaining daily requirement increased from `2,860,364/day` to `2,947,042/day`.

## Idle Time Or Execution Gap

- No active-product growth is visible across a nearly `24` hour source-of-truth window.
- That makes the shortfall operationally stronger than a normal "below target" miss: the live active catalog was static across the entire day that just closed.
- The issue is therefore not a reporting variance. It is direct evidence that the catalog growth engine did not produce new active rows during the measured interval.

## Corrective Assignments In Place

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently gates recovery.

## Conclusion

`2026-05-28` closed as a target-shortfall day on the live source-of-truth metric. The active product count
remained at `2,747,644` from the last `2026-05-28` baseline through the first `2026-05-29` snapshot, leaving the
business at `0` active products added for the closed day versus a required pace of `2,860,364`, and raising the
new required run rate to `2,947,042` active products per day for the remaining `33` days through `2026-06-30`.
