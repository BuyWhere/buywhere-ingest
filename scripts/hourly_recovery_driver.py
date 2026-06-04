#!/usr/bin/env python3
"""Hourly recovery driver for BUY-30097 — posts maglev delta comment + lane status.

Runs at the top of every UTC hour, querying canonical DB (maglev) and posting:
1. Delta SQL results (real rows vs target 150k)
2. Rolling cumulative deficit tracking
3. Lane status (child issue references)
4. Recovery completion check (3 consecutive hours ≥150k real rows + deficit cleared)
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
import requests


# Synthetic merchants to exclude from real-row count
SYNTHETIC_MERCHANTS = {
    "shopnow",
    "techdepot",
    "fastshop",
    "megamart",
    "smartcart",
    "valuehub",
    "easycart",
    "quickbuy",
    "primestore",
    "globalmart",
}

# Target rows per hour (real rows only)
TARGET_ROWS_PER_HOUR = 150_000

# Recovery tracking: cumulative deficit since 06:00 UTC 2026-06-04
RECOVERY_START_HOUR = datetime(2026, 6, 4, 6, 0, 0, tzinfo=timezone.utc)

# Issue/comment IDs
TARGET_ISSUE_ID = "0d44274d-ae2e-47fd-8f6d-a544a1395f9b"  # BUY-30097
PARENT_ISSUE_ID = "7c8d9e0f-1a2b-3c4d-5e6f-7g8h9i0j1k2l"  # BUY-29861 (placeholder)

# Child lane issues
CHILD_ISSUES = {
    "dash": "BUY-30111",  # purge
    "stock": "BUY-30112",  # confirm canonical
    "hex": "BUY-30113",  # platform ingest
}

# Recovery state file (persisted across runs)
STATE_FILE = REPO_ROOT / "data" / ".recovery_state.json"


def load_recovery_state() -> dict[str, Any]:
    """Load recovery state from persistent file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "consecutive_success_hours": 0,
        "cumulative_deficit": 0.0,
        "last_hour_checked": None,
    }


