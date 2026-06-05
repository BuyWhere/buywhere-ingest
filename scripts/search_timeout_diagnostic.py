#!/usr/bin/env python3
"""Search timeout diagnostic — BUY-31213 root cause analysis tool.

Diagnoses why the REST search endpoint (/v1/products/search) times out at 30s
on common queries like 'laptop', 'iPhone'. Runs EXPLAIN ANALYZE with multiple
query strategies to identify the cheapest execution plan.

Usage:
    python scripts/search_timeout_diagnostic.py [query] [country_code]

    python scripts/search_timeout_diagnostic.py laptop US
    python scripts/search_timeout_diagnostic.py iPhone
    python scripts/search_timeout_diagnostic.py "wireless headphones"

Findings (2026-06-05 Kai investigation):
    - Query planner chooses Seq Scan over GIN index for ALL FTS queries
    - ts_rank() forces materialization of ALL matching rows before LIMIT
    - 5.5M dead tuples bloat scans; table never manually vacuumed
    - work_mem = 4MB too small for large GIN bitmap scans
    - After ANALYZE, seq scan cached queries improved to ~260ms but
      cold queries still 5-16s

Recommended fixes:
    1. Remove ts_rank() from default search path — use GIN index order
    2. Increase work_mem to 256MB for search sessions
    3. Schedule regular VACUUM ANALYZE during low-ingestion windows
    4. Add statement_timeout = 5s with fallback to simplified query
    5. Consider read replica for search to avoid ingestion I/O contention
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import psycopg2
import psycopg2.extras

QUERY_TIMEOUT_S = 15

TEST_QUERIES = [
    ("laptop", "US"),
    ("laptop", None),
    ("iPhone", "US"),
    ("iPhone", None),
    ("headphones wireless", "SG"),
    ("running shoes", None),
]


def _db_url() -> str:
    pin = REPO_ROOT / "data" / ".catalog_db_url"
    if pin.exists():
        url = pin.read_text().strip()
        if url:
            return url
    return os.environ.get("DATABASE_URL", "")


def run_explain(cur, query: str, country: str | None, strategy: str) -> dict:
    where_parts = [
        "search_vector @@ plainto_tsquery('english', %s)",
        "is_active = true",
    ]
    params: list = [query]
    if country:
        where_parts.append("country_code = %s")
        params.append(country)

    where_clause = " AND ".join(where_parts)

    if strategy == "ts_rank":
        select = f"""SELECT id, title, country_code
            FROM products
            WHERE {where_clause}
            ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC
            LIMIT 10"""
        params.append(query)
    elif strategy == "no_rank":
        select = f"""SELECT id, title, country_code
            FROM products
            WHERE {where_clause}
            LIMIT 10"""
    elif strategy == "gin_forced":
        select = f"""SELECT id, title, country_code
            FROM products
            WHERE {where_clause}
            LIMIT 10"""
    else:
        select = f"""SELECT id, title, country_code
            FROM products
            WHERE {where_clause}
            LIMIT 10"""

    plan_lines = []
    execution_ms = None
    status = "ok"
    node_type = "unknown"
    total_cost = 0

    try:
        cur.execute("SET statement_timeout = '%ds'" % QUERY_TIMEOUT_S)
        if strategy == "gin_forced":
            cur.execute("SET enable_seqscan = off")
            cur.execute("SET enable_indexscan = off")
        else:
            cur.execute("SET enable_seqscan = on")
            cur.execute("SET enable_indexscan = on")

        cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " + select, params)
        for row in cur.fetchall():
            line = row[0]
            plan_lines.append(line)
            if "Execution Time" in line:
                execution_ms = float(line.split(":")[-1].strip().replace("ms", ""))
            if "Seq Scan" in line:
                node_type = "Seq Scan"
            elif "Bitmap Heap Scan" in line:
                node_type = "Bitmap Heap Scan"
            elif "Index Scan" in line and "GIN" not in line:
                node_type = "Index Scan (non-GIN)"
            elif "Index Scan" in line:
                node_type = "Index Scan"
            if "cost=" in line and ".." in line:
                try:
                    cost_part = line.split("cost=")[1].split(" ")[0]
                    total_cost = float(cost_part.split("..")[-1])
                except (ValueError, IndexError):
                    pass

    except psycopg2.errors.QueryCanceled:
        conn = cur.connection
        conn.rollback()
        status = "timeout"
        execution_ms = QUERY_TIMEOUT_S * 1000
    except Exception as e:
        conn = cur.connection
        conn.rollback()
        status = "error"
        execution_ms = -1

    return {
        "strategy": strategy,
        "status": status,
        "execution_ms": execution_ms,
        "node_type": node_type,
        "total_cost": total_cost,
        "plan": plan_lines[:5] if plan_lines else [],
    }


def check_table_health(cur) -> dict:
    cur.execute("""
        SELECT n_live_tup, n_dead_tup,
               last_vacuum, last_analyze, last_autoanalyze
        FROM pg_stat_user_tables WHERE relname = 'products'
    """)
    row = cur.fetchone()
    if not row:
        return {}
    return {
        "live_tuples": row[0],
        "dead_tuples": row[1],
        "last_vacuum": str(row[2]) if row[2] else "never",
        "last_analyze": str(row[3]) if row[3] else "never",
        "last_autoanalyze": str(row[4]) if row[4] else "never",
    }


def check_gin_index_stats(cur) -> list[dict]:
    cur.execute("""
        SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch,
               pg_size_pretty(pg_relation_size(indexrelid)) as size
        FROM pg_stat_user_indexes
        WHERE relname = 'products' AND indexrelname LIKE '%%search%%'
        ORDER BY idx_scan DESC
    """)
    results = []
    for row in cur.fetchall():
        results.append({
            "index": row[0],
            "scans": row[1],
            "tuples_read": row[2],
            "tuples_fetched": row[3],
            "size": row[4],
        })
    return results


def check_settings(cur) -> dict:
    settings = {}
    for setting in ["work_mem", "maintenance_work_mem", "effective_cache_size",
                     "random_page_cost", "seq_page_cost"]:
        cur.execute("SHOW %s" % setting)
        settings[setting] = cur.fetchone()[0]
    return settings


def main():
    db_url = _db_url()
    if not db_url:
        print("ERROR: No database URL configured", file=sys.stderr)
        return 1

    custom_query = sys.argv[1] if len(sys.argv) > 1 else None
    custom_country = sys.argv[2] if len(sys.argv) > 2 else None

    queries = [(custom_query, custom_country)] if custom_query else TEST_QUERIES

    print("=" * 70)
    print("SEARCH TIMEOUT DIAGNOSTIC — BUY-31213")
    print("=" * 70)

    conn = psycopg2.connect(db_url, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()

    print("\n--- Table Health ---")
    health = check_table_health(cur)
    for k, v in health.items():
        print(f"  {k}: {v}")

    print("\n--- GIN Index Stats ---")
    gin_stats = check_gin_index_stats(cur)
    for stat in gin_stats:
        print(f"  {stat['index']}: scans={stat['scans']:,} "
              f"read={stat['tuples_read']:,} fetch={stat['tuples_fetched']:,} "
              f"size={stat['size']}")

    print("\n--- PostgreSQL Settings ---")
    settings = check_settings(cur)
    for k, v in settings.items():
        print(f"  {k}: {v}")

    print("\n--- Query Benchmark ---")
    strategies = ["no_rank", "ts_rank", "gin_forced"]

    results = []
    for query, country in queries:
        country_label = country or "ALL"
        print(f"\n  Query: '{query}' ({country_label})")

        for strategy in strategies:
            result = run_explain(cur, query, country, strategy)
            result["query"] = query
            result["country"] = country_label
            results.append(result)

            status_icon = {"ok": " ", "timeout": "!", "error": "X"}.get(result["status"], "?")
            ms_str = f"{result['execution_ms']:.0f}ms" if result['execution_ms'] else "N/A"
            print(f"    [{status_icon}] {strategy:15s} {ms_str:>10s}  "
                  f"({result['node_type']}) cost={result['total_cost']:.0f}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    timeouts = [r for r in results if r["status"] == "timeout"]
    fast = [r for r in results if r["status"] == "ok" and r["execution_ms"] and r["execution_ms"] < 1000]
    slow = [r for r in results if r["status"] == "ok" and r["execution_ms"] and r["execution_ms"] >= 1000]

    print(f"  Timeouts: {len(timeouts)}")
    print(f"  Slow (>=1s): {len(slow)}")
    print(f"  Fast (<1s): {len(fast)}")

    if health.get("dead_tuples", 0) > 1_000_000:
        print(f"\n  WARNING: {health['dead_tuples']:,} dead tuples — run VACUUM ANALYZE")

    ts_rank_timeouts = [r for r in timeouts if r["strategy"] == "ts_rank"]
    if ts_rank_timeouts:
        print(f"\n  ROOT CAUSE: ts_rank() causes {len(ts_rank_timeouts)} timeouts")
        print("  FIX: Remove ts_rank() from default search path")

    gin_not_used = [r for r in results if r["status"] == "ok" and r["node_type"] != "Bitmap Heap Scan"]
    if len(gin_not_used) > len(results) // 2:
        print(f"\n  ROOT CAUSE: Query planner avoids GIN indexes ({len(gin_not_used)}/{len(results)} queries use seq/non-GIN scans)")
        print("  FIX: ANALYZE products; increase work_mem; consider query hints")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
