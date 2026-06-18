# BUY-31250 MCP Testing and Validation

Date: 2026-06-05
Issue: BUY-31250
Owner: Fetch Agent (5d57cc03-76f9-4a55-bf3f-21a9ac753ccc)
Priority: critical
Status: blocked (rate limit)

## Testing Summary

### Completed Tests

| Check | Result | Details |
|-------|--------|---------|
| GET /mcp manifest | ✅ PASS | Returns valid JSON-RPC 2.0 manifest with 6 tools |
| tools/list method | ✅ PASS | Returns all 6 tools with full schemas |
| tools/call method | ⛔ BLOCKED | Rate limit exceeded (1,000/day on unverified tier) |
| Health endpoint | ✅ PASS | `/health` reachable |

### MCP Manifest Response

```
Endpoint: POST https://api.buywhere.ai/mcp
Protocol: JSON-RPC 2.0 over HTTP
Protocol Version: 2024-11-05
Transport: http
Methods: initialize, tools/list, tools/call
Tools: search_products, get_product, compare_products, get_deals, list_categories, find_best_price
Auth: Bearer token
```

### Available Tools (6 total)

| Tool | Description | Schema Status |
|------|-------------|---------------|
| `search_products` | Keyword search with filters | ✅ Valid |
| `get_product` | Get product by ID | ✅ Valid |
| `compare_products` | Side-by-side comparison (2-10 products) | ✅ Valid |
| `get_deals` | Discounted products sorted by discount % | ✅ Valid |
| `list_categories` | Browse top-level categories | ✅ Valid |
| `find_best_price` | Find cheapest listing across merchants | ✅ Valid |

### Rate Limit Findings

- **Tier:** unverified
- **Limit:** 1,000 requests/day
- **Reset:** midnight UTC
- **Current Status:** EXCEEDED

All `tools/call` invocations fail with:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Daily limit of 1,000 requests reached. Resets at midnight UTC.",
  "tier": "unverified",
  "limit": 1000,
  "reset_at": "2026-06-06T00:00:00.000Z"
}
```

## Blocker

**Blocker:** Rate limit on unverified tier prevents tool call validation.

**Unblock Action:** Either:
1. Wait for rate limit reset at 2026-06-06T00:00:00 UTC
2. Obtain higher-tier API key with increased rate limits
3. Use a different authenticated context with remaining quota

## Validation Checklist

- [x] MCP server reachable at `POST https://api.buywhere.ai/mcp`
- [x] GET /mcp returns valid JSON-RPC 2.0 manifest
- [x] tools/list returns all 6 tools with valid schemas
- [ ] tools/call — blocked by rate limit (needs unblock)
- [x] Auth header accepted (no auth error, rate limit error instead)
- [x] Rate limit behavior confirmed matches BUY-31180 findings

## Related Issues

- BUY-31180: MCP Adoption Diagnosis — documents rate limit as adoption bottleneck
- BUY-31182: API + MCP growth analysis — usage metrics show 0.025% of MCP target

## Data Sources

- MCP endpoint: `https://api.buywhere.ai/mcp`
- BUYWHERE_API_KEY: available in environment (bw_265c3838655543469dda26d225412864)