def save_recovery_state(state: dict[str, Any]) -> None:
    """Save recovery state to persistent file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def database_url() -> str:
    """Read canonical DB URL from .catalog_db_url file."""
    db_url_path = REPO_ROOT / "data" / ".catalog_db_url"
    if not db_url_path.exists():
        raise FileNotFoundError(f"Database URL file not found: {db_url_path}")
    return db_url_path.read_text().strip()


def get_postgres_conn():
    """Open a connection to the canonical catalog DB."""
    return psycopg2.connect(database_url())


def query_hourly_delta(conn, hour_start: datetime) -> dict[str, int]:
    """Query the hourly delta for real rows (excluding synthetic merchants).

    Returns: {
        "hour": "2026-06-04 14:00:00+00",
        "total_rows": 12345,
        "real_rows": 10000,
    }
    """
    # Ensure the hour_start is at the top of the hour
    hour_start_ts = hour_start.replace(minute=0, second=0, microsecond=0)
    hour_end_ts = hour_start_ts.replace(hour=hour_start_ts.hour + 1) if hour_start_ts.hour < 23 else hour_start_ts.replace(hour=0, day=hour_start_ts.day + 1)

    # SQL query: count rows created in this hour, filter out synthetic merchants
    query = """
        SELECT
            date_trunc('hour', created_at) AS hour,
            COUNT(*) AS total_rows,
            COUNT(*) FILTER (
                WHERE merchant_id NOT IN %s
                AND url NOT LIKE %s
            ) AS real_rows
        FROM products
        WHERE created_at >= %s
        AND created_at < %s
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT 1
    """

    synthetic_list = tuple(sorted(SYNTHETIC_MERCHANTS))
    url_pattern = "%example.com%"

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (synthetic_list, url_pattern, hour_start_ts, hour_end_ts))
        row = cur.fetchone()

    if not row:
        return {
            "hour": hour_start_ts.isoformat(),
            "total_rows": 0,
            "real_rows": 0,
        }

    return {
        "hour": row["hour"].isoformat() if row["hour"] else hour_start_ts.isoformat(),
        "total_rows": row["total_rows"],
        "real_rows": row["real_rows"],
    }


def compute_cumulative_deficit(
    current_real_rows: int, current_hour: datetime
) -> float:
    """Compute rolling cumulative deficit since RECOVERY_START_HOUR.

    Deficit = sum of (max(0, TARGET_ROWS - real_rows)) for each hour since start.
    """
    # For this implementation, we'll compute from the current hour backward
    # In production, this would fetch all hourly deltas since RECOVERY_START_HOUR
    # For now, assume we only have this run's data; the deficit is tracked externally
    deficit = max(0, TARGET_ROWS_PER_HOUR - current_real_rows)
    return deficit


def check_recovery_complete(
    consecutive_hours_at_target: int, cumulative_deficit: float
) -> bool:
    """Check if recovery condition is met:
    3 consecutive hours ≥150k real rows AND cumulative deficit cleared (≤0).
    """
    return consecutive_hours_at_target >= 3 and cumulative_deficit <= 0


def post_comment_to_issue(
    comment_body: str, issue_id: str = TARGET_ISSUE_ID
) -> dict[str, Any]:
    """Post a comment to the issue via Paperclip API."""
    api_base = os.environ.get("PAPERCLIP_API_URL", "http://localhost:3000")
    api_url = api_base.rstrip("/") + "/api"
    api_key = os.environ.get("PAPERCLIP_API_KEY")
    run_id = os.environ.get("PAPERCLIP_RUN_ID")

    if not api_key:
        raise ValueError("PAPERCLIP_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if run_id:
        headers["X-Paperclip-Run-Id"] = run_id

    payload = {"body": comment_body}

    response = requests.post(
        f"{api_url}/issues/{issue_id}/comments",
        json=payload,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def mark_issue_done(comment_body: str, issue_id: str = TARGET_ISSUE_ID) -> dict[str, Any]:
    """Mark an issue as done via Paperclip API."""
    api_base = os.environ.get("PAPERCLIP_API_URL", "http://localhost:3000")
    api_url = api_base.rstrip("/") + "/api"
    api_key = os.environ.get("PAPERCLIP_API_KEY")
    run_id = os.environ.get("PAPERCLIP_RUN_ID")

    if not api_key:
        raise ValueError("PAPERCLIP_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if run_id:
        headers["X-Paperclip-Run-Id"] = run_id

    payload = {"status": "done", "comment": comment_body}

    response = requests.patch(
        f"{api_url}/issues/{issue_id}",
        json=payload,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def format_recovery_comment(
    hour_data: dict[str, Any],
    cumulative_deficit: float,
    lane_status: str,
) -> str:
    """Format the hourly recovery comment."""
    hour_str = hour_data["hour"]
    total_rows = hour_data["total_rows"]
    real_rows = hour_data["real_rows"]
    target_delta = real_rows - TARGET_ROWS_PER_HOUR

    status_emoji = "✅" if real_rows >= TARGET_ROWS_PER_HOUR else "❌"

    comment = f"""{status_emoji} **Recovery Update** — {hour_str}

| Metric | Value |
| --- | --- |
| Real Rows (excl. synthetic) | {real_rows:,} |
| Target | {TARGET_ROWS_PER_HOUR:,} |
| Delta | {target_delta:+,} |
| Cumulative Deficit | {cumulative_deficit:,.0f} |

### Lane Status
{lane_status}

