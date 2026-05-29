# PostHog Product Analytics Spec

Owner: Reed (CPO)
Project: PostHog project `415112`
Last updated: 2026-05-24

## Scope

BuyWhere is an API/MCP product used by AI agents. Useful PostHog data will come from explicit
server-side event capture, not browser autocapture features like heatmaps or session replay.

This document defines the product analytics contract that engineering should emit and that product
should use for dashboards and KPI reporting.

## Distinct ID Strategy

Use a stable PostHog `distinct_id` per calling agent identity.

Priority order:

1. API key id, if each agent has a unique key
2. MCP client id / integration id
3. Fallback synthetic id derived from account plus agent name

Required person properties:

- `agent_name`
- `agent_type`
- `customer_account_id`
- `integration_type`
- `first_seen_at`

## Core Events

### `api_query`

Emit for every API query request.

Required properties:

- `endpoint`
- `method`
- `agent_identity`
- `query_text`
- `query_length`
- `result_count`
- `latency_ms`
- `status_code`
- `success`
- `market`
- `request_id`
- `environment`
- `occurred_at`

Optional properties:

- `top_result_id`
- `top_result_score`
- `customer_account_id`

### `mcp_tool_call`

Emit for every MCP tool invocation.

Required properties:

- `tool_name`
- `agent_identity`
- `result_count`
- `latency_ms`
- `success`
- `request_id`
- `environment`
- `occurred_at`

Optional properties:

- `tool_arguments_hash`
- `market`
- `customer_account_id`

### `search_performed`

Emit when an agent executes a search flow, whether through API or MCP.

Required properties:

- `query`
- `query_length`
- `agent_identity`
- `result_count`
- `market`
- `request_id`
- `environment`
- `occurred_at`

Optional properties:

- `top_result_relevance`
- `search_mode`
- `filters_applied`

### `search_result_used`

Emit when an agent meaningfully uses a search result, including downstream `get_product`,
`compare`, or equivalent action.

Required properties:

- `source_event_request_id`
- `agent_identity`
- `action_type`
- `selected_result_id`
- `selected_result_rank`
- `environment`
- `occurred_at`

Optional properties:

- `selected_result_score`
- `market`

### `agent_registered`

Emit when a new agent identity or integration is created.

Required properties:

- `agent_identity`
- `agent_name`
- `agent_type`
- `customer_account_id`
- `integration_type`
- `environment`
- `occurred_at`

### `repeat_call_7d`

Derived event or scheduled flag for agents that make a repeat request within 7 days of first use.

Required properties:

- `agent_identity`
- `first_call_at`
- `repeat_call_at`
- `environment`

## KPI Definitions

### API queries per month

Count of `api_query` events in the reporting month.

### MCP tool calls per month

Count of `mcp_tool_call` events in the reporting month.

### Active AI agents

Unique `distinct_id` values with at least one `api_query` or `mcp_tool_call` during the reporting
window.

### Search success rate

Recommended primary definition:

`search_result_used / search_performed`

Computed as the percentage of `search_performed` events that produce at least one downstream
`search_result_used` event tied by request id or session correlation.

Secondary cuts:

- by market
- by tool / endpoint
- by result count bucket

### Agent activation funnel

Funnel steps:

1. `agent_registered`
2. first `api_query` or `mcp_tool_call`
3. `repeat_call_7d`
4. active in trailing 30 days

## Dashboards

### Product Usage

Required tiles:

- monthly `api_query` volume vs target
- monthly `mcp_tool_call` volume vs target
- unique active agents in trailing 30 days
- search success rate overall
- search success rate by market
- top endpoints by volume
- top MCP tools by volume
- p95 latency by endpoint from `api_query.latency_ms`
- activation funnel
- 7-day retention / repeat usage trend

### Operational Analytics Inputs

These are owned by engineering but should reuse the same event stream:

- error rate by endpoint
- failed MCP tool calls
- p95 latency trend

## Implementation Notes For Engineering

- Use server-side PostHog capture in the API and MCP runtime.
- Do not rely on browser autocapture for product metrics.
- Ensure `request_id` is present on related events so searches can be tied to downstream usage.
- Strip or hash sensitive payload fields before sending to PostHog.
- If raw query text is sensitive, emit a sanitized version plus `query_length` and a hash.

## Dependencies

Product definition is complete in this document. Remaining execution dependencies:

- Rex: instrument event emission in API/MCP services and enable error/latency capture
- Lyra: configure human-web PostHog usage separately for marketing
- Vera: consume resulting dashboards in reporting

## Current Status

- Event schema defined: yes
- Dashboard spec defined: yes
- Instrumentation confirmed live: no
- Dashboard build confirmed live: no
