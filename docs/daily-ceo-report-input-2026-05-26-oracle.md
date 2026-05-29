# Daily CEO Report Input

Date: 2026-05-26
Issue: BUY-24310
Owner: Oracle
Workspace: Paperclip issue checkout `_default`

## Required KPI values (queried 2026-05-26 ~23:20 UTC)

Reporting windows used:

- Month to date: `2026-05-01 00:00:00 UTC` through query time on `2026-05-26 UTC`
- Same-day spot check: `2026-05-26 00:00:00 UTC` through query time on `2026-05-26 UTC`

1) Exact merchant count
- Value: `15,070` distinct merchant ids represented in `public.products`
- Supporting breakdown:
  - `15,006` product-backed merchant ids also exist in `public.merchants`
  - `64` product-backed merchant ids currently have no matching `public.merchants` row
  - `64,856` total rows exist in `public.merchants`, but that registry total materially exceeds the live catalog-backed merchant footprint
- Method: production Postgres aggregate over `public.products.merchant_id`, reconciled against `public.merchants`
- Calculation note: for the CEO report, the defensible "exact merchant count" is the live catalog-backed distinct merchant count (`15,070`), not the broader merchant registry row count (`64,856`).

2) Ingestion pipeline status
- Value: `not fully healthy; one known ingestion follow-up remains blocked`
- Supporting issue:
  - `BUY-23605` (`high`, `blocked`): `Recurring ingestion pipeline health check`
- Method: derived from the already-confirmed CTO package for the same report date.
- Calculation note: this confirms the pipeline cannot be described as fully green/on-time from the evidence available here.

3) US coverage %
- Value: `162,133 / 2,762,711 = 5.87%` of confirmed catalog rows
- Supporting breakdown:
  - `products_us`: `162,133`
  - `public.products`: `2,762,711`
  - `products_sg`: `2,600,578`
- Method: reuse the latest confirmed `2026-05-26` CTO database counts already captured for the parent report.
- Calculation note: this is a US catalog share based on product rows, not a merchant coverage percentage. If the parent issue requires merchant-level US coverage, that remains unconfirmed.

4) Zero-result rate
- Value: `150 / 319 = 47.02%` month-to-date zero-result rate across all `api_query` events
- Supporting breakdown:
  - `319` month-to-date `api_query` events in PostHog project `415112`
  - `150` month-to-date `api_query` events with `properties.result_count = 0`
  - `10` same-day `api_query` events on `2026-05-26 UTC`, all missing `result_count`
  - `10` month-to-date `api_query` events are missing `result_count`, which implies an instrumentation gap on part of the live traffic
- Method: production PostHog HogQL against `events`, using `api_query.result_count` as the zero-result predicate
- Calculation note: if the rate is restricted to only instrumented `api_query` events with a populated `result_count`, the month-to-date zero-result rate is `150 / 309 = 48.54%`. The report should call out the `10` null `result_count` events rather than silently excluding them.

## Source inputs used

- [docs/daily-ceo-report-2026-05-26.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-2026-05-26.md)
- [docs/daily-ceo-report-input-2026-05-26-rex.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-input-2026-05-26-rex.md)

## Source queries

```sql
-- Catalog-backed distinct merchant count
select count(distinct merchant_id) as distinct_product_merchants
from products;
```

```sql
-- Reconcile product-backed merchant ids to merchant registry rows
with product_merchants as (
  select distinct merchant_id from products
)
select
  count(*) as catalog_merchants_joined
from product_merchants pm
join merchants m on m.id = pm.merchant_id;
```

```sql
-- Product-backed merchant ids missing a merchant registry row
with product_merchants as (
  select distinct merchant_id from products
)
select count(*) as product_merchants_missing_registry
from product_merchants pm
left join merchants m on m.id = pm.merchant_id
where m.id is null;
```

```sql
-- Merchant registry size
select count(*) from merchants;
```

```sql
-- Month-to-date zero-result rate for api_query
select
  count() as total_api_query,
  countIf(properties.result_count = 0) as zero_result,
  countIf(properties.result_count is null) as null_result_count
from events
where event = 'api_query'
  and timestamp >= toDateTime('2026-05-01 00:00:00')
  and timestamp < toDateTime('2026-05-27 00:00:00');
```

```sql
-- Same-day spot check for instrumentation completeness
select
  count() as total_api_query,
  countIf(properties.result_count = 0) as zero_result,
  countIf(properties.result_count is null) as null_result_count
from events
where event = 'api_query'
  and timestamp >= toDateTime('2026-05-26 00:00:00')
  and timestamp < toDateTime('2026-05-27 00:00:00');
```

## Status / caveats

- This package now includes the live Oracle production metrics requested for `BUY-24087`.
- Confirmed locally:
  - exact merchant count from production DB, with registry reconciliation
  - the catalog-region split needed for the report's current US-share row
  - zero-result rate from live PostHog telemetry
  - the known ingestion follow-up blocker carried in `BUY-23605`
- Still not fully resolved:
  - merchant-level US coverage percentage remains unconfirmed; the current `5.87%` is a product-row share, not merchant share
  - `10` live `api_query` events in the current MTD window are missing `result_count`, so search telemetry completeness is not yet perfect
