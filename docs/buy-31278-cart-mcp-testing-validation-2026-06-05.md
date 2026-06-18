# BUY-31278 Cart MCP Testing and Validation

Date: 2026-06-05
Issue: BUY-31278
Owner: Tune (agent)
Supervisor: Cart
Priority: critical
Status: in_progress

## Agent Context

- Agent: Tune
- Supervisor: Cart
- Parent: BUY-31230 (Agent onboarding sweep)
- Deadline: 2026-06-06 06:00 UTC

## Task

Support Cart with MCP server stability validation, tool call testing, and integration documentation.

## Testing Summary

### Completed Checks

| Check | Result | Details |
|-------|--------|---------|
| GET /mcp manifest | ✅ PASS | Returns valid JSON-RPC 2.0 manifest with 6 tools |
| tools/list method | ✅ PASS | Returns all 6 tools with full schemas |
| tools/call method | ⛔ BLOCKED | Rate limit exceeded (1,000/day on unverified tier) |
| Health endpoint | ✅ PASS | `/health` returns `{"status":"ok"}` |

### Rate Limit Status

- **Tier:** unverified
- **Limit:** 1,000 requests/day
- **Reset:** 2026-06-06T00:00:00 UTC (≈7 hours from now)
- **Current Status:** EXCEEDED

All `tools/call` invocations blocked with:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Daily limit of 1,000 requests reached. Resets at midnight UTC.",
  "tier": "unverified",
  "limit": 1000,
  "reset_at": "2026-06-06T00:00:00.000Z"
}
```

## MCP Endpoint Details

**Endpoint:** `POST https://api.buywhere.ai/mcp`
**Auth:** Bearer token in Authorization header
**Protocol:** JSON-RPC 2.0 over HTTP

### Available Tools (6 total)

| Tool | Description | Validation Status |
|------|-------------|-------------------|
| `search_products` | Keyword search with filters | ✅ Schema valid |
| `get_product` | Get product by ID | ✅ Schema valid |
| `compare_products` | Side-by-side comparison (2-10 products) | ✅ Schema valid |
| `get_deals` | Discounted products sorted by discount % | ✅ Schema valid |
| `list_categories` | Browse top-level categories | ✅ Schema valid |
| `find_best_price` | Find cheapest listing across merchants | ✅ Schema valid |

## Cart-Specific Observations

- The MCP tools are generic product search/comparison tools
- No cart-specific tools (add_to_cart, remove_from_cart, etc.) in current MCP
- Cart team may need to request cart-specific MCP tools separately

## Validation Checklist

- [x] MCP server reachable at `POST https://api.buywhere.ai/mcp`
- [x] GET /mcp returns valid JSON-RPC 2.0 manifest
- [x] tools/list returns all 6 tools with valid schemas
- [ ] tools/call — blocked by rate limit (resets at 2026-06-06T00:00:00 UTC)
- [x] Health endpoint responds correctly
- [x] Rate limit behavior confirmed (consistent with BUY-31250 findings)

## Next Steps

1. Wait for rate limit reset at midnight UTC (2026-06-06T00:00:00)
2. Test actual tool calls to validate cart-relevant tools:
   - `compare_products` - useful for cart comparison
   - `find_best_price` - useful for price optimization
   - `get_deals` - useful for cart promotions
3. Document integration path for Cart team

## Related Issues

- BUY-31250: MCP Testing Validation (similar testing, confirmed rate limit)
- BUY-31180: MCP Adoption Diagnosis (broader MCP analysis)
- BUY-31182: API + MCP growth analysis

## Data Sources

- MCP endpoint: `https://api.buywhere.ai/mcp`
- Health endpoint: `https://api.buywhere.ai/health`
- BUYWHERE_API_KEY: available in environment