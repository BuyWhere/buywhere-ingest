# BUY-32028 Runtime Surface Audit

Date: 2026-06-06
Agent: Rex

## Summary

I could not safely patch the live `/v1/products/search` query path from the currently attached workspace because the reachable local repositories do not contain the Postgres-backed implementation that matches the live production behavior.

## Evidence

1. The assigned checkout (`18221361-973a-493e-9e19-4c43b7a1c6eb/_default`) is an ops/scripts workspace.
   - It contains `scripts/search_timeout_diagnostic.py`, which documents the likely root cause: `ORDER BY ts_rank(...)` causing broad-query timeouts.
   - It does not contain an HTTP service implementation for `/v1/products/search`.

2. A sibling checkout (`e61bbe4e-c203-446d-ba8d-4cbf612804e3/_default`) contains `mcp-server-production.js` and `mcp-server.js`, but both expose only a mock `/v1/products/search` handler.
   - The handler returns hard-coded products and does not execute SQL.
   - `deploy.sh` in that repo starts `node mcp-server-production.js`, so that checkout represents a mock/test service surface, not the live ranked search implementation described in BUY-32028.

3. A second sibling checkout (`4b4739f7-c7f5-42d3-b6ab-f7b58687c9d3/_default`) contains catalog ingestion scripts and merchant packages.
   - It contains SQL references to `products`, but no `/v1/products/search` route and no `ts_rank(...)` query path.

4. The live endpoint behavior described in BUY-32028 does not match either local service checkout.
   - Production returns `503 {"error":"Search query timed out","timeout_ms":20000}` for broad US queries.
   - The mock route in the reachable local service repo cannot produce that response shape or execute ranked full-text search.

## Conclusion

The production service backing `https://api.buywhere.ai/v1/products/search` is not present in the currently attached execution workspace(s), or production is running an undeclared runtime artifact that is no longer represented by the local source tree.

## Unblock Needed

Provide one of:

1. The actual service repository/workspace that backs `api.buywhere.ai` search in production.
2. The deployment/runtime source of truth for the ranked query path currently serving `/v1/products/search`.
3. A deployment path that is explicitly confirmed to publish changes from one of the reachable local repos.
