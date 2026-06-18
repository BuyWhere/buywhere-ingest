# BUY-31289 Cart MCP Design

Date: 2026-06-05
Issue: BUY-31289
Owner: Hue (9c478889-e182-4714-b3d0-19b2672c1601)
Supervisor: Cart
Priority: critical
Status: in_progress (awaiting rate limit reset)

## Overview

Cart MCP provides Model Context Protocol access to the buywhere product catalog. This document outlines the integration design, tool schemas, and test coverage strategy.

## MCP Endpoint

- **URL**: `POST https://api.buywhere.ai/mcp`
- **Protocol**: JSON-RPC 2.0 over HTTP
- **Protocol Version**: 2024-11-05
- **Auth**: Bearer token (BUYWHERE_API_KEY)
- **Rate Limit**: 1,000 requests/day (unverified tier) — resets at midnight UTC

## Available Tools (6 Total)

| Tool | Description | Schema Status |
|------|-------------|---------------|
| `search_products` | Keyword search with filters | ✅ Valid |
| `get_product` | Get product by ID | ✅ Valid |
| `compare_products` | Side-by-side comparison (2-10 products) | ✅ Valid |
| `get_deals` | Discounted products sorted by discount % | ✅ Valid |
| `list_categories` | Browse top-level categories | ✅ Valid |
| `find_best_price` | Find cheapest listing across merchants | ✅ Valid |

## Tool Schemas (Verified via tools/list)

### search_products

```json
{
  "name": "search_products",
  "description": "Search the BuyWhere product catalog by keyword. Returns products from e-commerce platforms across multiple regions (Singapore, US, etc.).",
  "inputSchema": {
    "type": "object",
    "properties": {
      "q": { "type": "string", "description": "Keyword search query" },
      "domain": { "type": "string", "description": "Filter by merchant platform (e.g. lazada, shopee, amazon)" },
      "region": { "type": "string", "description": "Filter by region (sea, us, eu, au)" },
      "country_code": { "type": "string", "enum": ["SG", "US", "VN", "TH", "MY"], "description": "Filter by ISO country code" },
      "min_price": { "type": "number", "description": "Minimum price" },
      "max_price": { "type": "number", "description": "Maximum price" },
      "limit": { "type": "integer", "description": "Number of results (max 100, default 20)" },
      "compact": { "type": "boolean", "description": "Agent-optimized compact shape" },
      "category": { "type": "string", "description": "Filter by product category name" }
    }
  }
}
```

### get_product

```json
{
  "name": "get_product",
  "description": "Get a specific product by its ID, including full details and current price.",
  "inputSchema": {
    "type": "object",
    "required": ["id"],
    "properties": {
      "id": { "type": "string", "description": "Product UUID" }
    }
  }
}
```

### compare_products

```json
{
  "name": "compare_products",
  "description": "Compare multiple products side-by-side. Returns price, brand, rating, and category.",
  "inputSchema": {
    "type": "object",
    "required": ["ids"],
    "properties": {
      "ids": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Array of product IDs to compare (2-10)",
        "minItems": 2,
        "maxItems": 10
      }
    }
  }
}
```

### get_deals

```json
{
  "name": "get_deals",
  "description": "Get discounted products sorted by discount percentage.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "min_discount": { "type": "number", "description": "Minimum discount percentage (default 10)" },
      "currency": { "type": "string", "description": "Filter by currency code (SGD, USD, MYR, VND, THB)" },
      "region": { "type": "string", "description": "Filter by region (sea, us, eu, au)" },
      "country_code": { "type": "string", "enum": ["SG", "US", "VN", "TH", "MY"] },
      "limit": { "type": "integer", "description": "Number of results (max 100, default 20)" }
    }
  }
}
```

### list_categories

