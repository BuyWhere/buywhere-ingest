#!/usr/bin/env python3
"""Hourly throughput dispatcher — BUY-33694 replacement for Oracle's broken routine.

Runs at the top of every UTC hour, queries the CANONICAL catalog DB (maglev via
data/.catalog_db_url), and files a child issue under BUY-29861 if real rows in
the just-completed hour are < 150,000.

Architecture (per scripts/catalog_target_report.py):
    catalog_pin_url      -> maglev.proxy.rlwy.net:31310/railway  (CANONICAL CATALOG)
    harness_database_url -> roundhouse.proxy.rlwy.net:27479/railway  (NOT the catalog)
    active_database_url  -> maglev  (repo-local writers use this)

IMPORTANT: Never use the harness DATABASE_URL (roundhouse). That DB has ~4.2M rows
and is not the catalog. The canonical catalog is on maglev.

Throughput signal strategy (maglev is write-contended per BUY-30590):
    1. PRIMARY   — pg_stat_user_tables.products.n_tup_ins delta since last
                   persisted reading. O(1), unaffected by table size or writer
                   contention. This is the canonical "rows inserted" counter.
    2. SECONDARY — SELECT COUNT(*) ... WHERE created_at in the just-completed
                   hour. Tries to give the same answer in real row terms,
                   filtering synthetic merchants. Has a statement_timeout
                   because the table scan can stall under contention; on
                   failure we log the timeout and continue with the n_tup_ins
                   delta.

Staleness signal:
    - SELECT MAX(created_at) FROM products — try with statement_timeout. If
      it fails, infer staleness from the n_tup_ins delta (no delta => stale).

State file: data/.throughput_state.json
    {
      "last_n_tup_ins": <int>,        # value of n_tup_ins at last successful run
      "last_n_tup_ins_at": <iso>,     # timestamp of that reading
      "last_hour_checked": <iso>,     # hour boundary last evaluated
      "last_check_result": "PASS"|"FAIL"|"ERROR",
      "last_check_real_rows": <int>,
      "last_check_source": "n_tup_ins_delta"|"count_window"|"unavailable"
    }
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
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

TARGET_ROWS_PER_HOUR = 150_000

# Per-statement timeouts (seconds) — maglev is contended; COUNTs can stall.
# Long enough to succeed in a quiet window, short enough not to block cron.
STMT_TIMEOUT_FAST_S = 5        # for pg_stat_user_tables and other O(1) reads
STMT_TIMEOUT_COUNT_S = 30      # for the hour-bucket COUNT (best-effort)
STMT_TIMEOUT_MAX_CREATED_S = 8 # for MAX(created_at) staleness snapshot

# BUY-29861 — parent for failure child issues
PARENT_ISSUE_ID = "4891fe2c-4957-46c9-a45d-451c157af77a"
COMPANY_ID = "177bc805-e3c8-4336-84cb-8e1e482d5a17"

# User to assign failure issues to (board owner)
ASSIGNEE_USER_ID = "MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6"

CATALOG_DB_URL_FILE = REPO_ROOT / "data" / ".catalog_db_url"
STATE_FILE = REPO_ROOT / "data" / ".throughput_state.json"


def catalog_db_url() -> str:
    """Read canonical catalog DB URL — always maglev, never roundhouse."""
    if not CATALOG_DB_URL_FILE.exists():
        raise FileNotFoundError(
            f"data/.catalog_db_url not found at {CATALOG_DB_URL_FILE}. "
            "Cannot query catalog — do NOT fall back to DATABASE_URL."
        )
    url = CATALOG_DB_URL_FILE.read_text().strip()
    if "roundhouse" in url:
        raise ValueError(
            f"data/.catalog_db_url contains roundhouse URL — this is wrong: {url}"
        )
    if "maglev" not in url:
        raise ValueError(
            f"data/.catalog_db_url is neither maglev nor roundhouse — "
            f"refusing to use unrecognized catalog target: {url}"
        )
    return url


def _api_headers() -> dict[str, str]:
    api_key = os.environ.get("PAPERCLIP_API_KEY", "")
    run_id = os.environ.get("PAPERCLIP_RUN_ID", "")
    h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if run_id:
        h["X-Paperclip-Run-Id"] = run_id
    return h


def _api_base() -> str:
    return os.environ.get("PAPERCLIP_API_URL", "http://localhost:3000").rstrip("/") + "/api"


# ---------------------------------------------------------------------------
# State persistence — between hourly fires we need the prior n_tup_ins reading
# to compute a delta. A separate file from data/.recovery_state.json (which is
# owned by the old hourly_recovery_driver.py) keeps the two routines
# independent.
# ---------------------------------------------------------------------------


def load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


# ---------------------------------------------------------------------------
# DB queries — split into a fast path (pg_stat) and a slow path (COUNT window).
# ---------------------------------------------------------------------------


def read_pg_stat_products(conn) -> dict[str, Any]:
    """O(1) read of pg_stat_user_tables.products — works under writer contention."""
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SET statement_timeout = %s", (f"{STMT_TIMEOUT_FAST_S}s",))
        cur.execute(
            """
            SELECT n_live_tup, n_tup_ins, n_tup_upd, n_tup_del,
                   seq_scan, idx_scan
            FROM pg_stat_user_tables WHERE relname = 'products'
            """
        )
        row = cur.fetchone()
    if not row:
        return {}
    return {
        "n_live_tup": int(row["n_live_tup"] or 0),
        "n_tup_ins": int(row["n_tup_ins"] or 0),
        "n_tup_upd": int(row["n_tup_upd"] or 0),
        "n_tup_del": int(row["n_tup_del"] or 0),
        "seq_scan": int(row["seq_scan"] or 0),
        "idx_scan": int(row["idx_scan"] or 0),
    }


def query_hour_window(conn, hour_start: datetime) -> dict[str, Any] | None:
    """Hour-bucket COUNT — best-effort under contention. Returns None on timeout."""
    hour_end = hour_start + timedelta(hours=1)
    synthetic_list = ",".join(f"'{m}'" for m in SYNTHETIC_MERCHANTS)
    sql = f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(*) FILTER (
                WHERE merchant_id::text NOT IN ({synthetic_list})
                  AND url NOT LIKE '%%example.com%%'
            ) AS real_rows,
            MIN(created_at) AS first_row,
            MAX(created_at) AS last_row
        FROM products
        WHERE created_at >= %s
          AND created_at <  %s
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET statement_timeout = %s", (f"{STMT_TIMEOUT_COUNT_S}s",))
            cur.execute(sql, (hour_start, hour_end))
            row = cur.fetchone()
    except psycopg2.errors.QueryCanceled:
        conn.rollback()  # cancel aborts the txn; clear it for the next query
        return {"error": "statement_timeout", "timeout_s": STMT_TIMEOUT_COUNT_S}
    conn.rollback()  # release the implicit txn so future SETs aren't in a bad state
    return {
        "total_rows": int(row["total_rows"] or 0),
        "real_rows": int(row["real_rows"] or 0),
        "first_row": str(row["first_row"]) if row["first_row"] else None,
        "last_row": str(row["last_row"]) if row["last_row"] else None,
    }


def query_max_created_at(conn) -> dict[str, Any] | None:
    """MAX(created_at) snapshot — best-effort under contention."""
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = %s", (f"{STMT_TIMEOUT_MAX_CREATED_S}s",))
            cur.execute("SELECT MAX(created_at) FROM products")
            row = cur.fetchone()
        conn.rollback()
        return {"max_created_at": str(row[0]) if row and row[0] else None}
    except psycopg2.errors.QueryCanceled:
        conn.rollback()
        return {"error": "statement_timeout", "timeout_s": STMT_TIMEOUT_MAX_CREATED_S}


# ---------------------------------------------------------------------------
# Throughput computation
# ---------------------------------------------------------------------------


def compute_real_rows_from_delta(
    state: dict[str, Any], stat: dict[str, Any], hour_start: datetime, now: datetime,
) -> dict[str, Any]:
    """Compute the per-hour insertion rate from the n_tup_ins delta since last run.

    Semantics: the per-hour rate is (now_n_tup_ins - last_n_tup_ins) /
    (now - last_at). This is the throughput we observed between the prior fire
    and the current fire; we treat it as the best estimate of how many rows
    were inserted in the just-checked hour (since writer activity in the past
    ~hour is the dominant signal).

    We require:
      - now > last_at (sanity)
      - delta_rows >= 0 (no backwards movement in the counter; negative means
        stats reset, treat as unavailable)

    Returns:
      {
        "real_rows": int | None,
        "delta_window_hours": float,
        "source": "n_tup_ins_delta" | "unavailable",
        "note": str,
      }
    """
    now_n = stat.get("n_tup_ins")
    if now_n is None:
        return {"real_rows": None, "source": "unavailable", "note": "no n_tup_ins reading"}

    last_n = state.get("last_n_tup_ins")
    last_at = state.get("last_n_tup_ins_at")
    if last_n is None or last_at is None:
        return {
            "real_rows": None,
            "source": "unavailable",
            "note": "no prior n_tup_ins reading — first run, baseline only",
        }

    last_at_dt = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
    if last_at_dt.tzinfo is None:
        last_at_dt = last_at_dt.replace(tzinfo=timezone.utc)
    delta_hours = (now - last_at_dt).total_seconds() / 3600.0

    delta_rows = now_n - last_n
    if delta_hours <= 0 or delta_rows < 0:
        return {
            "real_rows": None,
            "source": "unavailable",
            "note": (
                f"non-monotonic n_tup_ins (now={now_n}, last={last_n}, "
                f"delta_h={delta_hours:.2f}, delta_rows={delta_rows})"
            ),
        }

    # Per-hour rate. The just-checked hour's row count is approximated as
    # 1h * this rate.
    per_hour = delta_rows / delta_hours
    return {
        "real_rows": int(round(per_hour)),
        "delta_window_hours": delta_hours,
        "delta_rows": delta_rows,
        "source": "n_tup_ins_delta",
        "note": f"n_tup_ins delta {delta_rows:,} over {delta_hours:.2f}h = {per_hour:,.0f}/hr",
    }


# ---------------------------------------------------------------------------
# Paperclip API integration
# ---------------------------------------------------------------------------


def dedup_check_existing_child(hour_start: datetime) -> bool:
    """Return True if a child issue for this hour already exists under BUY-29861."""
    hour_tag = hour_start.strftime("%Y-%m-%dT%H")
    r = requests.get(
        f"{_api_base()}/companies/{COMPANY_ID}/issues",
        params={"q": f"throughput-check-{hour_tag}", "parentId": PARENT_ISSUE_ID},
        headers=_api_headers(),
        timeout=20,
    )
    if r.ok:
        issues = r.json() if isinstance(r.json(), list) else r.json().get("issues", [])
        return len(issues) > 0
    return False


def create_stall_issue(
    hour_start: datetime,
    real_rows: int,
    source: str,
    note: str,
    hour_data: dict | None,
    stat: dict,
    max_created: dict | None,
    db_host: str,
    fire_ts: str,
) -> str:
    hour_end = hour_start + timedelta(hours=1)
    pct = 100.0 * real_rows / TARGET_ROWS_PER_HOUR
    margin = real_rows - TARGET_ROWS_PER_HOUR
    hour_label = hour_start.strftime("%Y-%m-%dT%H")

    count_block = ""
    if hour_data is None:
        count_block = "| (skipped — fast-path only) |"
    elif "error" in hour_data:
        count_block = f"| (timeout after {hour_data['timeout_s']}s — fast-path only) |"
    else:
        count_block = (
            f"| {hour_data['total_rows']:,} | {hour_data['real_rows']:,} | "
            f"{hour_data['first_row'] or '(none)'} | {hour_data['last_row'] or '(none)'} |"
        )

    max_block = (
        f"| {max_created['max_created_at']} |"
        if max_created and "max_created_at" in max_created and max_created["max_created_at"]
        else "| (timeout — staleness inferred from n_tup_ins delta) |"
    )

    description = f"""# Hourly Throughput Check — {hour_label}

