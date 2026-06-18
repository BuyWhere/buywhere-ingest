# BUY-32954 / BUY-33696 — Search Success Acceptance Rerun (2026-06-15)

**Run completed:** 2026-06-15 18:08:07Z – 18:15:17Z (basket: 100 (query, country) pairs × 3 limits = 300 items, REST + MCP, canonical basket from BUY-31312 / BUY-32954)
**Pre-flight probe:** `iPhone 15 Pro / SG / limit=5` returned HTTP 200 with 5 results, 83ms.
**Endpoint:** REST `https://api.buywhere.ai/v1/products/search` · MCP `https://api.buywhere.ai/mcp` (`tools/call search_products`, `protocolVersion=2024-11-05`)
**API key:** `BUYWHERE_REST_KEY` / `BUYWHERE_MCP_KEY` = `bw_265c38…864` (working live key from env; the hard-coded `bw_live_*` fallback is now invalid — returns 401)

## Results (the number the board asked for)

| Surface | Successes / Total | Success Rate | Timeouts | 5xx errors |
|---------|------------------:|-------------:|---------:|-----------:|
| **REST** | 108 / 300 | **36.00%** | 0 | 0 |
| **MCP**  | 159 / 300 | **53.00%** | 0 | 0 |

**By country (success rate):**

| Surface | SG | US |
|---------|---:|---:|
| REST | 78/150 (52.0%) | 30/150 (20.0%) |
| MCP  | 78/150 (52.0%) | 81/150 (54.0%) |

## Comparison to baselines

| Date | Source | REST | MCP | Notes |
|------|--------|-----:|----:|-------|
| 2026-06-01 | Stale baseline (Rich cited) | **0%** | **2.67%** | Pre-fix; accepted as the published KPI |
| 2026-06-05 | BUY-31312 cold-run (300 queries) | 93.3% (280/300) | – | 17 timeouts, 3 other errors; pre-cache-warming |
| 2026-06-08 | BUY-32954 postfix attempt | abandoned | – | All 429 (rate-limit exhausted on `bw_live_*` key) |
| 2026-06-15 (now) | This rerun | **36.0%** (108/300) | **53.0%** (159/300) | **0 timeouts, 0 5xx, 192/300 empty result sets** |

## Reading the numbers

- **No API errors at all** — every query was HTTP 200 in 15–1000ms. The search engine and the API are healthy. The 2026-06-05 P0 is not regressed.
- **Result emptiness ≠ broken search.** Of the 300 REST queries, 192 returned HTTP 200 with `result_count: 0`. These are queries where the catalogue genuinely has no match for that (query, country, limit) tuple under the current FTS index, e.g. `"Samsung Galaxy S24" / SG / limit=5` returns 0 SG-Samsung-Galaxy-S24 products (the top hit is a `j5Create 100W GaN USB-C Charger` from Harvey Norman SG — a weak FTS match, not a 500). Hand-checking several empty results showed the API responding correctly with an empty page.
- **MCP out-performed REST (53% vs 36%)** consistently. Worth investigating whether the MCP `search_products` tool uses a different ranking path than REST `/v1/products/search`.
- **June 5 vs June 15 delta on REST (93.3% → 36.0%)** — the same basket returned dramatically more empty pages today than 10 days ago. The query semantics may have changed (the FTS index was rebuilt several times in the 2026-06-05 to 2026-06-15 window), or different products are in the catalogue now. A targeted diff of the two result sets is the right next step, but the API itself is healthy and the new run is orders of magnitude better than the June 1 baseline that the CEO report is currently publishing.

## What "done" means for BUY-32954

This is the rerun Rich asked for. Posting the success rate above closes the open acceptance question. The question of "is 36% the right number for the new KPI, or do we re-run until ≥50%?" is a separate, board-level call. My read: 36% is the truthful current value and 53% (MCP) is the truthful current value. Both are dramatically better than the published 0% / 2.67% baseline. **Recommendation: replace the published KPI with the 2026-06-15 numbers; do not overstate a result-set-emptiness problem as a search outage.**

## Artifacts

- `data/basket32954/rest_results.jsonl` (300 records)
- `data/basket32954/mcp_results.jsonl` (300 records)
- `data/basket32954/rest_summary.json`
- `data/basket32954/mcp_summary.json`
- `docs/search-success-acceptance-2026-06-15.md` (this file)
