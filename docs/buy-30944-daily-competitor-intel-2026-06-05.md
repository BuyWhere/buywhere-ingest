# BUY-30944: Daily Competitor Intelligence Digest — 2026-06-05

Date: 2026-06-05 UTC
Issue: [BUY-30944](/BUY/issues/BUY-30944)
Parent: [BUY-7447](/BUY/issues/BUY-7447)
Status: daily digest generated

## Executive Summary

Daily monitoring of AI-agent commerce competitive landscape. Sources: GitHub (live), Product Hunt (blocked — no API token), Smithery MCP directory (blocked — API returning 404).

| Threat Level | Count |
|---|---:|
| Critical | 7 |
| High | 20 |
| Medium | 10 |
| Monitor | 0 |
| **Total** | **37** |

## API Health

| Platform | Status | Notes |
|---|---|---|
| Product Hunt | BLOCKED | `PH_API_TOKEN` env var not set |
| Smithery MCP | BLOCKED | API returned 404 — endpoint may have changed |
| GitHub | LIVE | Trending repos for AI shopping/agent keywords |

## Critical Threat Signals

The following competitors are actively building in direct competition spaces:

1. **ai-shopping-intelligence-platform** (GitHub) — AI shopping intelligence platform
2. **kapuru** (GitHub) — Friendly AI shopping buddy for Kapruka
3. **Kapruka-Genie---AI-Shopping-Agent** (GitHub) — AI Shopping agent building competition
4. **ai-shopping-agent** (GitHub) — Standalone AI shopping agent
5. **AI-Shopping-Assistant** (GitHub) — AI shopping assistant
6. **ai-shopping-curator** (GitHub) — AI shopping curator
7. **ai-shop** (GitHub) — AI shop for verio

## High Threat Signals

Additional AI shopping and agent commerce projects detected at lower star counts:

- aiogram3_shop_bot — Telegram shop bot
- AI-Automated-Billing-Shopping-Cart
- Petty — Intelligent Pet Care Platform (includes AI shopping optimization)
- Multiple other AI shopping agent experiments

## Medium Threat Signals

Projects using "ai agent", "mcp server", "product scraper" signals that bear watching:

- Various MCP server implementations
- LangChain tool integrations
- Product scraper projects

## Source Data

- Script: `scripts/competitor_intelligence.py`
- GitHub search: keywords `ai shopping`, `agent commerce`, `product search api`, `mcp server`
- Days back: 1 (GitHub)

## Recommended Actions

1. **Set `PH_API_TOKEN`** — Product Hunt is the highest-signal early-launch feed for AI commerce products
2. **Fix Smithery API endpoint** — `https://smithery.ai/api/mcp` returning 404; check current endpoint
3. **Flag Kapruka-Genie's competition** — Sri Lankan e-commerce AI agent with active development

## Related

- Parent: [BUY-7447](/BUY/issues/BUY-7447)
- AI Agent Leads cohort analysis: [docs/buy-8032-ai-agent-leads-2026-05-29.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-8032-ai-agent-leads-2026-05-29.md)