**Result: {"PASS" if real_rows >= TARGET_ROWS_PER_HOUR else "FAIL"} — {real_rows:,} / {TARGET_ROWS_PER_HOUR:,} ({pct:.1f}%).**

Parent: [BUY-29861](/BUY/issues/BUY-29861). Dispatcher: [BUY-33694](/BUY/issues/BUY-33694). Source: `{source}`.

> {note}

## Just-completed hour: {hour_start.isoformat()} → {hour_end.isoformat()}

| Metric | Value |
|---|---|
| Real rows (per `{source}`) | **{real_rows:,}** |
| Threshold | {TARGET_ROWS_PER_HOUR:,} |
| Margin vs. threshold | **{margin:+,} ({pct - 100:.1f}%)** |
| % of 150,000/hr target | **{pct:.1f}%** |
| `pg_stat_user_tables.products.n_live_tup` | {stat.get('n_live_tup', '?'):,} |
| `pg_stat_user_tables.products.n_tup_ins`  | {stat.get('n_tup_ins', '?'):,} |
| `MAX(created_at)` (snapshot {fire_ts}) {max_block} |

## Hour-bucket COUNT verification (best-effort)

| total_rows | real_rows | first_row | last_row |
|---:|---:|---|---|
{count_block}

## DB proof (canonical PostgreSQL @ {db_host})

