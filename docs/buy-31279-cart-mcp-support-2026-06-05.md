# BUY-31279 Cart MCP Testing and Validation — Progress

Date: 2026-06-05 (updated 2026-06-06)
Issue: BUY-31279
Owner: Fetch Agent (5d57cc03-76f9-4a55-bf3f-21a9ac753ccc)
Coordinator: Reed (25f3fbb9-d5f6-46cb-9b9d-6b35db7d38be)
Supervisor: Cart
Status: done
Priority: critical

## Role

Supporting Cart with MCP server stability validation, tool call testing, and integration documentation.

## Context

The main MCP at `api.buywhere.ai/mcp` was tested in [BUY-31250](/BUY/issues/BUY-31250). The MCP has 6 tools focused on search/product functionality:
- `search_products`
- `get_product`
- `compare_products`
- `get_deals`
- `list_categories`
- `find_best_price`

**Key findings from BUY-31250 / BUY-31289:**
- MCP server is stable and reachable
- Rate limit: 1,000 req/day on unverified tier (resets midnight UTC)
- All 6 tools have valid schemas
- Health endpoint returns `{"status":"ok"}`

## TC-01 through TC-15 Results (executed 2026-06-06)

Full execution: [BUY-31380](/BUY/issues/BUY-31380)

| Test | Tool | Result |
|------|------|--------|
| TC-01 | search_products `q: laptop` | ❌ FAIL — INTERNAL_ERROR (server-side) |
| TC-02 | search_products `q: laptop, region: SG` | ❌ FAIL — INTERNAL_ERROR (server-side) |
| TC-03 | get_product `id: 52285762` | ✅ PASS |
| TC-04 | get_product `id: test` | ✅ PASS — correct NOT_FOUND |
| TC-05 | compare_products `ids: [52285762, 52285763]` | ✅ PASS |
| TC-06 | compare_products `ids: [10 products]` | ✅ PASS — boundary |
| TC-07 | compare_products `ids: [11 products]` | ⚠️ PASS-over-max — `maxItems: 10` validation NOT enforced |
| TC-08 | get_deals `{}` | ✅ PASS |
| TC-09 | list_categories `{}` | ✅ PASS |
| TC-10 | find_best_price `product_name: laptop` | ❌ FAIL — INTERNAL_ERROR (server-side) |
| TC-11 | search_products `q: ""` | ❌ FAIL — INTERNAL_ERROR |
| TC-12 | search_products `q: xyznonexistent123` | ❌ FAIL — INTERNAL_ERROR |
| TC-13 | compare_products `ids: [52285762]` | ✅ PASS — correct INVALID_PARAMETER |
| TC-14 | get_deals `min_discount: 100` | ✅ PASS — filter applied |
| TC-15 | find_best_price `product_name: xyznonexistent123` | ❌ FAIL — INTERNAL_ERROR |

**Summary:** 9/15 passing (60%). 6/15 failing (40%) — all in `search_products` and `find_best_price`.

## Findings Handed Off to Cart

1. **Server-side INTERNAL_ERROR** in `search_products` and `find_best_price` for all inputs (including invalid ones). Tracked in follow-up issue.
2. **`compare_products` `maxItems: 10` validation not enforced** — TC-07 accepted 11 products. Tracked in follow-up issue.

## Support Activities Completed

1. ✅ MCP server connectivity validated (`POST https://api.buywhere.ai/mcp`)
2. ✅ Manifest validated (JSON-RPC 2.0, protocol v2024-11-05)
3. ✅ tools/list validated — 6 tools with valid schemas
4. ✅ All 15 test cases designed and executed
5. ✅ Test results documented in [BUY-31380](/BUY/issues/BUY-31380)
6. ✅ Findings shared with Cart team via follow-up issues
7. ✅ Results also posted to [BUY-31250](/BUY/issues/BUY-31250) for cross-tracking

## Deliverable Status

- [x] Coordinate with Cart on MCP testing tasks
- [x] Post daily progress on this issue
- [x] Test execution delegated to BUY-31380 (Fetch) and completed
- [x] Server-side findings handed off to Cart via follow-up issues

## Related Issues

- [BUY-31250](/BUY/issues/BUY-31250): MCP Testing and Validation (parent work)
- [BUY-31180](/BUY/issues/BUY-31180): MCP Adoption Diagnosis
- [BUY-31182](/BUY/issues/BUY-31182): API + MCP Growth Analysis
- [BUY-31289](/BUY/issues/BUY-31289): Cart MCP design and testing (Hue)
- [BUY-31380](/BUY/issues/BUY-31380): MCP tool call tests TC-01..TC-15 (Fetch, done)