```json
{
  "name": "list_categories",
  "description": "List top-level product categories available in the BuyWhere catalog.",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

### find_best_price

```json
{
  "name": "find_best_price",
  "description": "Find the best current price across all merchants for a product.",
  "inputSchema": {
    "type": "object",
    "required": ["product_name"],
    "properties": {
      "product_name": { "type": "string", "description": "Product name to find best price for" },
      "category": { "type": "string", "description": "Category to filter by" },
      "country_code": { "type": "string", "enum": ["SG", "MY", "TH", "PH", "VN", "ID", "US"] },
      "region": { "type": "string", "enum": ["us", "sea"] }
    }
  }
}
```

## Test Coverage Design

### Priority 1 — Core Functionality (When rate limit clears)

| Test Case | Tool | Expected Result |
|-----------|------|-----------------|
| TC-01: Basic keyword search | `search_products` | Returns matching products |
| TC-02: Search with price filter | `search_products` | Returns filtered results |
| TC-03: Get product by valid ID | `get_product` | Returns product details |
| TC-04: Get product by invalid ID | `get_product` | Returns error |
| TC-05: Compare 2 products | `compare_products` | Returns comparison data |
| TC-06: Compare 10 products (max) | `compare_products` | Returns comparison data |
| TC-07: Compare 11 products (over max) | `compare_products` | Returns validation error |
| TC-08: Get deals sorted by discount | `get_deals` | Returns sorted deals |
| TC-09: List all categories | `list_categories` | Returns category list |
| TC-10: Find best price for product | `find_best_price` | Returns cheapest listing |

### Priority 2 — Edge Cases

| Test Case | Tool | Expected Result |
|-----------|------|-----------------|
| TC-11: Empty search query | `search_products` | Returns validation error |
| TC-12: Search with no results | `search_products` | Returns empty array |
| TC-13: Compare 1 product (below min) | `compare_products` | Returns validation error |
| TC-14: Get deals with min_discount=100 | `get_deals` | Returns only 100% off items |
| TC-15: Find best price for unknown product | `find_best_price` | Returns error |

### Priority 3 — Integration Tests

| Test Case | Description |
|-----------|-------------|
| IT-01: Auth header validation | Missing/invalid token returns 401 |
| IT-02: Rate limit headers | Verify X-RateLimit-* headers present |
| IT-03: Concurrent requests | Handle multiple simultaneous calls |
| IT-04: Large result set | Pagination or limit enforcement |

## Design Considerations

### Cart Use Cases

1. **Product Discovery**: Use `search_products` to find items in cart category
2. **Price Comparison**: Use `compare_products` when user adds multiple items
3. **Deal Alerts**: Use `get_deals` to highlight discounted items in cart
4. **Best Price**: Use `find_best_price` to ensure cart has best deal
5. **Category Browse**: Use `list_categories` for cart organization

### Error Handling

- Rate limit: Implement exponential backoff with 1h cooldown
- 4xx errors: Log and surface to user
- 5xx errors: Retry with circuit breaker (3 attempts, 30s timeout)

### Rate Limit Strategy

- **Current**: 1,000 req/day (unverified tier)
- **Needed for production**: 10,000+ req/day
- **Escalation path**: Contact Cart team to upgrade API tier

## Verification Results (2026-06-05 16:39 UTC)

### Connectivity Tests

| Test | Result | Details |
|------|--------|---------|
| GET /mcp manifest | ✅ PASS | Returns valid JSON-RPC 2.0 manifest |
| POST tools/list | ✅ PASS | Returns all 6 tools with full schemas |
| POST tools/call | ⛔ BLOCKED | Rate limit exceeded (1,000/day) |

### Rate Limit Error

```json
{
  "error": "rate_limit_exceeded",
  "message": "Daily limit of 1,000 requests reached. Resets at midnight UTC.",
  "tier": "unverified",
  "limit": 1000,
  "reset_at": "2026-06-06T00:00:00.000Z",
  "upgrade_url": "https://buywhere.ai/pricing"
}
```

## Blocker

**Blocker**: Rate limit exceeded on `tools/call` method
**Unblock**: Rate limit resets at 2026-06-06T00:00:00 UTC (~7.25h from now)

## Related Issues

- [BUY-31230](/BUY/issues/BUY-31230) — Parent: Agent onboarding sweep
- [BUY-31250](/BUY/issues/BUY-31250) — MCP testing validation (rate limit confirmed)
- [BUY-31278](/BUY/issues/BUY-31278) — [Tune] Cart MCP testing
- [BUY-31279](/BUY/issues/BUY-31279) — [Fetch] Cart MCP testing