### SQL Query (Canonical Maglev DB-A)
```sql
SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows,
       COUNT(*) FILTER (WHERE merchant_id NOT IN ('shopnow', 'techdepot', 'fastshop',
                                                     'megamart', 'smartcart', 'valuehub',
                                                     'easycart', 'quickbuy', 'primestore',
                                                     'globalmart')) AS real_rows
FROM products
WHERE created_at >= '2026-06-04 00:00:00+00'
GROUP BY 1
ORDER BY 1;
```
"""
    return comment.strip()


def get_lane_status() -> str:
    """Get current status of child lane issues."""
    # In a real implementation, this would query the Paperclip API for child issue status
    # For now, return a static template
    return f"""
- [Dash (Purge)](/BUY/issues/BUY-30111) — deduplication & pruning
- [Stock (Confirm Canonical)](/BUY/issues/BUY-30112) — schema verification
- [Hex (Platform Ingest)](/BUY/issues/BUY-30113) — distributed ingestion
"""


def main() -> int:
    """Main entry point for hourly recovery driver."""
    print("[hourly_recovery_driver] Starting hourly recovery check...")

    # Load persistent recovery state
    recovery_state = load_recovery_state()

    # Get the current UTC hour (start of the hour)
    now = datetime.now(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    current_hour_str = current_hour.isoformat()

    # Avoid running twice in the same hour
    if recovery_state.get("last_hour_checked") == current_hour_str:
        print(f"[hourly_recovery_driver] Already ran for {current_hour_str}, skipping")
        return 0

    try:
        conn = get_postgres_conn()
        try:
            # Query hourly delta from canonical DB
            hour_data = query_hourly_delta(conn, current_hour)
            print(f"[hourly_recovery_driver] Hour data: {json.dumps(hour_data, indent=2)}")

            real_rows = hour_data["real_rows"]
            deficit_this_hour = max(0, TARGET_ROWS_PER_HOUR - real_rows)

            # Update cumulative deficit
            cumulative_deficit = recovery_state.get("cumulative_deficit", 0.0) + deficit_this_hour
            recovery_state["cumulative_deficit"] = cumulative_deficit

            # Check if this hour met target
            if real_rows >= TARGET_ROWS_PER_HOUR:
                recovery_state["consecutive_success_hours"] = recovery_state.get("consecutive_success_hours", 0) + 1
            else:
                recovery_state["consecutive_success_hours"] = 0

            # Mark this hour as checked
            recovery_state["last_hour_checked"] = current_hour_str

            print(
                f"[hourly_recovery_driver] "
                f"Real rows: {real_rows} | "
                f"Consecutive success hours: {recovery_state['consecutive_success_hours']} | "
                f"Cumulative deficit: {cumulative_deficit:.0f}"
            )

            # Build and post comment
            lane_status = get_lane_status()
            comment_body = format_recovery_comment(hour_data, cumulative_deficit, lane_status)

            print("[hourly_recovery_driver] Posting comment to issue...")
            post_comment_to_issue(comment_body)
            print("[hourly_recovery_driver] Comment posted successfully")

            # Save state before checking completion (to persist progress)
            save_recovery_state(recovery_state)

            # Check recovery completion condition
            if check_recovery_complete(
                recovery_state["consecutive_success_hours"], cumulative_deficit
            ):
                print(
                    "[hourly_recovery_driver] "
                    "Recovery condition met! "
                    "Posting proof comment and marking BUY-30097 done..."
                )
                recovery_proof = f"""
## Recovery Achieved! 🎉

**Requirement met as of {current_hour.isoformat()}:**
- ✅ 3 consecutive UTC hours each produced ≥150,000 real rows
- ✅ Cumulative deficit cleared ({cumulative_deficit:.0f} ≤ 0)

Marking this recovery tracker as complete. Parent issue [BUY-29861](/BUY/issues/BUY-29861)
now unblocked for final reconciliation.
"""
                mark_issue_done(recovery_proof)
                print("[hourly_recovery_driver] Issue marked done")
                # Clear state file on completion
                STATE_FILE.unlink(missing_ok=True)
                return 0

        finally:
            conn.close()

    except Exception as e:
        print(f"[hourly_recovery_driver] Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
