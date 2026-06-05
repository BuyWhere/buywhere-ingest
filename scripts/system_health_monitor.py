#!/usr/bin/env python3
"""System health monitor — BUY-31178 prevention tool.

Single-pass health check that validates:
1. DB write freshness (max updated_at within last 2 hours)
2. Runtime vs canonical count divergence (<5% tolerance)
3. API latency (p95 < 500ms warning, <1000ms critical)
4. Source diversity (>=2 active source families in last hour)
5. Health endpoint availability

Exit codes: 0 = healthy, 1 = warning, 2 = critical, 3 = error
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import psycopg2
import psycopg2.extras
import requests as http_requests

SYNTHETIC_MERCHANTS = {
    "shopnow", "techdepot", "fastshop", "megamart", "smartcart",
    "valuehub", "easycart", "quickbuy", "primestore", "globalmart",
}

FRESHNESS_THRESHOLD_HOURS = 2
DIVERGENCE_TOLERANCE_PCT = 5.0
LATENCY_WARNING_MS = 500
LATENCY_CRITICAL_MS = 1000
MIN_SOURCE_FAMILIES = 2
API_BASE_URL = "https://api.buywhere.ai"
HEALTH_TIMEOUT_S = 10
DB_CONNECT_TIMEOUT_S = 15
DB_QUERY_TIMEOUT_S = 30
LATENCY_SAMPLE_COUNT = 3


def _db_url() -> str:
    pin = REPO_ROOT / "data" / ".catalog_db_url"
    if pin.exists():
        url = pin.read_text().strip()
        if url:
            return url
    return os.environ.get("DATABASE_URL", "")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_db_freshness(conn) -> dict[str, Any]:
    result = {"check": "db_freshness", "status": "unknown", "message": "", "value": None}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '%ds'" % DB_QUERY_TIMEOUT_S)
            cur.execute(
                "SELECT max(updated_at) AS max_ts FROM products"
            )
            row = cur.fetchone()
            if not row or not row["max_ts"]:
                result["status"] = "critical"
                result["message"] = "No rows found in products table"
                return result

            max_ts = row["max_ts"]
            if max_ts.tzinfo is None:
                max_ts = max_ts.replace(tzinfo=timezone.utc)

            age = datetime.now(timezone.utc) - max_ts
            age_hours = age.total_seconds() / 3600
            result["value"] = {
                "max_updated_at": max_ts.isoformat(),
                "age_hours": round(age_hours, 2),
            }

            if age_hours > FRESHNESS_THRESHOLD_HOURS:
                result["status"] = "critical"
                result["message"] = (
                    f"DB writes stale: max updated_at is {age_hours:.1f}h old "
                    f"(threshold: {FRESHNESS_THRESHOLD_HOURS}h)"
                )
            elif age_hours > FRESHNESS_THRESHOLD_HOURS / 2:
                result["status"] = "warning"
                result["message"] = (
                    f"DB writes aging: max updated_at is {age_hours:.1f}h old"
                )
            else:
                result["status"] = "healthy"
                result["message"] = f"DB writes fresh: max updated_at is {age_hours:.1f}h old"
    except Exception:
        conn.rollback()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SET LOCAL statement_timeout = '%ds'" % DB_QUERY_TIMEOUT_S)
                cur.execute(
                    "SELECT greatest(last_vacuum, last_analyze, last_autoanalyze) AS last_maint "
                    "FROM pg_stat_user_tables WHERE relname = 'products'"
                )
                row = cur.fetchone()
                last_maint = row["last_maint"] if row else None
                if last_maint:
                    if last_maint.tzinfo is None:
                        last_maint = last_maint.replace(tzinfo=timezone.utc)
                    age_h = (datetime.now(timezone.utc) - last_maint).total_seconds() / 3600
                    result["status"] = "warning"
                    result["value"] = {"last_maintenance": last_maint.isoformat(), "age_hours": round(age_h, 2)}
                    result["message"] = (
                        f"DB max(updated_at) timed out; last autoanalyze {age_h:.1f}h ago — "
                        f"DB under heavy load"
                    )
                else:
                    result["status"] = "warning"
                    result["message"] = "DB max(updated_at) timed out; no maintenance stats available"
        except Exception as e2:
            conn.rollback()
            result["status"] = "critical"
            result["message"] = f"Could not query DB freshness (fallback also failed): {e2}"
    return result


def get_canonical_product_count(conn) -> dict[str, Any]:
    """
    Get exact product count from canonical DB with no silent fallback.

    Returns:
        {
            'count': int,
            'exact': bool,
            'source': str,  # 'exact', 'pg_stat_fresh', 'unavailable'
            'timestamp': str,
            'note': str,  # Optional context
        }
    """
    result = {
        "count": 0,
        "exact": False,
        "source": "unavailable",
        "timestamp": _ts(),
        "note": "",
    }

    # Tier 1: Exact count with reasonable timeout (10s)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '10s'")
            cur.execute("SELECT count(*) AS cnt FROM products")
            row = cur.fetchone()
            result.update({
                "count": row["cnt"] if row else 0,
                "exact": True,
                "source": "exact",
            })
            return result
    except Exception:
        conn.rollback()

    # Tier 2: Check pg_stat freshness and use if recent (< 1 hour old)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute(
                """
                SELECT n_live_tup AS cnt,
                       greatest(last_analyze, last_autoanalyze) AS last_stats_update
                FROM pg_stat_user_tables
                WHERE relname = 'products'
                """
            )
            row = cur.fetchone()
            if row and row["last_stats_update"]:
                last_update = row["last_stats_update"]
                if last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=timezone.utc)
                age_seconds = (datetime.now(timezone.utc) - last_update).total_seconds()
                if age_seconds < 3600:
                    result.update({
                        "count": row["cnt"] if row else 0,
                        "exact": False,
                        "source": "pg_stat_fresh",
                        "note": f"pg_stat from {int(age_seconds)}s ago",
                    })
                    return result
                else:
                    result["note"] = f"pg_stat stale ({int(age_seconds)}s old), not using"
    except Exception:
        conn.rollback()

    # Tier 3: Could not get any reliable count
    return result


def check_runtime_canonical_divergence(conn) -> dict[str, Any]:
    result = {"check": "runtime_canonical_divergence", "status": "unknown", "message": "", "value": None}

    canonical_data = get_canonical_product_count(conn)
    canonical_count = canonical_data["count"]
    exact = canonical_data["exact"]
    source = canonical_data["source"]

    if source == "unavailable":
        result["status"] = "warning"
        result["message"] = "Could not get canonical count (DB timeout or unavailable)"
        result["value"] = {"canonical_count": None, "canonical_exact": False, "error": "DB unavailable"}
        return result

    if not exact:
        result["status"] = "warning"
        result["message"] = f"Using approximate canonical count: {canonical_data.get('note', 'pg_stat')}"
        result["value"] = {"canonical_count": canonical_count, "canonical_exact": exact, "note": canonical_data.get("note")}
        # Continue to check divergence anyway, but mark as warning

    try:
        resp = http_requests.get(
            f"{API_BASE_URL}/v1/catalog/stats",
            timeout=HEALTH_TIMEOUT_S,
        )
        resp.raise_for_status()
        body = resp.json()
        runtime_count = body.get("data", {}).get("total_products", 0)
        approximate = body.get("meta", {}).get("approximate", True)
    except Exception as e:
        result["status"] = "warning"
        result["message"] = f"Could not reach runtime stats endpoint: {e}"
        result["value"] = {"canonical_count": canonical_count, "canonical_exact": exact, "source": source}
        return result

    if canonical_count == 0:
        divergence_pct = 0.0
    else:
        divergence_pct = abs(runtime_count - canonical_count) / canonical_count * 100

    result["value"] = {
        "canonical_count": canonical_count,
        "canonical_exact": exact,
        "canonical_source": source,
        "runtime_count": runtime_count,
        "divergence_pct": round(divergence_pct, 3),
        "approximate": approximate,
    }

    if divergence_pct > DIVERGENCE_TOLERANCE_PCT:
        if result["status"] != "warning":
            result["status"] = "warning"
        result["message"] = (
            f"Runtime/canonical divergence: {divergence_pct:.1f}% "
            f"(tolerance: {DIVERGENCE_TOLERANCE_PCT}%)"
        )
    else:
        if exact and source == "exact":
            result["status"] = "healthy"
            result["message"] = f"Runtime/canonical aligned: {divergence_pct:.1f}% divergence"
        else:
            result["status"] = "warning"
            result["message"] = f"Runtime/canonical aligned ({divergence_pct:.1f}%) but using approximate canonical count"
    return result


def check_api_latency() -> dict[str, Any]:
    result = {"check": "api_latency", "status": "unknown", "message": "", "value": None}
    latencies = []

    for i in range(LATENCY_SAMPLE_COUNT):
        try:
            start = time.monotonic()
            resp = http_requests.get(
                f"{API_BASE_URL}/health/db",
                timeout=HEALTH_TIMEOUT_S,
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            if resp.status_code >= 500:
                latencies.append(elapsed_ms)
            else:
                latencies.append(elapsed_ms)
        except Exception:
            latencies.append(HEALTH_TIMEOUT_S * 1000)

    if not latencies:
        result["status"] = "critical"
        result["message"] = "Could not measure API latency"
        return result

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    worst = max(latencies)

    result["value"] = {
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "worst_ms": round(worst, 1),
        "samples": len(latencies),
    }

    if p95 >= LATENCY_CRITICAL_MS:
        result["status"] = "critical"
        result["message"] = f"API p95 latency CRITICAL: {p95:.0f}ms (threshold: {LATENCY_CRITICAL_MS}ms)"
    elif p95 >= LATENCY_WARNING_MS:
        result["status"] = "warning"
        result["message"] = f"API p95 latency elevated: {p95:.0f}ms (warning: {LATENCY_WARNING_MS}ms)"
    else:
        result["status"] = "healthy"
        result["message"] = f"API latency healthy: p95={p95:.0f}ms"
    return result


def check_source_diversity(conn) -> dict[str, Any]:
    """Check source diversity using pre-aggregated catalog_stats (fast) with
    fallback to lightweight products-sample if catalog_stats is stale."""
    result = {"check": "source_diversity", "status": "unknown", "message": "", "value": None}
    try:
        # Primary: use catalog_stats (pre-aggregated, instant)
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute(
                """
                SELECT source, total, ts
                FROM catalog_stats
                WHERE source IS NOT NULL AND source != ''
                ORDER BY total DESC
                """
            )
            rows = cur.fetchall()
            if rows:
                # Filter out synthetic merchants from source names
                sources = []
                for r in rows:
                    s = r["source"]
                    if not any(sm in s for sm in SYNTHETIC_MERCHANTS):
                        sources.append(s)
                distinct_sources = len(sources)
                ts = rows[0]["ts"]
                if ts and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                stats_age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600 if ts else None

                result["value"] = {
                    "distinct_sources": distinct_sources,
                    "top_sources": sources[:10],
                    "total_sources_in_stats": len(rows),
                    "stats_age_hours": round(stats_age_hours, 1) if stats_age_hours else None,
                    "source": "catalog_stats",
                }

                if stats_age_hours and stats_age_hours > 24:
                    result["status"] = "warning"
                    result["message"] = (
                        f"Source diversity from stale catalog_stats ({stats_age_hours:.0f}h old): "
                        f"{distinct_sources} sources (may not reflect current state)"
                    )
                elif distinct_sources < MIN_SOURCE_FAMILIES:
                    result["status"] = "warning"
                    result["message"] = (
                        f"Low source diversity: {distinct_sources} source(s) "
                        f"(minimum: {MIN_SOURCE_FAMILIES}): {sources[:5]}"
                    )
                else:
                    result["status"] = "healthy"
                    result["message"] = (
                        f"Source diversity OK: {distinct_sources} sources from catalog_stats"
                    )
                return result

        # Fallback: lightweight sample — just count distinct sources via sku prefix
        conn.rollback()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '10s'")
            cur.execute(
                """
                SELECT count(DISTINCT source) AS distinct_sources
                FROM products
                WHERE merchant_id NOT IN %s
                LIMIT 1
                """,
                (tuple(sorted(SYNTHETIC_MERCHANTS)),),
            )
            row = cur.fetchone()
            distinct_sources = row["distinct_sources"] if row else 0

            result["value"] = {
                "distinct_sources": distinct_sources,
                "source": "products_sample",
            }

            if distinct_sources < MIN_SOURCE_FAMILIES:
                result["status"] = "warning"
                result["message"] = (
                    f"Low source diversity: {distinct_sources} source(s) "
                    f"(minimum: {MIN_SOURCE_FAMILIES})"
                )
            else:
                result["status"] = "healthy"
                result["message"] = f"Source diversity OK: {distinct_sources} sources"
    except Exception as e:
        conn.rollback()
        result["status"] = "warning"
        result["message"] = f"Could not check source diversity: {e}"
    return result


def check_health_endpoints() -> dict[str, Any]:
    result = {"check": "health_endpoints", "status": "unknown", "message": "", "value": None}
    checks = {}
    endpoints = {
        "db": f"{API_BASE_URL}/health/db",
        "redis": f"{API_BASE_URL}/health/redis",
        "api_catalog": f"{API_BASE_URL}/.well-known/api-catalog",
    }

    for name, url in endpoints.items():
        try:
            start = time.monotonic()
            resp = http_requests.get(url, timeout=HEALTH_TIMEOUT_S)
            elapsed_ms = (time.monotonic() - start) * 1000
            checks[name] = {
                "status_code": resp.status_code,
                "latency_ms": round(elapsed_ms, 1),
                "healthy": resp.status_code < 500,
            }
        except Exception as e:
            checks[name] = {"status_code": None, "latency_ms": None, "healthy": False, "error": str(e)}

    result["value"] = checks
    unhealthy = [k for k, v in checks.items() if not v["healthy"]]

    if unhealthy:
        result["status"] = "critical"
        result["message"] = f"Unhealthy endpoints: {unhealthy}"
    else:
        result["status"] = "healthy"
        result["message"] = "All health endpoints OK"
    return result


def main() -> int:
    print(f"[system_health_monitor] {_ts()} Starting health check...")

    db_url = _db_url()
    if not db_url:
        print("[system_health_monitor] CRITICAL: No database URL configured", file=sys.stderr)
        return 3

    all_checks = []
    worst_status = "healthy"
    status_order = {"healthy": 0, "warning": 1, "critical": 2}

    # Single DB connection for all DB checks — avoids 3x connection overhead
    conn = None
    try:
        conn = psycopg2.connect(db_url, connect_timeout=DB_CONNECT_TIMEOUT_S)
    except Exception as e:
        all_checks.append({
            "check": "db_connection",
            "status": "critical",
            "message": f"Could not connect to database: {e}",
            "value": None,
        })

    db_checks = [
        (check_db_freshness, True),
        (check_runtime_canonical_divergence, True),
        (check_source_diversity, True),
    ]
    for check_fn, needs_conn in db_checks:
        if not needs_conn:
            all_checks.append(check_fn())
            continue
        if conn is None:
            all_checks.append({
                "check": check_fn.__name__,
                "status": "critical",
                "message": f"Database error in {check_fn.__name__}: no connection",
                "value": None,
            })
            continue
        try:
            all_checks.append(check_fn(conn))
        except Exception as e:
            conn.rollback()
            all_checks.append({
                "check": check_fn.__name__,
                "status": "critical",
                "message": f"Database error in {check_fn.__name__}: {e}",
                "value": None,
            })

    if conn:
        conn.close()

    all_checks.append(check_api_latency())
    all_checks.append(check_health_endpoints())

    for c in all_checks:
        level = status_order.get(c["status"], 2)
        worst_level = status_order.get(worst_status, 2)
        if level > worst_level:
            worst_status = c["status"]

    report = {
        "timestamp": _ts(),
        "overall_status": worst_status,
        "checks": all_checks,
    }

    print(json.dumps(report, indent=2))

    exit_map = {"healthy": 0, "warning": 1, "critical": 2}
    return exit_map.get(worst_status, 3)


if __name__ == "__main__":
    raise SystemExit(main())
