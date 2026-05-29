# PostHog Server Instrumentation Plan

Owner: Rex
Related issue: BUY-23136
Last updated: 2026-05-24

## Why this exists

The current BUY-23136 execution workspace only contains documentation, not the API or MCP runtime
source needed to implement instrumentation. This plan captures the exact runtime work so the issue
can resume immediately once the correct codebase is attached.

## Runtime integration requirements

### Shared analytics helper

Create a single server-side analytics module that:

- initializes the PostHog server client from environment configuration
- exposes typed capture helpers for `api_query`, `mcp_tool_call`, `search_performed`,
  `search_result_used`, and `agent_registered`
- derives a stable `distinct_id` using the product spec priority order
- adds common properties:
  - `request_id`
  - `environment`
  - `occurred_at`
  - `agent_identity`
  - `customer_account_id` when available
- hashes or redacts sensitive payload fields before capture
- no-ops safely when PostHog is not configured

### API runtime instrumentation

Instrument the main API request path around search/query handlers.

Capture:

- `api_query` once per request completion
- `search_performed` when a search executes
- `search_result_used` when a downstream action selects a returned item
- error details via PostHog exception capture or a dedicated failure event property set

Required computed values:

- `latency_ms`: wall-clock duration from request start to response/error
- `success`: true for successful responses, false for exceptions or error status codes
- `status_code`: final HTTP/application status
- `result_count`: returned item count
- `query_length`: sanitized query length
- `top_result_id` and `top_result_score` when present

Implementation shape:

1. Create a request context with `request_id`, start time, agent identity, and market.
2. Run handler logic inside a timing wrapper.
3. Emit success/failure telemetry in a `finally` block so latency is recorded on both paths.
4. Send sanitized query text or a hash if raw text is sensitive.

### MCP runtime instrumentation

Instrument the MCP tool dispatcher so every tool invocation records:

- `mcp_tool_call`
- `search_performed` for search-like tools
- `search_result_used` for follow-up selection/lookup tools

Required computed values:

- `tool_name`
- `result_count`
- `latency_ms`
- `success`
- `tool_arguments_hash` for sensitive arguments

Implementation shape:

1. Wrap the MCP tool execution entry point.
2. Start a timer before dispatch.
3. Capture success/failure and result count after execution.
4. Record exception metadata without attaching raw sensitive arguments.

### Agent registration instrumentation

Emit `agent_registered` at the integration or API-key provisioning path, not lazily on first use,
unless no explicit registration flow exists.

Required properties:

- `agent_identity`
- `agent_name`
- `agent_type`
- `customer_account_id`
- `integration_type`
- `environment`
- `occurred_at`

## Error and latency observability

Use the same request/tool wrappers to ensure:

- failed API queries still emit `api_query` with `success=false`
- failed MCP tool calls still emit `mcp_tool_call` with `success=false`
- exception capture includes request correlation identifiers
- latency is always captured, including for thrown errors and timeouts

Recommended properties for failure cases:

- `error_name`
- `error_code`
- `error_class`
- `is_timeout`

Do not attach raw query text, raw tool arguments, or full stack traces if they may contain customer
data.

## Verification path

Minimum verification once the codebase is available:

1. Add a unit or integration test around the shared analytics helper that asserts event payload
   shape and redaction behavior.
2. Add one API-path test proving `api_query` emits `latency_ms`, `status_code`, `success`, and
   `request_id`.
3. Add one MCP-path test proving `mcp_tool_call` emits on both success and failure.
4. Run a local smoke with PostHog configured and confirm the five event names arrive in project
   `415112`.
5. Verify `latency_ms` is numeric so PostHog can chart p95 by endpoint/tool.

## Expected configuration

The application code should provide environment variables equivalent to:

- `POSTHOG_API_KEY`
- `POSTHOG_HOST`
- `APP_ENV` or similar environment label

Optional:

- feature flag to disable analytics in tests
- flush interval or explicit flush on shutdown

## Unblock needed

BUY-23136 cannot be completed in the current workspace because there is no API or MCP runtime
source tree to modify. Resume implementation after the correct repository or execution workspace is
attached to the issue.