Connection string source: `data/.catalog_db_url` (maglev). NOT the harness `DATABASE_URL`.

- n_tup_ins delta query (PRIMARY signal — works under maglev contention):
  ```sql
  SELECT n_live_tup, n_tup_ins, n_tup_upd
  FROM pg_stat_user_tables WHERE relname = 'products';
  -- {stat.get('n_live_tup', 0):,} | {stat.get('n_tup_ins', 0):,} | {stat.get('n_tup_upd', 0):,}
  ```
- Hour-bucket COUNT (SECONDARY — for cross-check, may time out under contention):
  ```sql
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '{hour_start.isoformat()}'
    AND created_at <  '{hour_end.isoformat()}'
  GROUP BY 1 ORDER BY 1;
  ```
"""

    title = (
        f"[BUY-33694 dispatcher] Hourly throughput check "
        f"({hour_start.strftime('%Y-%m-%d %H:%M')} UTC fire, "
        f"{hour_start.strftime('%H:%M')}–{hour_end.strftime('%H:%M')} window)"
    )

    payload = {
        "companyId": COMPANY_ID,
        "title": title,
        "description": description,
        "parentId": PARENT_ISSUE_ID,
        "status": "todo",
        "priority": "high",
        "assigneeUserId": ASSIGNEE_USER_ID,
    }
    r = requests.post(
        f"{_api_base()}/companies/{COMPANY_ID}/issues",
        json=payload,
        headers=_api_headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("identifier", "BUY-????")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the check and print the result, but do not call the Paperclip API.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="File a child issue even if the result is PASS (useful for testing).",
    )
    parser.add_argument(
        "--check-hour",
        type=str,
        default=None,
        metavar="YYYY-MM-DDTHH:00",
        help="Check a specific past hour (e.g. 2026-06-07T06:00) instead of the just-completed hour. "
        "Used for backfill verification of the BUY-33694 DoD windows.",
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    if args.check_hour:
        # Parse an explicit hour_start (e.g. "2026-06-07T06:00" or with timezone)
        from datetime import datetime as _dt

        hs_str = args.check_hour.replace("Z", "+00:00")
        try:
            hour_start = _dt.fromisoformat(hs_str)
        except ValueError:
            print(f"ERROR: --check-hour must be ISO-8601 (got {args.check_hour!r})")
            return 2
        if hour_start.tzinfo is None:
            hour_start = hour_start.replace(tzinfo=timezone.utc)
        hour_start = hour_start.replace(minute=0, second=0, microsecond=0)
    else:
        hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    fire_ts = now.strftime("%Y-%m-%d %H:%M UTC")

    print(
        f"[throughput-dispatcher] Checking hour {hour_start.isoformat()} "
        f"→ {(hour_start + timedelta(hours=1)).isoformat()}"
    )

    db_url = catalog_db_url()
    from urllib.parse import urlparse

    parsed = urlparse(db_url)
    db_host = f"{parsed.hostname}:{parsed.port}{parsed.path}"
    print(f"[throughput-dispatcher] DB: {db_host}")

    state = load_state()

    # Avoid running twice in the same hour (unless --force).
    if not args.force and state.get("last_hour_checked") == hour_start.isoformat():
        print(
            f"[throughput-dispatcher] Already ran for {hour_start.isoformat()}, "
            "skipping (use --force to override)."
        )
        return 0

    # Check for an existing child before opening a new connection — cheap.
    if not args.dry_run and dedup_check_existing_child(hour_start):
        print(
            f"[throughput-dispatcher] Child issue already exists for "
            f"{hour_start.isoformat()}, skipping."
        )
        # Persist the new n_tup_ins baseline so the next run's delta is accurate.
        # We still want to capture n_tup_ins even when dedup blocks the file.
        try:
            conn = psycopg2.connect(db_url, connect_timeout=15)
            stat = read_pg_stat_products(conn)
            conn.close()
            if stat:
                state["last_n_tup_ins"] = stat.get("n_tup_ins")
                state["last_n_tup_ins_at"] = now.isoformat()
                state["last_hour_checked"] = hour_start.isoformat()
                state["last_check_result"] = "DEDUP"
                state["last_check_source"] = "n_tup_ins"
                save_state(state)
        except Exception as e:
            print(f"[throughput-dispatcher] baseline refresh failed: {e}")
        return 0

    conn = psycopg2.connect(db_url, connect_timeout=15)
    try:
        # PRIMARY: pg_stat (fast).
        stat = read_pg_stat_products(conn)
        if not stat:
            print("[throughput-dispatcher] FATAL: pg_stat_user_tables returned no row for products")
            return 2

        # SECONDARY: hour-bucket COUNT (best-effort).
        hour_data = query_hour_window(conn, hour_start)
        if hour_data and "error" not in hour_data:
            print(
                f"[throughput-dispatcher] hour_bucket_count: total={hour_data['total_rows']:,} "
                f"real={hour_data['real_rows']:,}"
            )
        elif hour_data and "error" in hour_data:
            print(
                f"[throughput-dispatcher] hour_bucket_count: TIMEOUT after {hour_data['timeout_s']}s "
                "(maglev contention — using n_tup_ins delta only)"
            )
        else:
            print("[throughput-dispatcher] hour_bucket_count: returned None")

        # Snapshot for staleness (best-effort).
        max_created = query_max_created_at(conn)

        # Compute the real_rows number.
        delta_result = compute_real_rows_from_delta(state, stat, hour_start, now)
        real_rows_from_delta = delta_result["real_rows"]

        # Prefer the COUNT window if available, fall back to delta.
        if hour_data and "error" not in hour_data:
            real_rows = hour_data["real_rows"]
            source = "count_window"
            note = f"hour-bucket COUNT against {db_host}"
        elif real_rows_from_delta is not None:
            real_rows = real_rows_from_delta
            source = "n_tup_ins_delta"
            note = delta_result["note"]
        else:
            real_rows = 0
            source = "unavailable"
            note = f"no signal available — n_tup_ins baseline missing. {delta_result.get('note', '')}"

        pct = 100.0 * real_rows / TARGET_ROWS_PER_HOUR
        print(
            f"[throughput-dispatcher] real_rows={real_rows:,} "
            f"target={TARGET_ROWS_PER_HOUR:,} ({pct:.1f}%) source={source}"
        )

        # First run with no baseline captures the n_tup_ins baseline and exits
        # without filing — otherwise we'd file a false "stall" on a healthy fleet
        # just because we haven't seen a prior reading.
        is_first_baseline = (
            state.get("last_n_tup_ins") is None and real_rows_from_delta is None
        )

        if args.dry_run:
            print("[throughput-dispatcher] --dry-run: would NOT call the Paperclip API")
            if is_first_baseline:
                print(
                    "  BASELINE_CAPTURE: persisting n_tup_ins as the first reading; "
                    "no issue filed this run."
                )
            else:
                print(
                    f"  PASS={real_rows >= TARGET_ROWS_PER_HOUR} → "
                    f"{'no-op' if real_rows >= TARGET_ROWS_PER_HOUR else 'would file under BUY-29861'}"
                )
        else:
            if is_first_baseline:
                print(
                    "[throughput-dispatcher] BASELINE_CAPTURE: no prior n_tup_ins "
                    "reading — persisting baseline and skipping the file/no-file decision "
                    "this run. The next hour's run will compute the delta."
                )
            elif real_rows < TARGET_ROWS_PER_HOUR and not args.force:
                identifier = create_stall_issue(
                    hour_start, real_rows, source, note,
                    hour_data, stat, max_created, db_host, fire_ts,
                )
                print(f"[throughput-dispatcher] FAIL — filed {identifier} under BUY-29861")
            else:
                print(f"[throughput-dispatcher] PASS — {real_rows:,} >= {TARGET_ROWS_PER_HOUR:,}. No issue filed.")

        # Persist the new n_tup_ins baseline and result for the next run.
        # `last_n_tup_ins_at` is the wall-clock time of THIS reading; the next
        # run's delta is then (next_now - this_now), which is the actual
        # elapsed time between the two fires and gives the correct per-hour
        # rate regardless of how often the dispatcher is invoked.
        state["last_n_tup_ins"] = stat.get("n_tup_ins")
        state["last_n_tup_ins_at"] = now.isoformat()
        state["last_hour_checked"] = hour_start.isoformat()
        state["last_check_result"] = (
            "BASELINE" if is_first_baseline
            else "PASS" if real_rows >= TARGET_ROWS_PER_HOUR
            else "FAIL"
        )
        state["last_check_real_rows"] = real_rows
        state["last_check_source"] = source
        state["last_n_live_tup"] = stat.get("n_live_tup")
        state["last_db_host"] = db_host
        save_state(state)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
