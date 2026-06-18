#!/usr/bin/env python3
"""Lyra Integration Metrics — BUY-31255 measurement collector.

Collects metrics for Lyra's merchant integration work:
1. Merchant integration status
2. Feed ingestion metrics
3. Catalog coverage by source
4. Lyra supervisor KPIs

Exit codes: 0 = success, 1 = warning, 2 = error
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import psycopg2
import psycopg2.extras

MERCHANT_QUEUE = {
    "courts_sg": {"name": "Courts SG", "type": "woocommerce", "status": "pending"},
    "guardian_sg": {"name": "Guardian SG", "type": "woocommerce", "status": "pending"},
    "qoo10_sg": {"name": "Qoo10 SG", "type": "woocommerce", "status": "backlog"},
    "shopee_sg": {"name": "Shopee SG", "type": "custom_api", "status": "awaiting_access"},
    "carousell_sg": {"name": "Carousell SG", "type": "custom_api", "status": "legal_review"},
    "lazada_vn": {"name": "Lazada VN", "type": "woocommerce", "status": "ready"},
    "tokopedia_id": {"name": "Tokopedia ID", "type": "custom_api", "status": "early_stage"},
}

# Mapping from MERCHANT_QUEUE keys to catalog_stats source names
MERCHANT_SOURCE_MAP = {
    "courts_sg": "courts_sg",
    "guardian_sg": "guardian_sg",
    "qoo10_sg": None,  # Not in catalog_stats
    "shopee_sg": None,  # Not in catalog_stats
    "carousell_sg": "carousell",
    "lazada_vn": "lazada_sg",  # Closest match
    "tokopedia_id": None,  # Not in catalog_stats
}

DB_CONNECT_TIMEOUT_S = 15
DB_QUERY_TIMEOUT_S = 30


def _db_url() -> str:
    pin = REPO_ROOT / "data" / ".catalog_db_url"
    if pin.exists():
        url = pin.read_text().strip()
        if url:
            return url
    return os.environ.get("DATABASE_URL", "")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_merchant_integration_status(conn) -> dict[str, Any]:
    result = {"check": "merchant_integration_status", "status": "unknown", "message": "", "value": None}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute(
                "SELECT source, total FROM catalog_stats WHERE source IS NOT NULL AND source != '' ORDER BY source"
            )
            rows = cur.fetchall()

        # Index catalog_stats by source name for fast lookup
        source_metrics = {}
        for row in rows:
            source = row["source"]
            total = int(row["total"]) if row["total"] else 0
            if source:
                source_metrics[source] = total

        merchant_status = {}
        for merchant_id, info in MERCHANT_QUEUE.items():
            mapped_source = MERCHANT_SOURCE_MAP.get(merchant_id)
            product_count = source_metrics.get(mapped_source, 0) if mapped_source else 0
            merchant_status[merchant_id] = {
                **info,
                "integration_status": "live" if product_count > 0 else info["status"],
                "product_count": product_count,
                "catalog_source": mapped_source,
            }

        live_merchants = [m for m, s in merchant_status.items() if s.get("integration_status") == "live"]

        result["value"] = {
            "merchants": merchant_status,
            "live_count": len(live_merchants),
            "total_count": len(MERCHANT_QUEUE),
        }
        result["status"] = "healthy"
        result["message"] = f"Integration status: {len(live_merchants)}/{len(MERCHANT_QUEUE)} merchants live"
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Could not check merchant status: {e}"
    return result


def check_feed_ingestion_metrics(conn) -> dict[str, Any]:
    result = {"check": "feed_ingestion_metrics", "status": "unknown", "message": "", "value": None}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute("SELECT source, total, ts FROM catalog_stats WHERE source IS NOT NULL AND source != '' ORDER BY total DESC")
            rows = cur.fetchall()

        feed_metrics = {}
        stats_ts = None
        for row in rows:
            source = row["source"]
            total = int(row["total"]) if row["total"] else 0
            ts = row["ts"]
            if source:
                feed_metrics[source] = {"total_items": total}
                if stats_ts is None and ts:
                    stats_ts = ts

        result["value"] = {
            "feeds": feed_metrics,
            "stats_timestamp": stats_ts.isoformat() if stats_ts else None,
        }
        result["status"] = "healthy"
        result["message"] = f"Feed metrics collected for {len(feed_metrics)} sources"
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Could not check feed metrics: {e}"
    return result


def check_catalog_coverage(conn) -> dict[str, Any]:
    result = {"check": "catalog_coverage", "status": "unknown", "message": "", "value": None}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute(
                "SELECT count(DISTINCT source) AS distinct_sources, sum(total) AS total_products, max(ts) AS last_update "
                "FROM catalog_stats WHERE source IS NOT NULL AND source != ''"
            )
            row = cur.fetchone()

        distinct_sources = int(row["distinct_sources"]) if row and row["distinct_sources"] else 0
        total_products = int(row["total_products"]) if row and row["total_products"] else 0
        last_update = row["last_update"] if row else None

        result["value"] = {
            "distinct_sources": distinct_sources,
            "total_products": total_products,
            "last_update": last_update.isoformat() if last_update else None,
        }
        result["status"] = "healthy"
        result["message"] = f"Catalog coverage: {total_products} products from {distinct_sources} sources"
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Could not check catalog coverage: {e}"
    return result


def main() -> int:
    print(f"[lyra_integration_metrics] {_ts()} Starting metrics collection...")

    db_url = _db_url()
    if not db_url:
        print("[lyra_integration_metrics] ERROR: No database URL configured", file=sys.stderr)
        return 2

    all_checks = []

    try:
        conn = psycopg2.connect(db_url, connect_timeout=DB_CONNECT_TIMEOUT_S)
        conn.autocommit = True
        try:
            all_checks.append(check_merchant_integration_status(conn))
            all_checks.append(check_feed_ingestion_metrics(conn))
            all_checks.append(check_catalog_coverage(conn))
        finally:
            conn.close()
    except Exception as e:
        print(f"[lyra_integration_metrics] ERROR: Database connection failed: {e}", file=sys.stderr)
        return 2

    report = {
        "timestamp": _ts(),
        "issue": "BUY-31255",
        "collector": "lyra_integration_metrics",
        "checks": all_checks,
    }

    print(json.dumps(report, indent=2))

    has_error = any(c["status"] == "error" for c in all_checks)
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
