# Daily CEO Report Input

Date: 2026-05-26
Issue: BUY-24223
Owner: Reed (CPO)
Workspace: Paperclip issue checkout `_default`

## Correction notice

Initial query ran at ~14:05 UTC. MCP telemetry went live at 16:12 UTC today — after that initial report. This document supersedes the 14:05 UTC values with a re-query at ~23:35 UTC.

## Required KPI values (queried 2026-05-26 ~23:35 UTC — corrected)

Reporting window used for monthly KPI definitions in the product spec:

- Month to date: `2026-05-01 00:00:00 UTC` through query time on `2026-05-26 UTC`
- Same-day spot check: `2026-05-26 00:00:00 UTC` through query time on `2026-05-26 UTC`

1) Platform coverage count
- Value: `2` covered production product platforms
- Method: Treat live product platform coverage as the count of required product telemetry surfaces with verified event emission in PostHog project `415112`.
- Evidence:
  - `api_query` is live with `319` events month to date (first observed 2026-05-23 08:24 UTC).
  - `mcp_tool_call` is now live with `22` events month to date (first observed 2026-05-26 16:12 UTC — MCP instrumentation went live today).
- Calculation note: **Both** required product platforms are now confirmed live: `2/2`. This is an upgrade from the 14:05 UTC report which showed `1/2` because MCP telemetry had not yet been emitted at that time.

2) API query volume
- Value: `319` month-to-date `api_query` events
- Method: Count of `api_query` events in PostHog project `415112`.
- Source: Live PostHog HogQL query against `events`.
- Correction note: Initial 14:05 UTC report showed `309`; 10 additional events were emitted between 14:05 and 23:35 UTC on 2026-05-26.

3) MCP tool call volume
- Value: `22` month-to-date `mcp_tool_call` events
- Tool breakdown:
  - `search_products`: 20 calls (2026-05-26 16:12–16:14 UTC)
  - `get_deals`: 1 call (2026-05-26 16:14 UTC)
  - `list_categories`: 1 call (2026-05-26 16:14 UTC)
- Method: Count of `mcp_tool_call` events in PostHog project `415112`.
- Source: Live PostHog HogQL query against `events`.
- Correction note: Initial 14:05 UTC report showed `0`; MCP instrumentation first emitted at 16:12 UTC on 2026-05-26. This is the first day MCP telemetry is present in the project. Prior reports (2026-05-24, 2026-05-25) correctly showed `0` because MCP was not yet instrumented.

4) Framework integrations
- Value: `0` named framework integrations observed in live product telemetry
- Observed buckets: `unknown = 309` (legacy events), `null/unset = 10` (newer events)
- Method: Group live `api_query` events by `properties.agent_framework`; count named frameworks separately from the `unknown` and null fallback buckets.
- Source: Live PostHog HogQL query against `events`.
- Calculation note: No named `agent_framework` values have appeared. The 10 newer `api_query` events lack the property entirely; 309 earlier events are tagged `unknown`.

## Source queries

```sql
-- All events: full history counts with first/last seen
select event, count() as c, min(timestamp) as first_seen, max(timestamp) as last_seen
from events
group by event
order by c desc
```

```sql
-- MCP tool call breakdown by tool
select properties.tool_name as tool_name, count() as c, min(timestamp) as first, max(timestamp) as last
from events
where event = 'mcp_tool_call'
group by properties.tool_name
order by c desc
```

```sql
-- Framework breakdown for api_query (MTD)
select properties.agent_framework as framework, count() as c
from events
where event = 'api_query'
  and timestamp >= toDateTime('2026-05-01 00:00:00')
group by framework
order by c desc
```

## Status / caveats

- All values sourced from live PostHog data (project `415112`), re-queried at ~23:35 UTC on 2026-05-26.
- **MCP telemetry is now live** as of 16:12 UTC on 2026-05-26 — first time in the project's history. This resolves the longstanding 0/1 platform coverage blocker.
- Framework integration property (`agent_framework`) is still not populated with named frameworks; all API traffic falls in `unknown` or null bucket.
- The 10 newer `api_query` events (emitted after 14:05 UTC) lack the `agent_framework` property entirely, suggesting a recent instrumentation change.
- These values are confirmed for the 2026-05-26 CEO report ([BUY-24087](/BUY/issues/BUY-24087)).
