# BUY-23139: Catalog KPI source of truth and search-success data support

Date: 2026-05-28
Owner: Oracle

## Decision

- Exact catalog KPIs stay DB-backed, not PostHog-backed.
- PostHog remains the product-analytics surface for query/search behavior, not the source of truth
  for product count, merchant count, or catalog coverage.
- The public catalog stats endpoint is also not the canonical KPI source when it drifts from exact
  DB-backed reporting.

## Evidence

- Exact merchant count is defined from production Postgres over `public.products.merchant_id`,
  reconciled against `public.merchants`, with the report explicitly preferring the catalog-backed
  distinct merchant count over the broader merchant registry total.
- US coverage in the current reporting package is derived from confirmed database row counts
  (`products_us` vs `public.products`), not telemetry.
- Search telemetry currently uses PostHog `api_query` events and already shows a live data-quality
  caveat: some events are missing `result_count`, so telemetry completeness is not yet perfect.
- The 2026-05-28 CEO report documents a material drift between exact Oracle DB reporting and the
  public `/v1/catalog/stats` fallback surface, which confirms that exact DB-backed reporting must
  remain canonical for catalog KPIs.

## Source mapping

- Product count / merchant count / catalog coverage:
  production database reporting
- Search-success KPI / query behavior / usage telemetry:
  PostHog server-side product analytics events
- Public catalog stats endpoint:
  operational/runtime surface only; not canonical when it disagrees with exact DB counts

## Catalog-side support Reed needs

- Keep `request_id` on every search/query event so `search_performed` can be tied to downstream
  `search_result_used`.
- Ensure every search/query event has a non-null `result_count`; the current nulls weaken the
  zero-result and search-success analysis.
- Emit stable result identifiers and ranks for returned results so downstream usage can be matched to
  the selected catalog item.
- Preserve query context needed for relevance cuts: market, query text or sanitized query hash,
  filters, and top-result score/relevance when available.

## What Reed does not need from catalog

- Reed does not need PostHog to become the source of truth for catalog breadth KPIs.
- Reed does not need Oracle to move product, merchant, or coverage reporting ownership into
  analytics telemetry.
- A separate DB-backed query log can help offline relevance tuning later, but it is not required to
  keep catalog KPI truth or to define the primary search-success KPI contract already captured in
  product analytics.
