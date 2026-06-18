#!/usr/bin/env python3
"""Midnight-boundary n_tup_ins snapshot — BUY-39805.

Captures `n_tup_ins` (and `n_live_tup`) at the UTC midnight boundary so the
next daily CEO report can cite an exact closed-day delta without reconstructing
from bracketing hourly reads.

The dispatcher (BUY-33694) persists `last_n_tup_ins` + `last_n_tup_ins_at`
after every fire. The first fire that crosses a UTC day boundary reads:

    open   = state.last_n_tup_ins  (taken at state.last_n_tup_ins_at < 00:00:00Z of today)
    close  = current pg_stat n_tup_ins (at >= 00:00:00Z of today)
    delta  = close - open
    n_live_tup_close = current pg_stat n_live_tup

…and writes them to `data/.throughput_state.json` under `last_closed_day`
and `last_midnight_recorded_date` (so a re-fire within the same day is a no-op).

Posts a comment to the BUY-33694 parent issue thread with the boundary read
so it shows up in the daily report path. The comment is the canonical evidence
the CEO report cites; the state file is the durable record.

Idempotency: the script reads `last_midnight_recorded_date` from state and
refuses to record twice for the same UTC date. To force a re-record (e.g.,
the prior state was lost), pass `--force` and the new boundary will overwrite.

This module is the canonical manual-heartbeat path. The dispatcher
(`scripts/hourly_throughput_dispatcher.py`) calls `capture_closed_day_snapshot()`
after every successful fire as well, so once the dispatcher cron is fixed the
midnight snapshot is automatic. The standalone entry point exists so that the
manual heartbeat path (which is the live fire today, per BUY-33694 cron
broken-ness) can record the boundary without depending on the dispatcher.

State file additions (BUY-39805):
    {
      "last_midnight_recorded_date": "YYYY-MM-DD",   # UTC day already snapshotted
      "last_closed_day": {
        "date":           "YYYY-MM-DD",              # the day that just closed
        "n_tup_ins_open":  <int>,                     # last reading < 00:00:00Z
        "n_tup_ins_close": <int>,                     # first reading >= 00:00:00Z
        "delta":          <int>,                      # close - open
        "n_live_tup_close": <int>,                    # live tup at the close reading
        "open_at":  "<iso>",                          # timestamp of the open reading
        "close_at": "<iso>",                          # timestamp of the close reading
        "db_host":  "<host:port/db>",                 # canonical maglev
        "source":   "midnight_snapshot"               # provenance
      }
    }
"""

from __future__ import annotations

import argparse
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

# Match dispatcher's constants so the DB URL / state file / API are read from
# the same locations.
CATALOG_DB_URL_FILE = REPO_ROOT / "data" / ".catalog_db_url"
STATE_FILE = REPO_ROOT / "data" / ".throughput_state.json"

# BUY-33694 — dispatcher parent; comment-thread is the canonical evidence path.
DISPATCHER_PARENT_ISSUE_ID = "587621b2-70bb-4d99-a82c-94852cd14588"
DISPATCHER_PARENT_IDENTIFIER = "BUY-33694"
COMPANY_ID = "177bc805-e3c8-4336-84cb-8e1e482d5a17"

# Per-statement timeout — fast O(1) read of pg_stat_user_tables.
STMT_TIMEOUT_S = 5


