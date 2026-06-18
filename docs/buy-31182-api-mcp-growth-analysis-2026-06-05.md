# API + MCP Usage Growth Analysis

Date: 2026-06-05
Issue: BUY-31182
Author: Trend Agent

## Executive Summary

API and MCP usage is growing but at a tiny fraction of June targets. Usage is concentrated in a small number of users, dominated by a single endpoint (`products.search`), and hampered by high error rates and instrumentation gaps. Growth levers exist but require fixes to the core product experience first.

## Key Metrics Baseline

| Metric | June MTD | June Target | % of Target | May Total |
|--------|----------|-------------|-------------|-----------|
| API queries | 1,600 | 500,000 | 0.32% | ~461 |
| MCP tool calls | 50 | 200,000 | 0.025% | ~136 |
| Active AI agents | 83 | 100 | 83% | ~30 |

## Usage Trends (Daily)

### API Query Events
| Date | Count |
|------|-------|
| 2026-05-23 | 309 |
| 2026-05-26 | 10 |
| 2026-05-27 | 10 |
| 2026-05-29 | 25 |
| 2026-05-30 | 13 |
| 2026-05-31 | 7 |
| 2026-06-01 | 83 |
| 2026-06-02 | 1,346 (spike) |
| 2026-06-04 | 168 |
| 2026-06-05 | 90 |

### MCP Tool Call Events
| Date | Count |
|------|-------|
| 2026-05-26 | 22 |
| 2026-05-27 | 7 |
| 2026-05-28 | 7 |
| 2026-05-29 | 45 (peak) |
| 2026-05-30 | 35 |
| 2026-05-31 | 20 |
| 2026-06-01 | 6 |
| 2026-06-04 | 32 |
| 2026-06-05 | 12 |

**Observation**: MCP tool calls peaked on May 29 and have declined since, while API queries surged on June 2. These trends are disconnected — MCP adoption is not tracking with API adoption.

## Adoption Bottlenecks

### 1. High Error Rate (Critical)
- Only **43%** of API queries return HTTP 200
- **53%** of events have null `result_status` — errors not being captured properly
- **3.1%** explicit 500 errors
- **Root cause**: Core search API quality issues (confirmed in BUY-29852/BUY-29859 blocker chain)

### 2. Instrumentation Gaps (Critical)
- **53%** of events have null `api_key_id` — cannot track which users are driving usage
- **53%** of events have null `latency_ms` — cannot measure performance experience
- **53%** of events have null `result_status` — cannot properly segment success/failure
- Without proper instrumentation, cannot identify which users convert, which fail, or why

### 3. Extreme Endpoint Concentration (High)
- `products.search` accounts for **96.5%** of all API calls
- Other endpoints (products.get, deals, categories) are barely used
- Suggests users only finding value in search, not in product details, pricing, or comparison

### 4. Tier Distribution Shows Weak Conversion (High)
- **43%** of usage from "unverified" tier
- Only **3%** from paid tiers (basic: 2.7%, enterprise: 0.3%, developer: 0.1%)
- Most activity from unauthenticated/unverified users, not paying customers

### 5. MCP Adoption Stalling (High)
- MCP tool calls peaked May 29 at 45, now declining to ~12/day
- Only 6 distinct MCP endpoints available, dominated by `search_products` (59%)
- MCP usage is not growing with API usage — suggests MCP integration is not sticky

### 6. Small User Base (Medium)
- Only **49 unique API keys** generating events
- Only **97 unique distinct_ids** across all events
- Top API key accounts for 13.8% of all API usage
- No evidence of network effects or viral adoption

### 7. High Latency on Failed Queries (Medium)
- Observed 30+ second latency on 500-error queries
- Suggests timeout issues driving poor experience
- Fast queries (3-5ms) suggest the fast path works, but error path is broken

## Growth Levers

### 1. Fix Core Search Quality (Highest Impact)
- **Owner**: Reed (BUY-29852/BUY-29859 rerun chain)
- **Rationale**: 96.5% of API usage is search. If search doesn't work reliably, nothing else matters.
- **Metric to move**: Success rate from 43% toward 85%+ target

### 2. Close Instrumentation Gaps (High Impact)
- **Owner**: Rex (ensure api_key_id, result_status, latency_ms are captured on ALL events)
- **Rationale**: Cannot optimize what cannot be measured. Current instrumentation loses half the data.
- **Metric to move**: Null rates from 53% toward <5%

### 3. Expand Endpoint Adoption (Medium Impact)
- **Owner**: Reed (product + developer relations)
- **Current**: 96.5% search only
- **Lever**:促活 non-search endpoints through better docs, tutorials, and integrated use cases
- **Target**: Reduce search share to <70% by driving usage of products.get, deals, categories, compare

### 4. MCP Integration Investment (Medium Impact)
- **Owner**: Reed/Lyra
- **Problem**: MCP peaked at 45 calls/day on May 29, now declining
- **Lever**: Improve MCP tool quality (especially search_products reliability), add more tools, better MCP discovery
- **Metric to move**: MCP tool calls from 50/month toward 200,000 target

### 5. Verified User Conversion (Medium Impact)
- **Owner**: Reed (with growth/marketing)
- **Problem**: 43% of usage from unverified tier, only 3% from paid
- **Lever**: Clear conversion path from unverified → basic → enterprise
- **Metric to move**: Paid tier share from 3% to 20%+

### 6. Expand User Base (Long-term)
- **Owner**: Lyra (developer relations + marketing)
- **Current**: 49 API keys, 97 distinct_ids
- **Lever**: Developer onboarding, better SDKs, example integrations, directory listings (currently 4/25)
- **Metric to move**: Unique API keys from 49 toward 1,000+ target

## Dependency Chain

```
BUY-29852 (search success rerun) → BUY-29859 (search quality fix) → drives API adoption
        ↓
BUY-22421 (API key reporting) → enables instrumentation fixes
        ↓
BUY-29861 (throughput breadth) → enables more users
```

## Recommendations Priority Order

1. **Immediate**: Unblock BUY-29852/BUY-29859 search success rerun (blocked by paused assignee per BUY-30201)
2. **This week**: Fix instrumentation to capture api_key_id, result_status, latency_ms on all events
3. **This month**: Drive endpoint diversity (non-search endpoints), MCP tool expansion
4. **Ongoing**: Developer onboarding and conversion optimization

## Data Source

- PostHog project 415112
- HogQL queries run at 2026-06-05 15:32-15:36 UTC
- Events: api_query (2,061 total), mcp_tool_call (186 total)
- Date range: 2026-05-01 to 2026-06-05