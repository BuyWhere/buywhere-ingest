#!/usr/bin/env python3
"""PostHog HogQL client for the BuyWhere daily CEO report.

Project: PostHog 415112
Auth:    POSTHOG_PAT (personal API key, query:read scope on project 415112)
NOT auth: POSTHOG_PROJECT_KEY / POSTHOG_PROJECT_TOKEN — those are project
            keys (write-only) and /api/projects/415112/query/ returns 403.

Issue: BUY-52246 (PostHog HogQL query:read access recovery for CEO-report
       telemetry) — this module is the durable fix so Lyra/Reed/Oracle
       can keep the daily report fresh without the personal-key-vs-project-
       key foot-gun repeating.

Public API:
    hogql(sql: str) -> list[list]
        Run a HogQL query, return the rows (results key from the API).
        Raises HogQLError on transport / API failure.

    ceo_report_pack(as_of: date) -> dict
        Pulls the canonical 5-KPI pack used by the daily CEO report:
          - api_query MTD count
          - mcp_tool_call MTD count
          - human $pageview (buywhere.ai) MTD count
          - unique active agents (distinct_id on api_query)
          - closed-day prior-day d/d deltas for api_query, mcp_tool_call,
            and $pageview.

CLI:
    python3 scripts/posthog_hogql.py ceo-pack [--as-of YYYY-MM-DD]
        Prints the canonical CEO-report KPI pack as JSON.
    python3 scripts/posthog_hogql.py query "SELECT 1"
        Run an ad-hoc HogQL query (handy for verification curls).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

POSTHOG_HOST = "https://us.i.posthog.com"
POSTHOG_PROJECT_ID = "415112"
SECRETS_FILE = Path("/home/paperclip/.secrets/fleet-secrets.json")


class HogQLError(RuntimeError):
    """PostHog HogQL call failed."""


def _load_pat() -> str:
    """Read POSTHOG_PAT from the fleet-secrets file. Falls back to env."""
    try:
        d = json.loads(SECRETS_FILE.read_text())
    except FileNotFoundError:
        d = {}
    pat = d.get("POSTHOG_PAT") or os.environ.get("POSTHOG_PAT")
    if not pat:
        raise HogQLError(
            "POSTHOG_PAT not found in "
            f"{SECRETS_FILE} or environment. Personal API key with "
            f"query:read scope on project {POSTHOG_PROJECT_ID} is required."
        )
    return pat


def hogql(sql: str, *, timeout_s: float = 30.0) -> list[list]:
    """Run a HogQL query against project 415112 and return results rows.

    Returns the raw `results` list-of-lists from the API. Numeric columns
    come back as strings on some queries; cast as needed by the caller.
    """
    pat = _load_pat()
    url = f"{POSTHOG_HOST}/api/projects/{POSTHOG_PROJECT_ID}/query/"
    body = json.dumps({"query": {"kind": "HogQLQuery", "query": sql}}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json",
            "User-Agent": "buywhere-posthog-hogql/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise HogQLError(
            f"PostHog returned HTTP {e.code} for {url}: {detail[:500]}"
        ) from e
    except urllib.error.URLError as e:
        raise HogQLError(f"PostHog call failed: {e.reason}") from e

    err = payload.get("error")
    if err:
        raise HogQLError(f"HogQL error: {err}")

    return payload.get("results") or []


def _scalar(rows: list[list], default: int | float = 0) -> int | float:
    if not rows or not rows[0]:
        return default
    val = rows[0][0]
    if val is None:
        return default
    # Cast strings to int when possible (PostHog returns numbers as
    # strings for some COUNT-style queries).
    if isinstance(val, str):
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return val
    return val


def ceo_report_pack(as_of: date | None = None) -> dict[str, Any]:
    """Return the canonical daily CEO report KPI pack.

    `as_of` is the closed day to use as the right edge of the MTD window
    (so calling with as_of=2026-06-15 returns "MTD through closed
    2026-06-14", matching the report's "through the closed YYYY-MM-DD UTC
    window" convention).

    All times are interpreted in UTC; the closed day is the calendar day
    00:00:00Z to 24:00:00Z.
    """
    as_of = as_of or (datetime.now(timezone.utc).date() - timedelta(days=1))
    if as_of >= datetime.now(timezone.utc).date():
        raise ValueError(
            f"as_of={as_of} is not a closed day; use the prior calendar day"
        )

    mtd_start = as_of.replace(day=1).isoformat()
    window_end = as_of.isoformat()  # exclusive
    day_start = as_of.isoformat()
    day_end = (as_of + timedelta(days=1)).isoformat()
    prior_day_start = (as_of - timedelta(days=1)).isoformat()
    prior_day_end = as_of.isoformat()
    month_start_dt = f"{mtd_start} 00:00:00"
    window_end_dt = f"{window_end} 00:00:00"
    day_start_dt = f"{day_start} 00:00:00"
    day_end_dt = f"{day_end} 00:00:00"
    prior_day_start_dt = f"{prior_day_start} 00:00:00"
    prior_day_end_dt = f"{prior_day_end} 00:00:00"

    # 1) api_query MTD
    api_query_mtd = _scalar(hogql(
        f"SELECT count(*) FROM events "
        f"WHERE event = 'api_query' "
        f"AND timestamp >= toDateTime('{month_start_dt}') "
        f"AND timestamp < toDateTime('{window_end_dt}')"
    ))

    # 2) mcp_tool_call MTD
    mcp_mtd = _scalar(hogql(
        f"SELECT count(*) FROM events "
        f"WHERE event = 'mcp_tool_call' "
        f"AND timestamp >= toDateTime('{month_start_dt}') "
        f"AND timestamp < toDateTime('{window_end_dt}')"
    ))

    # 3) browser-side $pageview MTD — the canonical Lyra KPI.
    #    The 06-15 report's "1,627 browser-side human $pageview events"
    #    matches `event = '$pageview'` with no is_bot filter: every
    #    $pageview event in the project has is_bot=null, so adding
    #    `is_bot = false` returns 0 (PostHog property coercion).
    pageview_mtd = _scalar(hogql(
        f"SELECT count(*) FROM events "
        f"WHERE event = '$pageview' "
        f"AND timestamp >= toDateTime('{month_start_dt}') "
        f"AND timestamp < toDateTime('{window_end_dt}')"
    ))

    # 4) unique active agents — distinct distinct_id across both
    #    api_query and mcp_tool_call events. This matches the prior
    #    report's "147 active AI agents" definition (just api_query
    #    returns 139, missing the mcp-only agents).
    agents = _scalar(hogql(
        f"SELECT count(DISTINCT distinct_id) FROM events "
        f"WHERE event IN ('api_query', 'mcp_tool_call') "
        f"AND timestamp >= toDateTime('{month_start_dt}') "
        f"AND timestamp < toDateTime('{window_end_dt}')"
    ))

    # 5) closed-day d/d deltas
    api_query_day = _scalar(hogql(
        f"SELECT count(*) FROM events WHERE event = 'api_query' "
        f"AND timestamp >= toDateTime('{day_start_dt}') "
        f"AND timestamp < toDateTime('{day_end_dt}')"
    ))
    api_query_prior = _scalar(hogql(
        f"SELECT count(*) FROM events WHERE event = 'api_query' "
        f"AND timestamp >= toDateTime('{prior_day_start_dt}') "
        f"AND timestamp < toDateTime('{prior_day_end_dt}')"
    ))

    mcp_day = _scalar(hogql(
        f"SELECT count(*) FROM events WHERE event = 'mcp_tool_call' "
        f"AND timestamp >= toDateTime('{day_start_dt}') "
        f"AND timestamp < toDateTime('{day_end_dt}')"
    ))
    mcp_prior = _scalar(hogql(
        f"SELECT count(*) FROM events WHERE event = 'mcp_tool_call' "
        f"AND timestamp >= toDateTime('{prior_day_start_dt}') "
        f"AND timestamp < toDateTime('{prior_day_end_dt}')"
    ))

    pageview_day = _scalar(hogql(
        f"SELECT count(*) FROM events WHERE event = '$pageview' "
        f"AND timestamp >= toDateTime('{day_start_dt}') "
        f"AND timestamp < toDateTime('{day_end_dt}')"
    ))
    pageview_prior = _scalar(hogql(
        f"SELECT count(*) FROM events WHERE event = '$pageview' "
        f"AND timestamp >= toDateTime('{prior_day_start_dt}') "
        f"AND timestamp < toDateTime('{prior_day_end_dt}')"
    ))

    return {
        "as_of": as_of.isoformat(),
        "mtd_start": mtd_start,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "host": POSTHOG_HOST,
            "project_id": POSTHOG_PROJECT_ID,
            "auth": "POSTHOG_PAT (personal API key, query:read scope)",
        },
        "kpis": {
            "api_queries_mtd": int(api_query_mtd),
            "mcp_tool_calls_mtd": int(mcp_mtd),
            "pageviews_human_mtd": int(pageview_mtd),
            "active_agents_mtd": int(agents),
        },
        "closed_day_deltas": {
            "api_queries": {
                "closed_day": int(api_query_day),
                "prior_day": int(api_query_prior),
                "dd": int(api_query_day) - int(api_query_prior),
            },
            "mcp_tool_calls": {
                "closed_day": int(mcp_day),
                "prior_day": int(mcp_prior),
                "dd": int(mcp_day) - int(mcp_prior),
            },
            "pageviews_human": {
                "closed_day": int(pageview_day),
                "prior_day": int(pageview_prior),
                "dd": int(pageview_day) - int(pageview_prior),
            },
        },
    }


def _cmd_ceo_pack(args: argparse.Namespace) -> int:
    as_of = None
    if args.as_of:
        as_of = date.fromisoformat(args.as_of)
    pack = ceo_report_pack(as_of=as_of)
    print(json.dumps(pack, indent=2, default=str))
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    rows = hogql(args.sql)
    print(json.dumps(rows, indent=2, default=str))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    p_ceo = sub.add_parser("ceo-pack", help="Run the canonical CEO-report KPI pack")
    p_ceo.add_argument("--as-of", help="Closed day (UTC), YYYY-MM-DD. Default: prior calendar day.")
    p_ceo.set_defaults(func=_cmd_ceo_pack)
    p_q = sub.add_parser("query", help="Run an ad-hoc HogQL query")
    p_q.add_argument("sql", help="HogQL query text")
    p_q.set_defaults(func=_cmd_query)
    return p


def main() -> int:
    args = _build_parser().parse_args()
    try:
        return args.func(args)
    except HogQLError as e:
        print(f"[posthog_hogql] ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
