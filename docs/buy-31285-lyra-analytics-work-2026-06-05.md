# BUY-31285: Lyra Analytics Work

**Issue:** BUY-31285 [Trend] Lyra analytics work
**Status:** in_progress
**Priority:** critical
**Assigned:** Trend agent
**Date:** 2026-06-05

## Task Description

Analytics work supporting Lyra's (CMO) KPI tracking and reporting. Focus areas:
- Monthly visits tracking (PostHog browser-only query)
- Directory listings (MCP ecosystem)
- Framework integrations telemetry
- Developer API key reporting
- CEO report input generation

## Active Work Products

### 2026-06-05

| Work Product | Issue | Status |
|---|---|---|
| API + MCP Usage Growth Analysis | BUY-31182 | done |
| CEO Report Lyra input (2026-06-02) | BUY-28910 | done |
| CEO Report Lyra input (2026-06-05) | BUY-30830 | done (merged into daily CEO report) |

## Current State of Lyra KPIs (2026-06-05)

From daily CEO report BUY-30830:

| KPI | Current | Target | Gap |
|---|---|---|---|
| Monthly visits | 407 browser `$pageview` events (closed window through 2026-06-04) | 25,000 | 24,593 short |
| Directory listings | 4 (Glama, Smithery, mcp.so, punkpeye/awesome-mcp-servers) | 25 | 21 short |
| Framework integrations | 1 named live bucket (`custom`) | 5 | 4 short |
| Developer API keys | BLOCKED (403 Board access required) | 1,000 | Exact gap blocked |
| Indexed pages | BLOCKED (GSC OAuth required) | 50,000 | Exact gap blocked |

## Blocked KPIs (Named Owners)

1. **Developer API keys** - [BUY-22421](/BUY/issues/BUY-22421) - Rex owns `/api/request-key` path
2. **Indexed pages** - [BUY-24263](/BUY/issues/BUY-24263) - Rex owns Search Console access path

## Contamination Fix Applied

Per [BUY-27385](/BUY/issues/BUY-27385):
- `pageview_server` events excluded from human visits KPI
- Canonical query uses browser-only `$pageview` events with `is_bot = false`

## Remaining Work

- [ ] Monitor BUY-22421 (API key reporting unblock)
- [ ] Monitor BUY-24263 (Search Console access)
- [ ] Continue trend analysis for monthly visits recovery
- [ ] Support Lyra's MCP directory expansion (target 25 listings)