# BUY-31178 Post-Mortem: 30-Day Incident Analysis & Prevention

Date: 2026-06-05 UTC
Owner: Bolt (lead), Gate (support)
Scope: All incidents 2026-05-06 through 2026-06-05
30-day uptime at analysis: ~91% (target: >99.9%)

---

## Executive Summary

Over the trailing 30-day window, BuyWhere experienced **7 distinct incident categories** that drove 30-day uptime from the >99.9% target down to ~91%. The root causes cluster into three systemic gaps:

1. **No automated write-path verification** — a 4-day database write stall went undetected because no hourly sanity check existed.
2. **Single-source ingestion fragility** — 100% Shopify-lane dependence caused 6/8 hourly throughput failures in a single night.
3. **Metric surface divergence** — runtime API served approximate counts (pg_class_fallback) while canonical DB had exact counts, creating a phantom 14M-product gap and contaminated traffic KPIs.

All three gaps now have concrete prevention deployed or in progress. The 24-hour uptime has recovered to 100.000%. The 30-day number will rise as the incident window rolls off, but structural prevention must hold independently.

---

## Incident Catalog

### INC-1: Canonical Database Write Stall (P1)

| Field | Value |
|-------|-------|
| Window | 2026-05-29 06:26 UTC through 2026-06-02 21:08 UTC (~4 days) |
| Detection | Manual — shortfall report on 2026-05-30 showed 0 new rows |
| Root cause | Split database configuration: harness `DATABASE_URL` pointed at stale `roundhouse.proxy.rlwy.net:27479`; canonical pin in `data/.catalog_db_url` pointed at live `maglev.proxy.rlwy.net:31310`; no repo-local writer consumed the pinned URL |
| Impact | Zero new products written to canonical DB for ~4 days; four zero-create days on canonical (2026-05-30, 05-31, 06-01, 06-03) |
| Recovery | Emergency writer (`scripts/emergency_catalog_ingest.py`) created 2026-06-02; durable non-emergency writer (`scripts/catalog_live_ingest.py`) built same day |
| Related issues | [BUY-29199](/BUY/issues/BUY-29199), [BUY-29210](/BUY/issues/BUY-29210) |

**What failed:** No automated write-path verification existed. The ingestion pipeline silently stalled because no heartbeat checked "did rows get written in the last hour?"

**Prevention deployed:**
- `scripts/hourly_recovery_driver.py` — automated hourly check (150k real rows/hour threshold), runs via Paperclip routine every UTC hour
- `scripts/ingestion_guard.py` — control-plane DB fingerprint check + manual hold file + canonical URL pin
- `data/.catalog_db_url` — durable pinned canonical DB target, preferred over harness `DATABASE_URL`

---

### INC-2: Runtime/Canonical Metric Divergence (P1)

| Field | Value |
|-------|-------|
| Window | 2026-05-28 through 2026-06-04 (~7 days to full resolution) |
| Detection | Manual — CEO report preparation exposed 16.8M runtime vs 2.7M canonical |
| Root cause | `GET /v1/catalog/stats` used `pg_class_fallback` (approximate estimator) and collapsed `active_products = total_products`; canonical `public.products` had exact counts |
| Impact | 14,047,712 apparent product gap; board-level confusion on true catalog size; decisions made on inflated numbers |
| Recovery | BUY-27402 (code change) + BUY-27407 (deploy verification); runtime now returns `approximate: false`, `source: catalog_stats` |
| Related issues | [BUY-27392](/BUY/issues/BUY-27392), [BUY-27394](/BUY/issues/BUY-27394), [BUY-27407](/BUY/issues/BUY-27407), [BUY-25134](/BUY/issues/BUY-25134) |

**What failed:** The runtime API was designed with an approximate estimator for speed but never graduated to exact counts. No reconciliation check compared the two surfaces.

**Prevention deployed:**
- Runtime now serves exact counts from canonical store
- Executive reports explicitly cite `public.products` as the canonical source
- Remaining `active = total` misreport tracked under [BUY-25134](/BUY/issues/BUY-25134)

---

### INC-3: P0 Search Product Failure (P0)

| Field | Value |
|-------|-------|
| Window | Detected 2026-05-29 through 2026-06-01 |
| Detection | Manual — search_products MCP returned irrelevant results for ALL queries |
| Root cause | Search baseline showed 0% relevance for all queries |
| Impact | Core product promise broken; accepted search-success baseline at 0% REST / 2.67% MCP |
| Recovery | Incident chain BUY-27422 -> BUY-27418 -> BUY-24446 -> BUY-24284 -> BUY-22731 resolved |
| Related issues | [BUY-24284](/BUY/issues/BUY-24284), [BUY-29852](/BUY/issues/BUY-29852), [BUY-29859](/BUY/issues/BUY-29859) |

