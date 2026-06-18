# BUY-37423 — 35-query search harness verification (2026-06-09)

## Result

The accepted 35-query harness itself is not present in this workspace, so I could only verify the live code path and patch the nearest local rerun harness. Based on the `BUY-37129` artifact trail, the accepted 0/35 result came from `buy-22746-harness/basket_harness.py`, but that directory is absent from the current checkout.

What I could prove in this heartbeat:

- REST was already pointed at the current public search route: `https://api.buywhere.ai/v1/products/search`.
- MCP was pointed at the legacy hostname `https://mcp.buywhere.ai/mcp` instead of the current canonical public route `https://api.buywhere.ai/mcp`.
- Current source of truth shows that `search_products` is implemented as a thin forwarder to `/v1/products/search`, so REST and MCP both exercise the same live search handler once they land on the current API service.
- I updated the nearest local rerun harness default to use `https://api.buywhere.ai/mcp` and added explicit base-URL logging to the run output and summary files.

I could not republish a live benchmark in this heartbeat because:

1. every available BuyWhere key is already over its daily quota and the live endpoints return immediate `429 rate_limit_exceeded`, and
2. the actual accepted 35-query harness source (`buy-22746-harness/basket_harness.py`) is not present in the current workspace

## Code-path proof

### Current live REST path

The API service mounts the products router at `/v1/products`, and `/v1/search` is only a redirect alias:

- `.opencode_tmp/buywhere/api/src/server.ts:185` mounts `productsRouter` at `/v1/products`
- `.opencode_tmp/buywhere/api/src/server.ts:194-197` redirects `/v1/search` to `/v1/products/search`
- `.opencode_tmp/buywhere/api/src/routes/products.ts:172-178` registers `GET /search`

Inside that live handler, the actual search query path is `search_vector @@ plainto_tsquery(...)` with the ranked `top_ids` CTE:

- `.opencode_tmp/buywhere/api/src/routes/products.ts:244-249`
- `.opencode_tmp/buywhere/api/src/routes/products.ts:363-389`

### Current live MCP path

The current API service mounts MCP at `/mcp`:

- `.opencode_tmp/buywhere/api/src/server.ts:177-180`

The current MCP server implementation forwards `search_products` directly to `/v1/products/search` on `https://api.buywhere.ai` by default:

- `.opencode_tmp/buywhere/packages/mcp-server/src/index.ts:20`
- `.opencode_tmp/buywhere/packages/mcp-server/src/index.ts:139-141`

That means the current production design is:

1. `POST /mcp`
2. `tools/call name=search_products`
3. internal forward to `GET /v1/products/search`
4. same REST search handler as direct API traffic

## Accepted-harness provenance

The only concrete reference to the accepted 35-query harness I found is in the `BUY-37129` issue thread comment from `2026-06-09T06:16:41Z`, which states:

- canonical rubric source: `buy-22746-harness/basket_harness.py`
- accepted rerun artifacts:
  - `buy-22746-harness/runs/acceptance-rerun-rest-2026-06-06/summary.json`
  - `buy-22746-harness/runs/acceptance-rerun-mcp-2026-06-06/summary_mcp.json`

Workspace check from this heartbeat:

```text
find . -path '*buy-22746-harness*' -maxdepth 4 -type f
-> no matches
```

So the precise accepted harness cannot be patched or rerun from the current checkout without first restoring that missing directory or attaching the correct workspace.

## Harness verification

Before patch on the nearest local rerun script:

- `scripts/basket_verify_32954.py:43` REST default was already `https://api.buywhere.ai/v1/products/search`
- `scripts/basket_verify_32954.py:44` MCP default is now patched, but before this heartbeat it was `https://mcp.buywhere.ai/mcp`

After patch on the nearest local rerun script:

- `scripts/basket_verify_32954.py:43-44` defaults are:
  - REST: `https://api.buywhere.ai/v1/products/search`
  - MCP: `https://api.buywhere.ai/mcp`
- `scripts/basket_verify_32954.py:277-281` prints the chosen base URLs at runtime
- `scripts/basket_verify_32954.py:336-338` writes the effective base URL into each summary JSON

The harness still supports overrides through:

- `BUYWHERE_REST_BASE`
- `BUYWHERE_MCP_BASE`

## Live endpoint checks

Public host probes from this heartbeat:

```text
curl -sSI https://api.buywhere.ai/mcp
-> HTTP/2 200
-> server: railway-hikari
-> x-powered-by: Express

curl -sSI https://mcp.buywhere.ai/mcp
-> HTTP/2 200
-> server: railway-hikari
-> x-powered-by: Express

curl -sSI https://api.buywhere.ai/v1/products/search?q=laptop
-> HTTP/2 401
-> server: railway-hikari
-> x-powered-by: Express
```

Those probes do not prove identical business responses, but they do show both MCP hostnames currently terminate on the same public service family. The codebase proof above is what establishes the canonical live path.

## Rerun blocker

Exact live rerun attempts from this heartbeat:

```text
curl -H "Authorization: Bearer $BUYWHERE_API_KEY" \
  "https://api.buywhere.ai/v1/products/search?q=laptop&country=US&region=US&limit=3"

curl -H "Authorization: Bearer $BUYWHERE_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"probe","method":"tools/call","params":{"name":"search_products","arguments":{"q":"laptop","country_code":"US","region":"US","limit":3}}}' \
  https://api.buywhere.ai/mcp
```

Returned:

```json
{"error":"rate_limit_exceeded","message":"Daily limit of 10,000 requests reached. Resets at midnight UTC.","tier":"unverified","limit":10000,"reset_at":"2026-06-10T00:00:00.000Z","upgrade_url":"https://buywhere.ai/pricing"}
```

The same happened with the enterprise fallback key:

```json
{"error":"rate_limit_exceeded","message":"Daily limit of 1,000 requests reached. Resets at midnight UTC.","tier":"enterprise","limit":1000,"reset_at":"2026-06-10T00:00:00.000Z","upgrade_url":"https://buywhere.ai/pricing"}
```

So the remaining work to republish the accepted benchmark is blocked by both missing source and quota:

1. restore or attach the actual `buy-22746-harness/` workspace, and
2. wait until `2026-06-10T00:00:00Z`, or provide a fresh key with quota remaining

## Next command after unblock

```bash
python3 buy-22746-harness/basket_harness.py
```

If the restored accepted harness still targets the legacy MCP hostname, align it to `https://api.buywhere.ai/mcp` first. The local `scripts/basket_verify_32954.py` patch is only a stopgap on the broader rerun script, not proof that the missing accepted harness is now fixed.
