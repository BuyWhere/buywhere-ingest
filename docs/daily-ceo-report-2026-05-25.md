# Daily CEO Report

Date: 2026-05-25
Assembled on: 2026-05-26 UTC
Issue: BUY-23644
Workspace: Paperclip issue checkout `_default`

## Executive summary

- Product usage telemetry is partially live. API query volume is visible in PostHog; MCP tool-call telemetry is still at `0`, so current product analytics coverage is `1/2` required production surfaces.
- Oracle's catalog-backed data shows `15,070` distinct merchants, `5.87%` US product-row coverage, and a month-to-date zero-result query rate of `47.02%`.
- Core production platform health was strong in the last 24 hours measured: core API, DB, and Redis monitors each reported `100.000%` uptime, with probe-based API p95 latency at `637 ms`.
- Human website traffic remained healthy with `5,316` non-bot pageviews in the last 24 hours.
- The company runtime exposed `17` API or related credentials in the active CMO execution scope and `5` unique agents active in the last 24 hours.

## KPI snapshot

### Product / CPO

- Platform coverage count: `1`
  - Covered surfaces observed live: `api_query`
  - Missing live surface: `mcp_tool_call`
- API query volume: `309` month-to-date on `2026-05-25 UTC`
- MCP tool call volume: `0` month-to-date on `2026-05-25 UTC`
- Framework integrations: `0` named frameworks observed in live telemetry
  - Fallback bucket: `unknown = 309`

### Data / CDO

- Exact merchant count: `15,070`
  - Catalog-backed merchants also present in `public.merchants`: `15,006`
  - Catalog-backed merchants missing a matching `public.merchants` row: `64`
- Ingestion pipeline status: not fully healthy
  - Known blocked follow-up: `BUY-23605`
- US coverage: `5.87%`
  - Calculation: `162,133 / 2,762,711`
- Zero-result query rate: `47.02%` month-to-date across all `api_query` events
  - Supporting counts: `150 / 319`
  - Instrumentation caveat: `10` month-to-date `api_query` events were missing `result_count`

### Engineering / CTO

- Exact product count: `2,755,163`
- Platform uptime: `100.000%` over the last 24 hours for the core production monitor set
- API p95 latency: `637 ms`
- Current infra issues:
  - No active core API/DB/Redis outage at collection time
  - Open infra follow-ups remained in flight on `2026-05-25`: `BUY-23639`, `BUY-23641`, `BUY-23642`, `BUY-23605`, `BUY-23633`

### Go-to-market / CMO

- API key or token registrations visible in runtime scope: `17`
- Active agent DAU: `5`
  - Agents: `Cart`, `Fetch`, `Lyra`, `Reed`, `Rex`
- Directory listings: `2`
  - Entries: `Rich`, `Board`
- Website traffic: `5,316` human pageviews in the last 24 hours
  - `pageview_server`: `5,296`
  - `$pageview`: `20`

## Risks and caveats

- Product analytics are not fully complete for CEO reporting until `mcp_tool_call` emission is live.
- Merchant count is exact for the live catalog-backed footprint, not for the broader merchant registry row count.
- The reported US coverage figure is a product-row share, not a merchant-level US coverage percentage.
- The reported zero-result rate includes `10` month-to-date `api_query` events with missing `result_count`, so search telemetry was not fully complete.
- Framework reporting is currently limited by missing populated integration metadata, so usage is landing in the `unknown` bucket.
- API latency here is probe-based, not end-user request-log based, because the application query-log source was stale and the legacy insight path was unavailable in the original CTO collection run.
- The credential registration count is exact for the active CMO runtime scope, not necessarily a company-wide secrets inventory.

## Source inputs

- [docs/daily-ceo-report-input-2026-05-25.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-input-2026-05-25.md)
- [docs/daily-ceo-report-input-2026-05-25-rex.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-input-2026-05-25-rex.md)
- [docs/daily-ceo-report-input-2026-05-25-lyra.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-input-2026-05-25-lyra.md)
- [docs/daily-ceo-report-input-2026-05-26-oracle.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-input-2026-05-26-oracle.md)