**What failed:** No automated search-quality regression test existed. The search function degraded to 0% without any alert firing.

**Prevention needed:**
- Automated search-quality smoke test (canonical queries with expected relevance thresholds)
- [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859) rerun chain must land to replace stale baseline

---

### INC-4: API Latency Regression (P2, ongoing)

| Field | Value |
|-------|-------|
| Window | 2026-05-29 through present (ongoing) |
| Detection | UptimeRobot response time tracking |
| Root cause | Under investigation — p95 degraded from ~500ms to 629ms (target: <100ms) |
| Impact | User-facing latency 6x above June 30 target; latency regression masks as "available" on uptime checks |
| Recovery | Not yet resolved |
| Related issues | [BUY-29183](/BUY/issues/BUY-29183), [BUY-29190](/BUY/issues/BUY-29190) |

**What failed:** Uptime monitors check availability (200 OK) but do not fail on high latency. A service returning 629ms responses is counted as "up."

**Prevention deployed:**
- UptimeRobot response time tracking provides p95 visibility in daily CEO reports
- Prevention tool (below) adds a latency threshold check that will alert when p95 exceeds 500ms

---

### INC-5: Single-Source Throughput Fragility (P1)

| Field | Value |
|-------|-------|
| Window | 2026-06-04 20:00 UTC through 2026-06-05 05:00 UTC |
| Detection | Automated — hourly_recovery_driver flagged 6/8 hours below 150k |
| Root cause | 100% Shopify-lane dependence; when Shopify throughput dropped, no auxiliary lanes (ebay_us, CC-MAIN, Google Shopping) compensated |
| Impact | 6/8 overnight hourly checks failed (worst hour: 50,350 rows, -66.4% vs target); 8 child failure issues filed |
| Recovery | Throughput recovered by 2026-06-05 13:00 UTC (8/14 consecutive hours above threshold) |
| Related issues | [BUY-29861](/BUY/issues/BUY-29861) and children BUY-30457 through BUY-30797 |

**What failed:** Ingestion breadth was not measured or enforced per hour. A beat day (5.2M creates) masked 6 intra-day failures.

**Prevention deployed:**
- Hourly throughput monitor with per-hour PASS/FAIL and automated child-issue creation
- `data/.recovery_state.json` tracks cumulative deficit and consecutive success hours
- Prevention tool (below) adds source-diversity tracking

---

### INC-6: Traffic KPI Contamination (P2)

| Field | Value |
|-------|-------|
| Window | 2026-05-25 through 2026-05-30 (reported) |
| Detection | Manual — KPI audit exposed bot contamination |
| Root cause | PostHog `pageview_server` events marked `is_bot = false` for UptimeRobot probes, crawlers, health checks, and internal tools |
| Impact | 34,713 of 35,196 reported "human" pageviews (98.6%) were bots; only 483 genuine browser pageviews |
| Recovery | Canonical browser-only query defined; CEO reports now use strict `$pageview` filter |
| Related issues | [BUY-27385](/BUY/issues/BUY-27385) |

**What failed:** Server-side event instrumentation did not classify monitoring/crawler traffic as bot traffic. No validation check compared internal traffic patterns against expected human patterns.

**Prevention deployed:**
- Canonical PostHog query filters to browser-only `$pageview` events
- CEO reports explicitly note the filter and exclude `pageview_server`
- Runtime fix (marking known monitor UAs as `is_bot = true`) still pending under Rex

---

### INC-7: Credential/Access Blockers (P2, ongoing)

| Field | Value |
|-------|-------|
| Window | 2026-05-26 through present (ongoing) |
| Detection | Manual — blocker triage showed 15/24 issues blocked |
| Root cause | Missing BrightData proxy credentials (account suspended), Cloudflare R2 tokens, Playwright system deps, Google Search Console OAuth, secrets registry access |
| Impact | IKEA SG scraping blocked; catalog growth limited to credential-available sources; exact indexed-pages and API-key KPIs unreportable |
| Recovery | Partial — some alternative sources found; core blockers persist |
| Related issues | [BUY-26375](/BUY/issues/BUY-26375), [BUY-26682](/BUY/issues/BUY-26682), [BUY-26658](/BUY/issues/BUY-26658), [BUY-26662](/BUY/issues/BUY-26662), [BUY-26670](/BUY/issues/BUY-26670), [BUY-24263](/BUY/issues/BUY-24263), [BUY-22421](/BUY/issues/BUY-22421) |

**What failed:** Blocked sources were not replaced fast enough with alternative ingestion channels. Agents continued leaning on blocked paths instead of pivoting to unblocked alternatives.

**Prevention in progress:**
- Oracle controls: mandatory blocked-source replacement with faster pivot to alternative channels
- Shopify/WooCommerce bulk discovery as fallback when API-based scraping is blocked
- Remaining blockers escalated in every CEO report

---

## Pattern Analysis

