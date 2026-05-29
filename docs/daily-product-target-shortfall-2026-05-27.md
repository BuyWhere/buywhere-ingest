# Daily Product Target Shortfall Report

Date: 2026-05-27 UTC
Issue: BUY-24561
Owner: Oracle
Collected at: 2026-05-27 07:13:54 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is treated as the inclusive window from
`2026-05-27` through `2026-06-30`, which is `35` calendar days. If the team instead measures from the
end of `2026-05-27`, the requirement becomes even steeper, so this report uses the less severe
same-day interpretation.

## Source of Truth

- Railway Postgres via `DATABASE_URL`
- Query time: `2026-05-27 07:13:54 UTC`
- Metric note: this issue's rule is defined on `current_active_products`, which is different from the CEO report's broader `real products` total.
- Query used:

```sql
select count(*) filter (where is_active) as active_products
from products;
```

## Daily Result

- Current active products: `2,747,644`
- Current real products (CEO report row): `2,762,711`
- Prior active products baseline: `2,747,644` as of `2026-05-26 14:06:16 UTC`
- Remaining active products to target: `97,252,356`
- Required products for `2026-05-27`: `2,778,639`
- Actual active products added so far on `2026-05-27`: `0`
- Variance versus required pace: `-2,778,639`

Clarification:

- The `14,067` difference between `real products` and `active products` is expected because the CEO report tracks all real catalog rows, while this shortfall rule explicitly tracks rows where `is_active = true`.
- The miss still stands under either interpretation: active growth is `0` versus a required `2,778,639`, and the broader real-product total remains far below the June 30 target path as well.

## Why The Miss Happened

1. Active-product growth is currently flat versus the prior dated DB snapshot. No same-day catalog expansion is visible in the source-of-truth count.
2. The catalog growth path remains structurally gated by the ingestion-restart chain [BUY-22739](/BUY/issues/BUY-22739) and terminal blocker [BUY-24283](/BUY/issues/BUY-24283).
3. Because the ingestion hold is still unresolved, the system is not producing the multi-million-per-day growth required to stay on the June 30 path.

## Idle Time Or Execution Gap

- Between `2026-05-26 14:06:16 UTC` and `2026-05-27 07:13:54 UTC`, the active-product count remained at `2,747,644`.
- That means the observable execution gap is not just "below target"; it is a full zero-growth interval across the latest measured window.
- The standing blocker state indicates the missing work is not reporting-only. The growth engine itself is still gated before fresh ingest can land into the live active catalog.

## Corrective Assignments In Place For The Next Day

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently terminally blocks recovery.

## Conclusion

`2026-05-27` is already a target-shortfall day on the live data currently available. Even under the inclusive
35-day interpretation, the business needed `2,778,639` active products added today and has produced `0`
so far in the latest source-of-truth snapshot.
