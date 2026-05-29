# Daily CEO Report Input

Date: 2026-05-24
Issue: BUY-23188
Owner: Reed (CPO)
Workspace: Paperclip issue checkout `_default`

## Required KPI values (as of 2026-05-24)

1) Platform coverage count
- Value: `0` active covered production platforms in this checkout
- Method: Count of production platform targets with confirmed live instrumentation and dashboard-backed metrics from source code + runtime validation.
- Source in this issue scope: only documentation exists in this workspace (`docs/posthog-product-analytics-spec.md`, `docs/posthog-server-instrumentation-plan.md`), and runtime repository is not attached.
- Calculation note: No `BUY-23136` runtime trees are present here, so there is no verifiable run-time surface to count.

2) API query volume
- Value: `unknown (not yet emitted in verified runtime)
- Method: Count of `api_query` events in PostHog project `415112`, reporting window for the metric period.
- Source: PostHog event stream for `api_query` (schema defined in `docs/posthog-product-analytics-spec.md`, expected implementation in `docs/posthog-server-instrumentation-plan.md`).
- Calculation note: No runtime instrumentation or event-access in this checkout to execute the query.

3) MCP tool call volume
- Value: `unknown (not yet emitted in verified runtime)
- Method: Count of `mcp_tool_call` events in PostHog project `415112`, same reporting window.
- Source: PostHog event stream for `mcp_tool_call` and server MCP runtime instrumentation plan.
- Calculation note: Same blocker as above; source emits are not yet live in attached workspace.

4) Framework integrations
- Value: `not yet enumerated in live inventory`
- Method: Enumerate implemented integrations by querying runtime `agent_registered.integration_type` and dashboard/report source-of-truth ownership list.
- Source: Product spec (`docs/posthog-product-analytics-spec.md`) and server instrumentation requirements (`docs/posthog-server-instrumentation-plan.md`).
- Calculation note: Existing docs define `integration_type` field and required properties, but no attached runtime registration data.

## Status / blocker

- Resume remains blocked by missing live runtime workspace for `BUY-23136` (no API/MCP source files in this checkout).
- Unblock owner/action: Rex/Lyra/Vera dependency handoff should continue in the attached runtime repository; once attached, values can be retrieved immediately by querying PostHog with the methods above.
- Canonical marketing dashboard remains `1622959` (from prior audit context).