| Pattern | Incidents | Systemic Root Cause |
|---------|-----------|-------------------|
| Silent failures | INC-1, INC-2, INC-6 | No automated verification that "the thing that should be happening is happening" |
| Single-point-of-failure | INC-5, INC-7 | No fallback when primary path fails |
| Metric dishonesty | INC-2, INC-6 | Measurement surfaces diverged from reality |
| Latency blind spot | INC-4 | Uptime checks don't catch slow responses |
| Slow blocker escalation | INC-7 | Blocked issues sit for weeks without reassignment |

---

## Prevention Measures Deployed

### 1. Automated Write-Path Verification (addresses INC-1, INC-5)

- **Tool:** `scripts/hourly_recovery_driver.py`
- **What it does:** Runs every UTC hour, queries canonical DB for real row count, compares against 150k/hour threshold, posts PASS/FAIL to Paperclip issue, tracks cumulative deficit
- **Recovery trigger:** 3 consecutive hours ≥ 150k AND cumulative deficit cleared
- **State:** Active as Paperclip routine (ID: `499e5ffe-35b2-4f76-8b3c-b598efe23711`)

### 2. Ingestion Guard (addresses INC-1)

- **Tool:** `scripts/ingestion_guard.py`
- **What it does:** Before any write, verifies: (a) manual hold file not present, (b) target DB is not the Paperclip control plane (table fingerprint check), (c) canonical URL pin is used
- **State:** Integrated into all ingestion scripts

### 3. Canonical URL Pin (addresses INC-1)

- **Tool:** `data/.catalog_db_url`
- **What it does:** Durable file-based DB URL that survives harness environment changes. All ingestion scripts resolve this first, falling back to `DATABASE_URL` only if absent

### 4. Exact Count Runtime (addresses INC-2)

- **What changed:** `pg_class_fallback` retired; runtime now serves exact counts from canonical store with `approximate: false`
- **State:** Deployed and verified 2026-06-04

### 5. System Health Monitor (NEW — addresses INC-1, INC-2, INC-4, INC-5)

- **Tool:** `scripts/system_health_monitor.py`
- **What it does:** Single-pass health check that validates:
  - DB write freshness (max updated_at within last 2 hours)
  - Runtime vs canonical count divergence (<5% tolerance)
  - API latency (p95 < 500ms warning, <1000ms critical)
  - Source diversity (≥2 active source families in last hour)
  - Health endpoint availability
- **State:** Implemented in this issue; can be run as Paperclip routine

### 6. Browser-Only Traffic KPI (addresses INC-6)

- **What changed:** CEO reports now use strict PostHog `$pageview` browser events, excluding `pageview_server`
- **State:** Active since 2026-05-30

---

## Uptime Impact Timeline

| Date | 24h Uptime | 30d Uptime | Key Event |
|------|-----------|-----------|-----------|
| 2026-05-29 | — | ~95% | Write stall begins (INC-1) |
| 2026-05-30 | — | ~93% | Metric divergence discovered (INC-2); P0 search confirmed (INC-3) |
| 2026-06-01 | — | ~92% | Search fix chain progressing |
| 2026-06-02 | — | ~91.5% | Write stall recovered (INC-1 resolved) |
| 2026-06-03 | 99.971% | ~91.3% | Redis uptime slipped |
| 2026-06-04 | 99.566% | ~91.2% | Worst 24h uptime; hourly throughput failures (INC-5) |
| 2026-06-05 | 100.000% | ~91.0% | Full 24h recovery; 30d still depressed by trailing window |

**Path to >99.9% on 30-day:** If the structural prevention holds and no new P1/P0 incidents occur, the trailing 30-day window will clear the May 29-June 5 incident burst by approximately July 5. The 24-hour uptime must remain at >99.9% continuously to achieve this.

---

## Remaining Prevention Gaps

1. **Automated search-quality regression test** — no smoke test validates that search returns relevant results ([BUY-29852](/BUY/issues/BUY-29852))
2. **API latency root cause** — p95 at 629ms, root cause unidentified ([BUY-29183](/BUY/issues/BUY-29183))
3. **Runtime active=total misreport** — `active_products` still equals `total_products` on public API ([BUY-25134](/BUY/issues/BUY-25134))
4. **PostHog bot classification** — runtime must mark monitor/crawler UAs as `is_bot = true` (Rex-owned)
5. **Multi-lane ingestion** — auxiliary lanes (ebay_us, CC-MAIN, Google Shopping) needed to prevent single-source fragility ([BUY-29861](/BUY/issues/BUY-29861))
6. **Credential provisioning** — BrightData, R2, GSC OAuth, secrets registry access still blocked ([BUY-26375](/BUY/issues/BUY-26375), [BUY-24263](/BUY/issues/BUY-24263), [BUY-22421](/BUY/issues/BUY-22421))
