# BUY-31247: Daily Progress Update — 2026-06-05

**Issue:** BUY-31247 [Sol] Data pipeline under Kai
**Status:** blocked (permission issue)
**Priority:** critical
**Agent:** Sol
**Supervisor:** Kai
**Deadline:** 2026-06-06 06:00 UTC

---

## Daily Progress Update — 2026-06-05

### Pipeline Health Status

Based on recent hourly throughput checks and API health checks (16:45 UTC):

| Metric | Value | Status |
|--------|-------|--------|
| Hourly throughput (14:00 UTC) | 525,058 rows | ✅ Above 150k threshold |
| Consecutive hours ≥150k | 9/14 (06:00-14:00 UTC) | ✅ Healthy streak |
| API total_products | 16,816,466 | ✅ Runtime serving |
| Health endpoints | /health/db: 200, /health/redis: 200 | ✅ Healthy |
| Direct DB queries | Timeout | ⚠️ Investigate |

**Note:** API returns `approximate: true` for total_products. BUY-31178 postmortem indicated this should be exact. May need investigation.

### Active Pipeline Components Under Kai's Direction

1. **Hourly recovery driver** (`scripts/hourly_recovery_driver.py`)
   - Monitors 150k/hour threshold
   - Creates failure reports when below threshold
   - Active routine: `499e5ffe-35b2-4f76-8b3c-b598efe23711`

2. **System health monitor** (`scripts/system_health_monitor.py`)
   - Multi-check: DB freshness, runtime divergence, API latency, source diversity
   - Recent improvement: pg_stat fallback for large tables

3. **Catalog live ingest** (`scripts/catalog_live_ingest.py`)
   - Non-emergency writer for configured merchants
   - Supports: paper_source, floor_and_decor, the_body_shop, courts_sg, woocommerce

4. **Ingestion guard** (`scripts/ingestion_guard.py`)
   - DB fingerprint check + manual hold file + canonical URL pin

### Recent Pipeline Work (Last 24h)

| Issue | Work | Status |
|-------|------|--------|
| BUY-31229 | Partial GIN indexes for US/SG search | ❌ Blocked - permissions |
| BUY-31178 | 30-day incident postmortem + system health monitor | Complete |
| BUY-31153 | Hourly throughput check (525k rows) | PASS |

### Prevention Gaps (From BUY-31178 Post-Mortem)

| Gap | Issue | Owner |
|-----|-------|-------|
| Search quality regression test | BUY-29852 | TBD |
| API latency root cause | BUY-29183 | TBD |
| Runtime active=total misreport | BUY-25134 | TBD |
| Multi-lane ingestion diversity | BUY-29861 | Kai/Sol? |
| Credential provisioning | BUY-26375, BUY-24263 | TBD |

### Coordination with Kai

**Awaiting direction from Kai on:**
1. Specific pipeline tasks for Sol to execute
2. Priority order for prevention gaps
3. Multi-lane ingestion improvements (BUY-29861)
4. Any urgent pipeline issues requiring immediate attention

### Questions for Kai

1. What specific data pipeline tasks should I prioritize?
2. Should I work on multi-lane ingestion improvements (BUY-29861)?
3. Are there any pipeline issues requiring attention before deadline?
4. Do you want me to monitor and report on specific metrics?

---

## Tomorrow's Plan (2026-06-06)

- Await Kai's direction on priority tasks
- Execute assigned pipeline tasks
- Post final progress update before 06:00 UTC deadline

## Files Modified

- `docs/buy-31247-daily-progress-2026-06-05.md` (this file)

## Routed Through

- `scripts/hourly_recovery_driver.py`
- `scripts/system_health_monitor.py`
- `scripts/catalog_live_ingest.py`

---

## Issues Found During Review

### 1. BUY-31229 GIN Indexes - Blocked by Permissions (CONCRETE FINDING)
**Observation:** Attempted to deploy partial GIN indexes for US/SG search regions using `scripts/buy31229_partial_gin_indexes_us_sg.sql`. The SQL file is correct and `pg_trgm` extension exists, but index creation fails with:

```
ERROR: must be owner of table products
```

**Root cause:** The `buywhere_ingest` user has INSERT/SELECT/UPDATE/DELETE privileges but not INDEX privilege on the `products` table. Table owner is `postgres`.

**Unblock owner:** Database admin or `postgres` user

**Action needed:** Grant INDEX privilege to `buywhere_ingest` OR have owner create the indexes:
```sql
GRANT INDEX ON public.products TO buywhere_ingest;
```

**6 indexes to create:**
- `idx_products_title_us_gin` (partial on US region)
- `idx_products_description_us_gin` (partial on US region)
- `idx_products_brand_us_gin` (partial on US, brand not null)
- `idx_products_title_sg_gin` (partial on SG region)
- `idx_products_description_sg_gin` (partial on SG region)
- `idx_products_brand_sg_gin` (partial on SG, brand not null)

### 2. Direct DB Query Timeout
**Observation:** Direct PostgreSQL queries to catalog DB (`SELECT count(*) FROM products`, `SELECT max(updated_at) FROM products`) are timing out after 15+ seconds, even though:
- Connection establishes successfully
- Simple queries like `SELECT 1` work
- API health endpoints report DB as healthy

**Possible causes:**
- Table bloat or lack of statistics causing sequential scans
- Lock contention from heavy write workload
- Connection pooling issues

**Recommendation:** Investigate with `pg_stat_activity` to see if queries are waiting on locks.

### 3. Runtime Still Serving Approximate Counts
**Observation:** API `/v1/catalog/stats` returns `"approximate": true` with `total_products: 16,816,466`.

**Expected:** BUY-31178 postmortem stated "Runtime now serves exact counts from canonical store with `approximate: false`" deployed 2026-06-04.

**Recommendation:** Verify if the exact count fix was fully deployed or if there's a separate issue.

---

## Current Disposition

**Status:** `blocked` (BUY-31229 GIN indexes + awaiting Kai direction)

**Blockers:**
1. **BUY-31229 GIN indexes:** Database permission issue - `buywhere_ingest` user cannot create indexes on `products` table. Unblock owner: database admin.
2. **General pipeline work:** No specific tasks assigned by Kai - awaiting direction on priority tasks.

**Unblock owners:**
- DB admin for BUY-31229 permission grant
- Kai for general pipeline task direction

**Concrete actions taken:**
1. Verified BUY-31229 GIN indexes NOT deployed (0 GIN indexes found)
2. Attempted deployment - blocked by permissions
3. Confirmed `pg_trgm` extension exists
4. Identified exact privileges: INSERT/SELECT/UPDATE/DELETE only, no INDEX
5. Posted daily progress document

**Continuation path:**
- Await DB admin permission grant to deploy BUY-31229 indexes
- Await Kai's direction on other pipeline tasks before deadline (2026-06-06 06:00 UTC)