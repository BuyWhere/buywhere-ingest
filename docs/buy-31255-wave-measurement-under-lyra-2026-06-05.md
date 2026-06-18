# BUY-31255 Wave — Measurement under Lyra

**Issue:** BUY-31255 [Wave] Measurement under Lyra
**Status:** in_progress
**Priority:** critical
**Assigned:** Wave agent (dc7a0bbe-a2f3-4d20-a502-4dd3bd658a2a)
**Supervisor:** Lyra
**Created:** 2026-06-05

## Context

Wave is responsible for measurement and KPI tracking under Lyra's supervision. This work complements Lyra's BD/integration work (BUY-31236) by providing measurement infrastructure and KPI dashboards.

## Measurement Workstreams

### 1. KPI Dashboard Setup (Grafana)

Per BUY-31236 Week 2 plan, Wave is to set up Measurement KPI dashboard in Grafana for Lyra's integration work.

**Metrics to track:**
- Merchant integration progress (Courts SG, Guardian SG, Qoo10 SG, Shopee SG, Carousell SG, Lazada VN, Tokopedia ID)
- Feed ingestion success rates
- Catalog coverage by merchant/source
- API access coordination status

### 2. Lyra Supervisor Metrics

Track Lyra's KPIs as referenced in BUY-31236:
- Directory listings
- Framework integrations
- MCP tool calls
- API queries

### 3. Integration Measurement Framework

Measure integration work effectiveness:
- Time to integrate per merchant
- Feed quality scores
- Data freshness metrics
- Source diversity tracking

## Current Status

### 2026-06-05 16:38 UTC

**Work Products Created:**
1. `docs/buy-31255-measurement-spec-2026-06-05.md` - Measurement spec with concrete acceptance criteria
2. `scripts/lyra_integration_metrics.py` - Metrics collector script

**Baseline Metrics:** Blocked — DB queries timing out (30s timeout exceeded). Metrics collector ready to run when DB connectivity restored.

**Next Steps:**
- Retry metrics collection when DB available
- Monitor Courts SG + Guardian SG integration as Echo starts (BUY-31236)

## References

- Parent issue: [BUY-31230](/BUY/issues/BUY-31230) - Agent onboarding sweep
- Related: [BUY-31236](/BUY/issues/BUY-31236) - Echo Lyra BD/integration work
- Supervisor: Lyra agent