def _catalog_db_url() -> str:
    """Read canonical catalog DB URL — always maglev, never roundhouse."""
    if not CATALOG_DB_URL_FILE.exists():
        raise FileNotFoundError(
            f"data/.catalog_db_url not found at {CATALOG_DB_URL_FILE}. "
            "Cannot query catalog."
        )
    url = CATALOG_DB_URL_FILE.read_text().strip()
    if "roundhouse" in url:
        raise ValueError(
            f"data/.catalog_db_url contains roundhouse URL — this is wrong: {url}"
        )
    if "maglev" not in url:
        raise ValueError(
            f"data/.catalog_db_url is neither maglev nor roundhouse: {url}"
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


def read_pg_stat_products(conn) -> dict[str, Any]:
    """O(1) read of pg_stat_user_tables.products."""
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SET statement_timeout = %s", (f"{STMT_TIMEOUT_S}s",))
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


def _midnight_utc(d: datetime) -> datetime:
    """Return the 00:00:00Z of the UTC day for the given datetime."""
    return d.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_iso_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def detect_boundary(
    state: dict[str, Any], now: datetime
) -> tuple[str | None, dict[str, Any] | None]:
    """Detect if a UTC midnight boundary was crossed since the last persisted reading.

    Returns (closed_day_date, open_reading):
      - closed_day_date: YYYY-MM-DD of the day that just closed (the day whose
        midnight has now passed), or None if no boundary was crossed.
      - open_reading: dict with at least {n_tup_ins, n_tup_ins_at, n_live_tup}
        describing the last persisted reading taken strictly before midnight
        (i.e., the last sample < 00:00:00Z). None if no usable open reading.
    """
    last_at_iso = state.get("last_n_tup_ins_at")
    last_n = state.get("last_n_tup_ins")
    if not last_at_iso or last_n is None:
        return None, None

    last_at = _parse_iso_utc(last_at_iso)
    last_midnight = _midnight_utc(last_at)
    now_midnight = _midnight_utc(now)

    if now_midnight == last_midnight:
        return None, None  # still in the same UTC day as the last reading

    if last_at >= now_midnight:
        return None, None  # last reading was already in the new day; not the
                            # first fire of the new day

    # last reading was strictly before now's midnight. The day that just
    # closed is `last_midnight.date()`.
    closed_day_date = last_midnight.date().isoformat()
    open_reading = {
        "n_tup_ins": int(last_n),
        "n_tup_ins_at": last_at.isoformat(),
        "n_live_tup": state.get("last_n_live_tup"),
    }
    return closed_day_date, open_reading


def build_closed_day_record(
    closed_day_date: str,
    open_reading: dict[str, Any],
    close_stat: dict[str, Any],
    close_at: datetime,
    db_host: str,
) -> dict[str, Any]:
    """Build the last_closed_day record from open + close readings."""
    n_open = int(open_reading["n_tup_ins"])
    n_close = int(close_stat["n_tup_ins"])
    delta = n_close - n_open
    return {
        "date": closed_day_date,
        "n_tup_ins_open": n_open,
        "n_tup_ins_close": n_close,
        "delta": delta,
        "n_live_tup_close": int(close_stat.get("n_live_tup") or 0),
        "open_at": open_reading["n_tup_ins_at"],
        "close_at": close_at.isoformat(),
        "db_host": db_host,
        "source": "midnight_snapshot",
    }


def _format_comment_body(record: dict[str, Any], fire_issue_identifier: str | None) -> str:
    delta = record["delta"]
    delta_sign = "+" if delta >= 0 else ""
    open_at = record["open_at"]
    close_at = record["close_at"]
    try:
        open_dt = _parse_iso_utc(open_at)
        close_dt = _parse_iso_utc(close_at)
        gap_h = (close_dt - open_dt).total_seconds() / 3600.0
        gap_str = f"{gap_h:.2f}h"
    except Exception:
        gap_str = "(unparseable gap)"

    provenance = (
        f" (fire {fire_issue_identifier})" if fire_issue_identifier else ""
    )

    return (
        f"**Midnight snapshot — closed day {record['date']}**{provenance}\n"
        f"\n"
        f"`n_tup_ins_open` ({open_at}) = **{record['n_tup_ins_open']:,}**\n"
        f"`n_tup_ins_close` ({close_at}) = **{record['n_tup_ins_close']:,}**\n"
        f"`delta` = **{delta_sign}{delta:,}** over {gap_str}\n"
        f"`n_live_tup_close` = **{record['n_live_tup_close']:,}**\n"
        f"`db_host` = `{record['db_host']}` (canonical maglev)\n"
        f"\n"
        f"Cited directly in the next daily CEO report under "
        f"`Daily Failure Summary` / `Incidents And Execution Path` — "
        f"no reconstruction from bracketing reads required."
    )


def post_boundary_comment(
    record: dict[str, Any], fire_issue_identifier: str | None
) -> str | None:
    """Post the boundary read to the BUY-33694 comment thread.

    Returns the comment id on success, or None on failure (the function logs
    but never raises — comment posting is best-effort evidence; the state file
    is the durable record).
    """
    body = _format_comment_body(record, fire_issue_identifier)
    payload = {"body": body}
    try:
        r = requests.post(
            f"{_api_base()}/issues/{DISPATCHER_PARENT_ISSUE_ID}/comments",
            json=payload,
            headers=_api_headers(),
            timeout=30,
        )
    except requests.RequestException as exc:
        print(
            f"[midnight-snapshot] WARN: Paperclip API call failed "
            f"({exc.__class__.__name__}: {exc}); state written, comment skipped"
        )
        return None
    if not r.ok:
        print(
            f"[midnight-snapshot] WARN: Paperclip API returned {r.status_code} "
            f"for comment on {DISPATCHER_PARENT_IDENTIFIER}; body: {r.text[:300]}"
        )
        return None
    try:
        body_json = r.json()
    except json.JSONDecodeError:
        return None
    return body_json.get("id")


def capture_closed_day_snapshot(
    *,
    now: datetime | None = None,
    force: bool = False,
    fire_issue_identifier: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """Capture the closed-day snapshot if a UTC midnight boundary was crossed.

    This is the canonical entry point. The dispatcher calls it; manual
    heartbeats can call it via `python3 scripts/midnight_snapshot.py` or
    `python3 -c "from scripts.midnight_snapshot import capture_closed_day_snapshot; ..."`.

    Returns the new `last_closed_day` record on success, or None if no
    boundary was crossed (or the boundary was already recorded for this
    closed day).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    state = load_state()

    closed_day_date, open_reading = detect_boundary(state, now)
    if closed_day_date is None:
        print("[midnight-snapshot] No UTC midnight boundary crossed; nothing to do.")
        return None

    if not force and state.get("last_midnight_recorded_date") == closed_day_date:
        print(
            f"[midnight-snapshot] Already recorded closed day {closed_day_date}; "
            "skipping (use --force to override)."
        )
        return None

    db_url = _catalog_db_url()
    from urllib.parse import urlparse

    parsed = urlparse(db_url)
    db_host = f"{parsed.hostname}:{parsed.port}{parsed.path}"
    print(
        f"[midnight-snapshot] Boundary crossed — closed day {closed_day_date}. "
        f"Reading current pg_stat from {db_host}…"
    )

    conn = psycopg2.connect(db_url, connect_timeout=15)
    try:
        close_stat = read_pg_stat_products(conn)
    finally:
        conn.close()

    if not close_stat or "n_tup_ins" not in close_stat:
        print(
            "[midnight-snapshot] FATAL: pg_stat_user_tables returned no row for "
            "products; cannot record closed-day snapshot."
        )
        return None

    record = build_closed_day_record(
        closed_day_date, open_reading, close_stat, now, db_host
    )

    print(
        f"[midnight-snapshot] closed_day={record['date']} "
        f"open={record['n_tup_ins_open']:,} close={record['n_tup_ins_close']:,} "
        f"delta={record['delta']:+,} n_live_tup_close={record['n_live_tup_close']:,}"
    )

    if dry_run:
        print(
            "[midnight-snapshot] --dry-run: would write state and post comment; "
            "skipping both."
        )
        return record

    # State write is the durable record; do it before the comment so a comment
    # failure doesn't leave the state unwritten.
    state["last_closed_day"] = record
    state["last_midnight_recorded_date"] = closed_day_date
    save_state(state)

    comment_id = post_boundary_comment(record, fire_issue_identifier)
    if comment_id:
        print(
            f"[midnight-snapshot] Comment posted to {DISPATCHER_PARENT_IDENTIFIER} "
            f"thread (id {comment_id})."
        )
    else:
        print(
            "[midnight-snapshot] Comment posting failed (see WARN above); state "
            "file still has the record — manual re-post may be needed."
        )

    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the snapshot and print the result, but do not write state or post.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the existing closed-day record for today if one exists.",
    )
    parser.add_argument(
        "--fire-issue",
        type=str,
        default=None,
        metavar="BUY-XXXXX",
        help="Identifier of the dispatch fire this snapshot is being captured "
        "from (e.g. BUY-39992). Shown in the comment body for traceability.",
    )
    args = parser.parse_args()

    record = capture_closed_day_snapshot(
        force=args.force,
        fire_issue_identifier=args.fire_issue,
        dry_run=args.dry_run,
    )
    return 0 if record is not None or not args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
