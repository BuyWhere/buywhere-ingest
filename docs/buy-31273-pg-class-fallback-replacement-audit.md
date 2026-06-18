# BUY-31273 pg_class_fallback Replacement — Audit & Design

**Owner:** Flux  
**Date:** 2026-06-05  
**Related:** [BUY-31273](/BUY/issues/BUY-31273), [BUY-31179](/BUY/issues/BUY-31179), [BUY-25134](/BUY/issues/BUY-25134)

## Executive Summary

The `pg_class_fallback` pattern is a workaround used when exact `count(*)` queries timeout. This audit identified all usage locations in the data workspace and designs an accurate replacement that uses reliable catalog stats without the fallback approximation.

## Audit Findings

### 1. Usage Locations in Data Workspace

**File:** `scripts/system_health_monitor.py`  
**Function:** `check_runtime_canonical_divergence()`  
**Lines:** 141-156

```python
# Current fallback pattern (lines 141-156):
try:
    cur.execute("SELECT count(*) AS cnt FROM products")
    row = cur.fetchone()
    canonical_count = row["cnt"] if row else 0
    exact = True
except Exception:
    try:
        conn.rollback()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT n_live_tup AS cnt FROM pg_stat_user_tables WHERE relname = 'products'"
            )
            row = cur.fetchone()
            canonical_count = row["cnt"] if row else 0
            exact = False
    except Exception as e2:
        # Error handling
```

### 2. Secondary Usage (Related Pattern)

**File:** `scripts/system_health_monitor.py`  
**Function:** `check_db_freshness()` (fallback within fallback)  
**Lines:** 101-129

This has a nested fallback pattern that queries `pg_stat_user_tables` when `max(updated_at)` times out, but this is acceptable as a secondary health indicator.

### 3. NOT in This Workspace

- The runtime `/v1/catalog/stats` endpoint is a **separate service** (railway.app)
- Runtime catalog drift (BUY-31179: 11.48M row gap) is being addressed by BUY-31180 (Flux) and BUY-31181 (Ops)

## Problem with Current Fallback

1. **Inaccuracy**: `pg_stat_user_tables.n_live_tup` is an estimate updated by autovacuum
2. **Race Conditions**: Stats may be stale between autovacuum runs
3. **Misleading**: Sets `exact=False` but caller may not check this flag
4. **BUY-31179 Impact**: Approximate stats contributed to catalog drift being undetected

## Accurate Replacement Design

### Principle

**Always use exact counts**. If `count(*)` times out, that's a legitimate health problem that should be surfaced as a warning/critical status, not silently degraded to an approximate value.

### Design: Three-Tier Query Strategy

1. **Tier 1: Exact count with timeout** (10s)
   - `SELECT count(*) AS cnt FROM products`
   - If successful → return exact count, `exact=true`

2. **Tier 2: Fast path using materialized stats** (5s)
   - Check if `public.catalog_stats_mv` exists and is fresh (last analyze < 1 hour)
   - Use `n_live_tup` from `pg_stat_user_tables` BUT validate freshness
   - If stats are stale → return warning, not degraded data

3. **Tier 3: Health warning only**
   - If both tiers fail, return a structured warning
   - Do NOT return approximate data as if it were real
   - Surface the timeout as a health check failure

### Key Invariant

> **No silent fallback.** If the DB is too slow to return an exact count, that's a health problem, not a reason to serve approximate data.

## Implementation Plan

### Phase 1: Update `system_health_monitor.py`

```python
def get_canonical_product_count(conn) -> dict:
    """
    Get exact product count from canonical DB.
    
    Returns:
        {
            'count': int,
            'exact': bool,
            'source': str,  # 'exact', 'pg_stat_fresh', 'timeout'
            'timestamp': str,
        }
    """
    result = {'exact': False, 'source': 'timeout', 'count': 0, 'timestamp': _ts()}
    
    # Tier 1: Exact count with reasonable timeout
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '10s'")
            cur.execute("SELECT count(*) AS cnt FROM products")
            row = cur.fetchone()
            result.update({
                'count': row['cnt'] if row else 0,
                'exact': True,
                'source': 'exact',
            })
            return result
    except Exception as e:
        conn.rollback()
    
    # Tier 2: Check pg_stat freshness and use if recent
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute("""
                SELECT n_live_tup AS cnt,
                       greatest(last_analyze, last_autoanalyze) AS last_stats_update
                FROM pg_stat_user_tables 
                WHERE relname = 'products'
            """)
            row = cur.fetchone()
            if row:
                last_update = row['last_stats_update']
                if last_update:
                    age = (datetime.now(timezone.utc) - last_update).total_seconds()
                    if age < 3600:  # Stats are fresh (< 1 hour old)
                        result.update({
                            'count': row['cnt'],
                            'exact': False,
                            'source': 'pg_stat_fresh',
                            'note': f'pg_stat from {int(age)}s ago',
                        })
                        return result
    except Exception:
        conn.rollback()
    
    # Tier 3: Could not get any count
    return result
```

### Phase 2: Update Health Check Logic

Modify `check_runtime_canonical_divergence()` to:
1. Use `get_canonical_product_count()` instead of direct fallback
2. Surface health warnings when Tier 1 fails
3. Never serve stale/frozen data from `catalog_stats` table

### Phase 3: Validation

1. Run `system_health_monitor.py` and verify:
   - Exact count is returned when DB is responsive
   - Fresh pg_stat is used when exact count times out but stats are recent
   - Health warning is raised when both fail

2. Compare against canonical DB using the verification query from BUY-31179:
   ```sql
   SELECT count(*) AS real_products FROM products;
   ```

3. Ensure no regression in BUY-31179 tracking (should continue to report ~28.30M for canonical)

## Related Work (Out of Scope for This Issue)

- **BUY-31180** (Flux): Restore runtime `/v1/catalog/stats` exact-count path
- **BUY-31181** (Ops): Grant `buywhere_ingest` UPDATE on `catalog_stats_mv`

## Success Criteria

1. ✅ `system_health_monitor.py` no longer uses silent pg_class fallback
2. ✅ Health check surfaces DB performance problems instead of masking them
3. ✅ Canonical count remains accurate for BUY-31179 tracking
4. ✅ Rex reviews and approves the implementation

## Next Steps

1. Implement the changes in `system_health_monitor.py`
2. Run validation tests
3. Document results and report to Rex
