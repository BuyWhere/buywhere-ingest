# Daily Product Target Shortfall Report

Date: 2026-06-05 UTC
Issue: BUY-30601
Owner: Oracle
Collected at: 2026-06-05 00:59:26 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-05` through `2026-06-30`, which is `26` calendar days.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url`
- URL used: `postgresql://buywhere_ingest@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- Catalog target sanity (`scripts/catalog_target_report.py`): `active_database_host = maglev.proxy.rlwy.net:31310/railway`, `surfaces_diverge = true` (control-plane DB correctly NOT in use)
- Query time: `2026-06-05 00:59:26.812224 UTC`
- Metric note: this issue's rule is defined on `current_active_products`; the raw row count is reported alongside for transparency.
- Guard note: older workspace shortfall artifacts dated before the `2026-05-31` DB-target correction used the wrong control-plane DB and are not valid baselines for this report.
- Primary query used:

```sql
select
  now() at time zone 'utc' as collected_at_utc,
  count(*) filter (where is_active) as active_products,
  count(*) as real_products,
  min(created_at) at time zone 'utc' as min_created,
  max(created_at) at time zone 'utc' as max_created,
  min(updated_at) at time zone 'utc' as min_updated,
  max(updated_at) at time zone 'utc' as max_updated
from public.products;
```

- Closed-day activity check used (the closed UTC day measured by this report is `2026-06-04`):

```sql
with bounds as (
  select
    timestamp '2026-06-04 00:00:00' as start_utc,
    timestamp '2026-06-05 00:00:00' as end_utc
)
select
  count(*) filter (where created_at >= start_utc and created_at < end_utc) as created_rows,
  count(*) filter (where updated_at >= start_utc and updated_at < end_utc) as updated_rows,
  count(*) filter (where is_active and created_at >= start_utc and created_at < end_utc) as created_active_rows
from public.products, bounds;
```

## Daily Result

- Current active products: `22,591,103`
- Current real products: `22,645,613`
- Last observable catalog create on the canonical DB: `2026-06-05 00:57:41.337539 UTC`
- Last observable catalog update on the canonical DB: `2026-06-05 00:57:41.337539 UTC`
- Closed-day (`2026-06-04` UTC) activity:
  - Created rows: `5,226,474`
  - Created-and-active rows: `5,192,873`
  - Updated rows: `3,771,144`
  - Distinct sources contributing creates: `100`
  - Distinct merchants contributing creates: `16,217`
- Remaining active products to target: `77,408,897`
- Required products per day from `2026-06-05` forward: `2,977,266`
- Variance for the closed `2026-06-04` day vs. prior day's required pace (`3,081,645`): `+2,111,228`
- Opening variance for `2026-06-05` at the first live snapshot: this report — `207,896` active rows already created in the open `2026-06-05` UTC partial day; live snapshot vs. today's required pace (`2,977,266`) tracking at `-2,769,370` as of `00:59:26 UTC` (≈4% of UTC day elapsed)

Clarification:

- The `54,510` difference between `real products` and `active products` is expected because this shortfall rule tracks `is_active` rows only; tombstoned/out-of-stock rows still count toward `real products`.
- This is a beat day, not a miss: the canonical DB shows the closed `2026-06-04` UTC day cleared `5,192,873` created-and-active rows against a required pace of `3,081,645` — a `+2,111,228` over-pace.
- The over-pace pulled the gap from `83,204,398` (yesterday's reported gap) down to `77,408,897`, lowering the required daily run rate from `3,081,645/day` to `2,977,266/day`.
- Latest observable create/update timestamps are at `2026-06-05 00:57:41 UTC`, well after the most recent closed day, confirming this is a live writer, not a frozen one.

## Why The Closed Day Cleared Pace

1. The canonical catalog received `5,226,474` row creates and `3,771,144` row updates across the `2026-06-04` UTC day.
2. Inserts were broad-based: `100` distinct sources and `16,217` distinct merchants contributed creates on that day, consistent with a multi-merchant ingest sweep rather than a single bulk dump.
3. With `5,192,873` of those creates landing as `is_active`, the day cleared the required `3,081,645` pace and reduced the remaining gap by `+2,111,228` net.

## Idle Time Or Execution Gap

- No closed-day execution gap on `2026-06-04`. The day's row activity is broad and large, and writes have continued into `2026-06-05`.
- However, the rolling history is still uneven: in the last 14 UTC days, four days (`2026-05-30`, `2026-05-31`, `2026-06-01`, `2026-06-03`) showed `0` created rows on the canonical DB, and three other days (`2026-05-24`, `2026-05-27`, `2026-05-28`) cleared only double- or triple-digit creates. The pace surplus from `2026-06-04` does not eliminate the structural risk that ingest can stall for multiple consecutive days at a time.
- Required daily pace is now `2,977,266/day` for `26` consecutive days. A single missed day reintroduces meaningful re-acceleration risk.

## Failure Days In The Reporting Window

The "failure report on any missed day" rule applies to closed UTC days where the active-product growth fell below the required pace at the start of that day.

- `2026-06-04` UTC (closed day measured by this report): **NOT A MISS** — `5,192,873` created-active rows vs. `3,081,645` required.
- No new failure report is filed for `2026-06-04`.

Prior misses already documented in this series (for context, not re-filed here):

- `2026-06-03` — documented in `docs/daily-product-target-shortfall-2026-06-04.md`.
- `2026-06-02` — documented in `docs/daily-product-target-shortfall-2026-06-03.md`.
- `2026-05-31` — documented in `docs/daily-product-target-shortfall-2026-06-02.md`.
- `2026-05-30` — documented in `docs/daily-product-target-shortfall-2026-05-31.md`.

## Corrective Assignments In Place

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently gated recovery (clearly progressed on `2026-06-04`).

## Conclusion

`2026-06-04` closed as a beat day on the canonical BuyWhere catalog DB. Active products grew to
`22,591,103`, leaving a `77,408,897` gap to the `100M` target and a forward required run rate of
`2,977,266` active products per day for the `26` calendar days remaining through `2026-06-30`. No
new daily-failure report is filed for `2026-06-04`. The structural risk surfaced by the rolling
14-day history — frequent zero-create days — remains the dominant pace risk; sustaining the
`2026-06-04`-style sweep across at least the next `26` days is what closes the target.
