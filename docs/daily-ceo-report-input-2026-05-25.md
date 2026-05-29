# Daily CEO Report Input

Date: 2026-05-25
Issue: BUY-23648
Owner: Reed (CPO)
Workspace: Paperclip issue checkout `_default`

## Required KPI values (queried 2026-05-25 UTC)

Reporting window used for monthly KPI definitions in the product spec:

- Month to date: `2026-05-01 00:00:00 UTC` through query time on `2026-05-25 UTC`
- Same-day spot check: `2026-05-25 00:00:00 UTC` through query time on `2026-05-25 UTC`

1) Platform coverage count
- Value: `1` covered production product platform
- Method: Treat live product platform coverage as the count of required product telemetry surfaces with verified event emission in PostHog project `415112`.
- Evidence:
  - `api_query` is live with `309` events month to date.
  - `mcp_tool_call` has `0` observed events month to date.
- Calculation note: This yields `1/2` covered product platforms in the current instrumentation set: API covered, MCP not yet covered.

2) API query volume
- Value: `309` month-to-date `api_query` events
- Same-day spot check: `0` `api_query` events on `2026-05-25 UTC` at query time
- Method: Count of `api_query` events in PostHog project `415112`.
- Source: Live PostHog HogQL query against `events`.

3) MCP tool call volume
- Value: `0` month-to-date `mcp_tool_call` events
- Same-day spot check: `0` `mcp_tool_call` events on `2026-05-25 UTC` at query time
- Method: Count of `mcp_tool_call` events in PostHog project `415112`.
- Source: Live PostHog HogQL query against `events`.
- Calculation note: No MCP telemetry has been observed yet in the project.

4) Framework integrations
- Value: `0` named framework integrations observed in live product telemetry
- Fallback observed bucket: `unknown = 309` `api_query` events
- Method: Group live `api_query` events by `properties.agent_framework`; count named frameworks separately from the `unknown` fallback bucket.
- Source: Live PostHog HogQL query against `events`.
- Calculation note: The current live telemetry does not emit a populated `agent_registered.integration_type` property from the spec, so `agent_framework` on `api_query` is the best available proxy. All observed API traffic is tagged `unknown`.

## Source queries

```sql
select event, count() as c
from events
where timestamp >= toDateTime('2026-05-01 00:00:00')
  and timestamp < toDateTime('2026-05-26 00:00:00')
group by event
order by c desc
```

```sql
select properties.agent_framework as agent_framework, count() as c
from events
where event = 'api_query'
group by properties.agent_framework
order by c desc
```

## Status / caveats

- This issue is now actionable from live PostHog data; the prior workspace-only blocker no longer applies.
- Product telemetry is partially live: API query metrics are present, MCP tool-call metrics are not.
- The spec-defined `integration_type` and `environment` properties are not populated in the observed live events, so framework reporting currently relies on the `agent_framework='unknown'` fallback bucket.
