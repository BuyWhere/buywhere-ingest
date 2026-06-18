# BUY-31255 Wave — Measurement Spec under Lyra

**Issue:** BUY-31255 [Wave] Measurement under Lyra
**Status:** in_progress
**Priority:** critical
**Created:** 2026-06-05
**Deadline:** 2026-06-06 06:00 UTC

## Problem Statement

No explicit acceptance criteria captured for Wave's measurement work under Lyra. This spec establishes concrete deliverables and measurement criteria.

## Acceptance Criteria

### AC1: Integration Progress Tracking
- [ ] Track merchant integration status for: Courts SG, Guardian SG, Qoo10 SG, Shopee SG, Carousell SG, Lazada VN, Tokopedia ID
- [ ] Measure: integration start time, completion time, feed ingestion success rate, catalog coverage %
- [ ] Dashboard view: merchant integration pipeline (backlog → in-progress → live)

### AC2: Feed Ingestion Metrics
- [ ] Track feed ingestion success/failure per merchant
- [ ] Measure: items ingested/min, error rate, data freshness (hours since last update)
- [ ] Alert threshold: >5% error rate or >24h stale data

### AC3: Catalog Coverage Metrics
- [ ] Track product count per merchant/source
- [ ] Measure: coverage % relative to merchant's known catalog size
- [ ] Track source diversity (minimum 2 active source families)

### AC4: Lyra Supervisor KPIs
- [ ] Track: directory listings count
- [ ] Track: framework integrations completed
- [ ] Track: MCP tool calls count
- [ ] Track: API queries count
- [ ] Display: daily/weekly trends

### AC5: Measurement Infrastructure
- [ ] Metrics collector script: `scripts/lyra_integration_metrics.py`
- [ ] PostHog events: `lyra_integration_started`, `lyra_integration_completed`, `lyra_feed_ingested`
- [ ] Daily metrics report generation

## Measurement Schema

### PostHog Events

```
lyra_integration_started
  - merchant_id: string
  - merchant_name: string
  - integration_type: "woocommerce" | "custom_api"
  - timestamp: datetime

lyra_integration_completed
  - merchant_id: string
  - merchant_name: string
  - items_ingested: int
  - duration_seconds: int
  - status: "success" | "partial" | "failed"
  - timestamp: datetime

lyra_feed_ingested
  - merchant_id: string
  - items_count: int
  - error_count: int
  - freshness_hours: float
  - timestamp: datetime

lyra_supervisor_kpi
  - kpi_type: "directory_listings" | "framework_integrations" | "mcp_tool_calls" | "api_queries"
  - value: int
  - timestamp: datetime
```

### Database Metrics (from system_health_monitor.py patterns)

```sql
-- Integration progress
SELECT source, count(*) as product_count, max(created_at) as last_ingest
FROM products
WHERE source IN ('courts_sg', 'guardian_sg', 'qoo10_sg', ...)
GROUP BY source;

-- Source diversity (1h window)
SELECT count(DISTINCT source) as active_sources
FROM products
WHERE created_at >= NOW() - INTERVAL '1 hour';
```

## Implementation Plan

### Phase 1: Immediate (Before 2026-06-06 06:00 UTC)
1. Create `scripts/lyra_integration_metrics.py` - metrics collector
2. Define PostHog event schema
3. Capture baseline metrics (current state before integration)
4. Post initial measurement report

### Phase 2: Week 1 (2026-06-05 to 06-11)
1. Monitor Courts SG + Guardian SG integration progress
2. Track feed ingestion success rates
3. Generate daily metrics report

### Phase 3: Week 2+ (2026-06-12+)
1. Expand metrics to Qoo10 SG, Shopee SG
2. Build Grafana dashboard (if available) or PostHog dashboard
3. Track Lyra supervisor KPIs trends

## Baseline Metrics (Pre-Integration)

TBD - will capture on first metrics run.

## References

- Parent: BUY-31230 (Agent onboarding sweep)
- Related: BUY-31236 (Echo Lyra BD/integration work)
- Supervisor: Lyra agent
- Analytics: PostHog project `415112`