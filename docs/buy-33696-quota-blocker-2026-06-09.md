# BUY-33696 quota blocker evidence — 2026-06-09

Purpose: document why the BUY-32954 acceptance rerun is still not executable in this heartbeat.

## What was attempted

On 2026-06-09 between 07:48:24Z and 07:48:51Z UTC, `scripts/basket_verify_32954.py` was exercised four ways:

1. default REST + MCP probe (`--surface both --max-queries 3`)
2. explicit unverified-key REST probe (`BUYWHERE_REST_KEY=$BUYWHERE_API_KEY`)
3. explicit unverified-key MCP probe (`BUYWHERE_MCP_KEY=$BUYWHERE_API_KEY`)

## Result

Every probe failed immediately with HTTP `429 rate_limit_exceeded` before any successful basket query was recorded.

- Enterprise fallback key (`bw_live_4Ae…LzP`):
  - REST: daily limit `1000` reached, reset at `2026-06-10T00:00:00.000Z`
  - MCP: daily limit `1000` reached, reset at `2026-06-10T00:00:00.000Z`
- Environment key (`bw_265c38…864`):
  - REST: daily limit `10000` reached, reset at `2026-06-10T00:00:00.000Z`
  - MCP: daily limit `10000` reached, reset at `2026-06-10T00:00:00.000Z`

## Evidence in repo

- `data/basket32954/rest_results.jsonl`
- `data/basket32954/mcp_results.jsonl`
- `data/basket32954/rest_summary.json`
- `data/basket32954/mcp_summary.json`

Representative 2026-06-09 records:

- REST enterprise:
  - `{"query":"iPhone 15 Pro Max","country":"SG","limit":5,"status":429,...,"reset_at":"2026-06-10T00:00:00.000Z"}`
- REST unverified:
  - `{"query":"Samsung Galaxy S24","country":"SG","limit":5,"status":429,...,"reset_at":"2026-06-10T00:00:00.000Z"}`
- MCP enterprise:
  - `{"query":"iPhone 15 Pro","country":"SG","limit":5,"status":429,...,"reset_at":"2026-06-10T00:00:00.000Z"}`
- MCP unverified:
  - `{"query":"iPhone 13","country":"SG","limit":5,"status":429,...,"reset_at":"2026-06-10T00:00:00.000Z"}`

## Conclusion

The acceptance rerun cannot proceed until after `2026-06-10T00:00:00Z` UTC or until a fresh BuyWhere key with remaining daily quota is provided. This is an external quota blocker, not a harness failure.
