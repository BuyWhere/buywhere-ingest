# BUY-31962 — Runtime Source & Verification Blocker (2026-06-09)

## Outcome of this heartbeat
- Root-cause work is **blocked** by two hard constraints in this workspace.

### 1) Missing production MCP handler source in attached checkouts
- The issue requires `/v1/products/search` + MCP tool implementations for `search_products` / `find_best_price`.
- I confirmed in sibling checkouts (`18221361-973a-...`, `18221361-973e-...`, `e61bbe4e-...`, `4b4739f7-...`), no checkout contains the live production search implementation.
- `BUY-32028` explicitly already concluded:
  - mock `mcp-server-production.js` in `e61bbe4e...` only contains hard-coded test handlers
  - actual production search runtime is absent from attached source
  - conclusion: attach source-of-truth or deployment path before server fixes are possible.

### 2) External quota gate prevents live verification
- Both REST and MCP probes with the available key return:
  - `rate_limit_exceeded` with reset `2026-06-10T00:00:00.000Z` (10,000 daily limit)
- Latest quick check (2026-06-09):
  - `POST https://mcp.buywhere.ai/mcp` with `search_products` returns 429 rate limit.
- Evidence logged in:
  - `docs/buy-33696-quota-blocker-2026-06-09.md`
  - `data/basket32954/mcp_results.jsonl`
  - `data/basket32954/rest_results.jsonl`

## Action required to unblock
1. Provide the actual production API repository/workspace (or confirm deployment publishes from a known checkout) that implements:
   - MCP `tools/call` handlers for `search_products` and `find_best_price`
   - the backing `/v1/products/search` runtime path
2. Resume verification with a fresh key (or after quota reset at 2026-06-10T00:00:00Z UTC).
3. Once access is provided, run minimal reproducer calls for:
   - `search_products` (`q`, `q + region`, empty `q`, unknown product)
   - `find_best_price` (valid product and unknown product)

## Evidence files reviewed
- `docs/buy-31279-cart-mcp-support-2026-06-05.md`
- `docs/buy-32028-runtime-surface-audit-2026-06-06.md`
- `docs/buy-33696-quota-blocker-2026-06-09.md`
- `docs/buy-16348-LIVE-TRIAGE-2026-06-08.md`
- `scripts/basket_verify_32954.py`
