#!/usr/bin/env python3
"""Database performance monitor for Rex's infrastructure team."""

import os
import time
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

# Database connection - try to get from environment or use default
DB_URL = os.environ.get("DATABASE_URL", "postgresql://buywhere_ingest:MommMnA7BUR3yo6qkPDO0vhxoOh6IQee@maglev.proxy.rlwy.net:31310/railway?sslmode=require")

def test_db_connection():
    """Test basic database connection and timing."""
    print(f"[{datetime.now().isoformat()}] Testing database connection...")

    try:
        start_time = time.time()
        conn = psycopg2.connect(DB_URL)
        conn_time = time.time() - start_time

        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()

        cur.close()
        conn.close()

        print(f"Connection successful in {conn_time:.3f}s")
        return True, conn_time

    except Exception as e:
        print(f"Connection failed: {e}")
        return False, 0

def check_active_queries():
    """Check for active/long-running queries."""
    print(f"[{datetime.now().isoformat()}] Checking active queries...")

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # Get active queries
        cur.execute("""
            SELECT
                pid,
                now() - pg_stat_activity.query_start AS duration,
                query,
                state
            FROM pg_stat_activity
            WHERE state = 'active'
            AND query NOT LIKE '%pg_stat_activity%'
            ORDER BY duration DESC
            LIMIT 10
        """)

        queries = cur.fetchall()
        if queries:
            print("Active queries:")
            for pid, duration, query, state in queries:
                print(f"  PID {pid}: {duration} - {query[:100]}...")
        else:
            print("No active queries found")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error checking queries: {e}")

def check_table_stats():
    """Check table statistics and vacuum status."""
    print(f"[{datetime.now().isoformat()}] Checking table statistics...")

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # Check products table stats
        cur.execute("""
            SELECT
                schemaname,
                tablename,
                n_tup_ins,
                n_tup_upd,
                n_tup_del,
                n_live_tup,
                n_dead_tup,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE tablename = 'products'
        """)

        stats = cur.fetchone()
        if stats:
            print("Products table stats:")
            print(f"  Inserts: {stats[2]}, Updates: {stats[3]}, Deletes: {stats[4]}")
            print(f"  Live tuples: {stats[5]}, Dead tuples: {stats[6]}")
            print(f"  Last vacuum: {stats[7]}")
            print(f"  Last autovacuum: {stats[8]}")
            print(f"  Last analyze: {stats[9]}")
            print(f"  Last autoanalyze: {stats[10]}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error checking table stats: {e}")

def main():
    """Main monitoring function."""
    print("=" * 60)
    print("DATABASE PERFORMANCE MONITOR")
    print("=" * 60)

    # Test connection
    success, conn_time = test_db_connection()

    if success:
        # Check various performance metrics
        check_active_queries()
        check_table_stats()

        print(f"\nSummary: Connection OK ({conn_time:.3f}s)")
    else:
        print("Summary: Connection FAILED - Database may be down or unreachable")

if __name__ == "__main__":
    main()