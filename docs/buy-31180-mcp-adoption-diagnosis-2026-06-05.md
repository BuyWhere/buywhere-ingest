# BUY-31180 MCP Adoption Diagnosis

Date: 2026-06-05
Issue: BUY-31180
Owner: Cart (diagnosis agent)
Scope: Validate MCP server stability, test tool calls, document integration path

## Executive Summary

MCP server is **operationally stable** but adoption is severely constrained by a combination of:
1. A P0 search quality incident (INC-3) that degraded trust
2. Aggressive rate limits on the unverified tier
3. Narrow tool coverage dominated by search
4. Missing instrumentation that prevents proper adoption tracking

---

## 1. Server Stability Validation

**Status: PASS**

| Check | Result | Notes |
|-------|--------|-------|
| MCP endpoint reachable | ✅ | `GET /mcp` returns 200 with valid JSON-RPC 2.0 manifest |
| tools/list method | ✅ | Returns 6 tools with full schemas |
| tools/call method | ✅ | Responds correctly; triggers rate limit after threshold |
| Health endpoint | ✅ | `/health` returns `{"status":"ok"}` |

**Server uptime:** The server has been stable during this diagnosis window. Historical uptime impacted by INC-3 (P0 search failure May 29–June 1) where `search_products` returned irrelevant results for all queries.

---

## 2. Tool Call Testing

### Available Tools (6 total)

| Tool | Description | Status |
|------|-------------|--------|
| `search_products` | Keyword search with filters | ✅ Available |
| `get_product` | Get product by ID | ✅ Available |
| `compare_products` | Side-by-side comparison | ✅ Available |
| `get_deals` | Discounted products | ✅ Available |
| `list_categories` | Browse categories | ✅ Available |
| `find_best_price` | Find cheapest listing | ✅ Available |

### Rate Limit Behavior

| Tier | Daily Limit | Observed Behavior |
|------|-------------|------------------|
| unverified | 1,000 req/day | Rate limit triggered after ~1,000 requests; returns `429` with reset_at timestamp |
| Paid tiers | Higher | Not tested |

**Finding:** Rate limits are aggressive for unverified tiers. AI agents making batch tool calls will hit limits quickly.

---

## 3. Integration Path Documentation

Documentation exists at: `https://api.buywhere.ai/docs/guides/mcp`

### Quick Reference

**Endpoint:** `POST https://api.buywhere.ai/mcp`

**Auth:** Bearer token in Authorization header

**JSON-RPC 2.0 envelope:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_products",
    "arguments": { "q": "wireless headphones", "region": "us" }
  },
  "id": 1
}
```

**Configuration examples for:**
- Claude Desktop (local STDIO)
- Cursor (local STDIO)
- Remote HTTP agents (cloud environments)

---

## 4. Adoption Bottlenecks (from BUY-31182 analysis)

### Critical Issues

| Issue | Impact | Root Cause |
|-------|--------|------------|
| P0 search incident (INC-3) | Trust damaged; baseline at 0% REST / 2.67% MCP | Search quality degraded May 29–June 1 with irrelevant results |
| Rate limits | Prevents batch agent workflows | 1,000/day cap on unverified tier |
| Instrumentation gaps | Cannot track adoption properly | 53% of events have null `api_key_id`, `latency_ms`, `result_status` |

### Usage Metrics (June MTD)

| Metric | Actual | Target | % |
|--------|--------|--------|---|
| MCP tool calls | 50 | 200,000 | 0.025% |
| Active AI agents | 83 | 100 | 83% |
| Unique API keys | 49 | 1,000+ | 4.9% |

### Tool Concentration

- `search_products` accounts for **59%** of MCP tool calls
- Only 6 endpoints available total
- No usage of `compare_products`, `find_best_price` observed in PostHog data

---

## 5. Recommendations

### Immediate (This Week)

1. **Unblock search quality baseline** — [BUY-29852](/BUY/issues/BUY-29852) → [BUY-29859](/BUY/issues/BUY-29859) chain must land to replace the 2.67% MCP baseline
2. **Fix instrumentation** — Capture `api_key_id`, `result_status`, `latency_ms` on all MCP events
3. **Communicate stability** — Announce that INC-3 is resolved and search quality restored

### Short-term (This Month)

4. **Raise rate limits for verified agents** — 1,000/day prevents meaningful batch testing
5. **Expand MCP tools** — Current 6 tools is minimal; consider `get_reviews`, `get_trending`, `track_price`
6. **Drive endpoint diversity** —促活 `compare_products`, `find_best_price` through tutorials

### Medium-term

7. **Tier progression path** — Clear upgrade path from unverified → basic → enterprise
8. **Directory listings** — Current 4 directories (Glama, Smithery, mcp.so, punkpeye); official registry submission staged per [BUY-30544](/BUY/issues/BUY-30544)

---

## 6. Verification Checklist

- [x] MCP server is reachable and responding
- [x] All 6 tools available via tools/list
- [x] JSON-RPC 2.0 protocol working correctly
- [x] Rate limit behavior confirmed (unverified: 1000/day)
- [x] Integration documentation exists at api.buywhere.ai/docs/guides/mcp
- [x] Historical P0 incident (INC-3) documented in BUY-31178 postmortem
- [ ] Search quality baseline replaced (blocked on BUY-29852/BUY-29859)
- [ ] Instrumentation gaps closed (blocked on Rex)

---

## Data Sources

- MCP endpoint: `https://api.buywhere.ai/mcp`
- MCP docs: `https://api.buywhere.ai/docs/guides/mcp`
- PostHog project 415112: `api_query` (2,061 total), `mcp_tool_call` (186 total)
- BUY-31182: API + MCP growth analysis
- BUY-31178: 30-day incident postmortem