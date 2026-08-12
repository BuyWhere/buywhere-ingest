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
      "last_check_result": "PASS"|"FAIL"|"BELOW_TARGET"|"BASELINE"|"ERROR",
      "last_check_real_rows": <int>,
      "last_check_source": "n_tup_ins_delta"|"count_window"|"unavailable"
    }
"""

from __future__ import annotations

import json
import os
import sys
import time
import base64
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import psycopg2
import psycopg2.extras
import requests
from requests.adapters import HTTPAdapter

_session = requests.Session()
_session.mount("http://", HTTPAdapter(pool_connections=4, pool_maxsize=8))
_session.mount("https://", HTTPAdapter(pool_connections=4, pool_maxsize=8))

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
STMT_TIMEOUT_FAST_RETRY_S = 20 # one retry when the fast path is transiently contended
STMT_TIMEOUT_COUNT_S = 30      # for the hour-bucket COUNT (best-effort)
STMT_TIMEOUT_MAX_CREATED_S = 8 # for MAX(created_at) staleness snapshot

# BUY-29861 — parent for failure child issues and PASS comments (canonical v6 dispatcher)
PARENT_ISSUE_ID = "4891fe2c-4957-46c9-a45d-451c157af77a"
PASS_COMMENT_ISSUE_ID = PARENT_ISSUE_ID
COMPANY_ID = "177bc805-e3c8-4336-84cb-8e1e482d5a17"

# User to assign failure issues to (board owner)
ASSIGNEE_USER_ID = "MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6"

CATALOG_DB_URL_FILE = REPO_ROOT / "data" / ".catalog_db_url"
STATE_FILE = REPO_ROOT / "data" / ".throughput_state.json"

# BUY-58452: evidence markdown report directory in the owning agent workspace.
EVIDENCE_DIR = Path(
    "/paperclip/instances/default/workspaces/"
    "a29ac9dc-cf0a-455b-964c-e75bd2f5fc47/BUY-58452"
)


def select_v6_throughput_signal(
    delta_ins_from_stats: int | None,
    canonical_ing_inserted: int | None,
    live_count_delta: int | None,
    n_live_tup_delta: int | None = None,
) -> tuple[int, str]:
    """Select the v6 pass/fail metric without letting weak signals mask passes.

    The returned metric is for evidence/display. The pass/fail predicate below
    enforces the same ordering so ticket creation cannot diverge from the
    evidence source.

    v6.2 hard guard (BUY-60573): n_live_tup_delta is the pg_stat_user_tables
    live-tuple *estimate* delta. Unlike the live_count delta (from SELECT
    count(*), which times out under maglev contention), n_live_tup is always
    available and is updated by ANALYZE. When the authoritative
    delta_ins_from_stats is below target BUT n_live_tup_delta is >= 150K, the
    stats insert counter is lagged/stale (not a true reset) and real inserts
    demonstrably happened. In that case the hard guard forces a PASS so we do
    not file a false-positive stall ticket on a healthy fleet.

    v6.4 (BUY-60953-fix): ing_inserted corroboration guards the
    n_live_tup_delta_guard against false positives from autovacuum bloat
    release. When ing_inserted is available and below target, an n_live_tup
    surge is likely from vacuum freeing dead tuple space, not real insert
    growth. 2026-07-08 18Z exhibited this: ing_inserted=18 with
    n_live_tup_delta=+7.4M (autovacuum).
    """
    # BUY-63915 fix: the Python guard predicate was inverted relative to the JS
    # dispatcher (nLiveTupGuardAllowed). When ing_inserted is LOW (< target),
    # ingestion was throttled and a large n_live_tup_delta is almost certainly
    # autovacuum/analyze dead-tuple release, not real inserts — the guard must be
    # BLOCKED so a low delta_ins_from_stats is NOT overridden. The guard should
    # be ALLOWED only when ing_inserted is unavailable (None) OR >= target
    # (ingestion healthy — a live-tuple surge corroborates real inserts despite
    # a lagged pg_stat counter, per v6.2 BUY-60573 stale-counter pattern).
    # 2026-07-31 03Z–10Z run exposed this inversion: 8 consecutive hours of
    # collapse (delta_ins 0..15K, ing 0..477K) were masked as PASS via
    # n_live_tup_delta_guard (autovacuum +1.5M surge), causing 5 missed
    # children (04Z/06Z/07Z/08Z/10Z) retrofiled under BUY-63915.
    n_live_tup_guard_blocked_by_ing_inserted = (
        n_live_tup_delta is not None
        and n_live_tup_delta >= TARGET_ROWS_PER_HOUR
        and canonical_ing_inserted is not None
        and int(canonical_ing_inserted) < TARGET_ROWS_PER_HOUR
    )

    # v6.2 rule 5(b) hard guard: n_live_tup corroboration overrides a low
    # delta_ins_from_stats. This blocks the stale-counter false-FAIL pattern
    # observed on 2026-07-06 22Z/23Z (delta_ins=2262/722 but n_live_tup grew
    # +247K/+876K).
    if (
        delta_ins_from_stats is not None
        and delta_ins_from_stats < TARGET_ROWS_PER_HOUR
        and n_live_tup_delta is not None
        and n_live_tup_delta >= TARGET_ROWS_PER_HOUR
        and not n_live_tup_guard_blocked_by_ing_inserted
    ):
        return int(n_live_tup_delta), "n_live_tup_delta_guard"

    if delta_ins_from_stats is not None:
        return int(delta_ins_from_stats), "delta_ins_from_stats"

    # When the primary stats delta is unavailable, n_live_tup_delta still
    # serves as a corroborating pass signal unless v6.4 ing_inserted
    # corroboration blocks a phantom live-tuple surge.
    if (
        n_live_tup_delta is not None
        and n_live_tup_delta >= TARGET_ROWS_PER_HOUR
        and not n_live_tup_guard_blocked_by_ing_inserted
    ):
        return int(n_live_tup_delta), "n_live_tup_delta_guard"

    if live_count_delta is not None and live_count_delta >= TARGET_ROWS_PER_HOUR:
        return int(live_count_delta), "live_count_delta"
    ing_inserted = int(canonical_ing_inserted or 0)
    if ing_inserted > 0:
        return ing_inserted, "ingestion_runs_observability"
    if live_count_delta is not None:
        return int(live_count_delta), "live_count_delta"
    return 0, "unavailable"


def should_file_v6_failure_ticket(
    *,
    delta_ins_from_stats: int | None,
    canonical_ing_inserted: int | None,
    live_count_delta: int | None,
    n_live_tup_delta: int | None = None,
) -> bool:
    """Return True when a v6 failure child should be filed.

    Rule 5a/5b/5d: delta_ins_from_stats is the PRIMARY authoritative signal.
    When non-null, it governs the decision directly: >= target passes, while
    below target files unless the v6.2 n_live_tup hard guard proves real growth
    and v6.4 ing_inserted corroboration does not block that guard.

    v6.2 rule 5(b) hard guard (BUY-60573): if delta_ins_from_stats is below
    target but n_live_tup_delta (the always-available pg_stat live-tuple
    estimate delta) is >= 150K, the insert counter is stale and real inserts
    happened — do NOT file.

    v6.4 (BUY-63152): ing_inserted corroboration blocks the n_live_tup hard
    guard when ing_inserted is available AND < target — autovacuum bloat
    release produced a phantom positive delta while zero/few rows were
    actually inserted. When ing_inserted is unavailable (None) OR >= target,
    the guard still fires to preserve stale-counter protection.

    Rule 5d: when delta_ins_from_stats is NULL (true stat reset / first tick),
    fall back to ingestion_runs and live_count. File only if every available
    fallback signal is also below 150K.
    """
    if delta_ins_from_stats is not None:
        if int(delta_ins_from_stats) >= TARGET_ROWS_PER_HOUR:
            return False
        # BUY-63915 fix: the guard is allowed (no file) only when ing_inserted
        # is unavailable (None) OR >= target — i.e. ingestion corroborates that
        # a live-tuple surge is real inserts despite a lagged pg_stat counter
        # (v6.2 BUY-60573 stale-counter pattern). When ing_inserted is LOW
        # (< target), a large n_live_tup_delta is autovacuum/analyze dead-tuple
        # release and must NOT override the authoritative low delta_ins_from_stats.
        if (
            n_live_tup_delta is not None
            and int(n_live_tup_delta) >= TARGET_ROWS_PER_HOUR
            and (canonical_ing_inserted is None or int(canonical_ing_inserted) >= TARGET_ROWS_PER_HOUR)
        ):
            return False
        if live_count_delta is not None and int(live_count_delta) >= TARGET_ROWS_PER_HOUR:
            return False
        return True

    # delta_ins_from_stats is NULL: stat reset or first-ever tick.
    # n_live_tup_delta corroborates real growth only when ing_inserted is
    # >= target (or unavailable/None as neutral). When ing_inserted is LOW (< target),
    # a live-tuple surge is autovacuum noise — block the guard so we fall
    # through to the ingestion_runs/live_count fallback which is the only
    # reliable signal when pg_stat counters have been reset.
    if (
        n_live_tup_delta is not None
        and n_live_tup_delta >= TARGET_ROWS_PER_HOUR
        and canonical_ing_inserted is not None
        and int(canonical_ing_inserted) < TARGET_ROWS_PER_HOUR
    ):
        # v6.4: n_live_tup guard is blocked by low ing_inserted (autovacuum
        # bloat). Do NOT return True here — fall through to check if
        # live_count_delta >= target (Rule 5d: FAIL only when ALL signals
        # are below 150K).
        pass
    elif (
        n_live_tup_delta is not None
        and int(n_live_tup_delta) >= TARGET_ROWS_PER_HOUR
        and (canonical_ing_inserted is None or int(canonical_ing_inserted) >= TARGET_ROWS_PER_HOUR)
    ):
        return False  # guard allows a stale-counter pass
    # Fall back to ingestion_runs and live_count (rule 5c/5d).
    ingestion_unavailable_or_low = (
        canonical_ing_inserted is None or int(canonical_ing_inserted) < TARGET_ROWS_PER_HOUR
    )
    live_count_unavailable_or_low = (
        live_count_delta is None or int(live_count_delta) < TARGET_ROWS_PER_HOUR
    )
    return ingestion_unavailable_or_low and live_count_unavailable_or_low


def is_completed_hour(hour_start: datetime, now: datetime) -> bool:
    """Return True only when the entire hourly window has elapsed."""
    if hour_start.tzinfo is None:
        hour_start = hour_start.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    hour_start = hour_start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    now = now.astimezone(timezone.utc)
    return hour_start + timedelta(hours=1) <= now


def assert_v6_forbidden_patterns(
    *,
    delta_ins_from_stats: int | None,
    delta_upd_from_stats: int | None,
    real_rows: int,
    source: str,
    live_count_delta: int | None,
    current_n_tup_ins: int | None = None,
    previous_n_tup_ins: int | None = None,
) -> None:
    """Enforce v6 forbidden decision patterns before filing failures."""
    # Rule 6(c): never report delta_ins_from_stats=0 if raw consecutive
    # n_tup_ins values clearly differ. A zero insert delta with update movement
    # is not itself contradictory; canonical products can legitimately receive
    # updates without inserts for an hour.
    if (
        delta_ins_from_stats is not None
        and delta_ins_from_stats == 0
        and current_n_tup_ins is not None
        and previous_n_tup_ins is not None
        and int(current_n_tup_ins) != int(previous_n_tup_ins)
    ):
        raise AssertionError(
            "v6 rule 6(c) violation: delta_ins_from_stats=0 while raw "
            f"consecutive n_tup_ins values differ ({previous_n_tup_ins} -> "
            f"{current_n_tup_ins}). Investigate canonical_throughput_hourly "
            "upsert; do NOT file a FAIL ticket."
        )

    # Rule 6(a): never file FAIL based on ing_inserted=0 alone when
    # delta_ins_from_stats is non-null.
    if delta_ins_from_stats is not None and real_rows < TARGET_ROWS_PER_HOUR and source == "ingestion_runs_observability":
        raise AssertionError(
            "v6 rule 6(a) violation: source fell back to ingestion_runs while "
            "delta_ins_from_stats is non-null. ingestion_runs is observability-only; "
            "real_rows must equal delta_ins_from_stats when available."
        )

    # Rule 6(b): never let a zero secondary metric become the selected failure
    # metric when another available counter shows movement.
    if (
        delta_ins_from_stats is not None
        and delta_ins_from_stats > 0
        and live_count_delta is not None
        and live_count_delta == 0
        and real_rows < TARGET_ROWS_PER_HOUR
        and source == "live_count_delta"
    ):
        raise AssertionError(
            "v6 rule 6(b) violation: live_count_delta=0 while "
            f"delta_ins_from_stats=+{delta_ins_from_stats}. The canonical stats "
            "delta shows inserts but live_count shows no growth. Do NOT file a FAIL ticket."
        )
    if (
        live_count_delta is not None
        and live_count_delta > 0
        and delta_ins_from_stats is not None
        and delta_ins_from_stats == 0
        and real_rows < TARGET_ROWS_PER_HOUR
        and source == "delta_ins_from_stats"
    ):
        raise AssertionError(
            "v6 rule 6(b) violation: delta_ins_from_stats=0 while "
            f"live_count_delta=+{live_count_delta}. The live count shows real growth "
            "but pg_stat counters appear flat. Do NOT file a FAIL ticket."
        )



def _fmt_int(value: Any, default: str = "?") -> str:
    """Format an int with thousands separators, tolerating None/missing."""
    if value is None:
        return default
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return default


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
    # The canonical catalog has migrated hosts over time (maglev, sakura, ...).
    # Accept any Railway proxy host for the catalog role while still refusing the
    # known-wrong harness DB (roundhouse, which is ~4.2M rows, not the catalog).
    return url


def _api_headers() -> dict[str, str] | None:
    api_key = os.environ.get("PAPERCLIP_API_KEY", "").strip()
    run_id = _jwt_run_id(api_key) or os.environ.get("PAPERCLIP_RUN_ID", "")
    if not api_key:
        return None
    h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if run_id:
        h["X-Paperclip-Run-Id"] = run_id
    return h


def _jwt_run_id(api_key: str) -> str | None:
    try:
        payload = api_key.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload.encode()))
        return decoded.get("run_id")
    except Exception:
        return None


def _api_base() -> str:
    return os.environ.get("PAPERCLIP_API_URL", "http://localhost:3000").rstrip("/") + "/api"


def _retry_request(
    method,
    url,
    *,
    max_attempts=3,
    initial_delay=2.0,
    backoff_factor=2.0,
    max_sleep=20.0,
    **kwargs,
):
    """Execute an HTTP request with exponential backoff retry on 429 / 5xx.

    Args:
        method: 'get' or 'post'.
        url: request URL.
        max_attempts: maximum number of attempts (default 3).
        initial_delay: seconds to wait before first retry (default 2.0).
        backoff_factor: multiplier per retry step (default 2.0).
        max_sleep: maximum sleep between attempts. Paperclip heartbeat runs are
            bounded; the dispatcher must buffer API work rather than sleeping
            for minutes inside the cron wrapper.
        **kwargs: forwarded to requests.{method}.

    Returns:
        requests.Response (raises on non-retryable errors after exhausting retries).
    """
    delay = initial_delay
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = _session.request(method, url, **kwargs)
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == max_attempts:
                raise
            print(f'[retry] attempt {attempt}/{max_attempts} failed '
                  f'(network error: {exc.__class__.__name__}: {exc}); '
                  f'retrying in {delay:.1f}s')
            time.sleep(delay)
            delay *= backoff_factor
            continue

        if resp.status_code == 429:
            if attempt == max_attempts:
                print(f'[retry] attempt {attempt}/{max_attempts}: 429 still returned; giving up')
                resp.raise_for_status()  # will raise the 429
            # Respect Retry-After when it fits inside this cron run's bounded
            # budget. Long rate-limit waits are handled by buffering the child
            # issue for the next hourly fire instead of risking heartbeat
            # timeout.
            retry_after = resp.headers.get('Retry-After')
            if retry_after:
                try:
                    wait = float(retry_after)
                except (TypeError, ValueError):
                    wait = delay
            else:
                wait = delay
            wait = min(wait, max_sleep)
            print(f'[retry] attempt {attempt}/{max_attempts}: 429 rate-limited; '
                  f'retrying in {wait:.1f}s (Retry-After={retry_after})')
            time.sleep(wait)
            delay *= backoff_factor
            continue

        # Retry 5xx on best-effort basis (dedup GET, child-filing POST)
        if 500 <= resp.status_code < 600:
            if attempt == max_attempts:
                print(f'[retry] attempt {attempt}/{max_attempts}: HTTP {resp.status_code}; giving up')
                resp.raise_for_status()
            print(f'[retry] attempt {attempt}/{max_attempts}: HTTP {resp.status_code}; '
                  f'retrying in {delay:.1f}s')
            time.sleep(min(delay, max_sleep))
            delay *= backoff_factor
            continue

        # Success
        return resp

    raise RuntimeError(f'exhausted {max_attempts} attempts for {method.upper()} {url}') from last_exc


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
    # Defensive serialization: state is shared with external/manual writes and can
    # contain non-JSON-native values (notably datetime objects). Always coerce
    # recursively before persisting to prevent a transient serialization error
    # from breaking the hourly dispatch run.
    normalized = _normalize_state_for_json(state)

    def _safe_default(obj: Any) -> str:
        if isinstance(obj, (set, tuple)):
            return str(list(obj))
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        return str(obj)

    payload = json.dumps(normalized, indent=2, default=_safe_default)
    tmp.write_text(payload)
    tmp.replace(STATE_FILE)


def _normalize_state_for_json(value: Any) -> Any:
    """Return a JSON-safe copy for state writes."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, timedelta):
        return f"{value.total_seconds()}s"
    if isinstance(value, dict):
        return {str(k): _normalize_state_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_state_for_json(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# ---------------------------------------------------------------------------
# DB queries — split into a fast path (pg_stat) and a slow path (COUNT window).
# ---------------------------------------------------------------------------


def read_pg_stat_products(conn) -> dict[str, Any]:
    """O(1) read of pg_stat_user_tables.products with one longer retry on timeout."""
    row = None
    last_error = None
    for timeout_s in (STMT_TIMEOUT_FAST_S, STMT_TIMEOUT_FAST_RETRY_S):
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SET statement_timeout = %s", (f"{timeout_s}s",))
                cur.execute(
                    """
                    SELECT n_live_tup, n_tup_ins, n_tup_upd, n_tup_del,
                           seq_scan, idx_scan
                    FROM pg_stat_user_tables WHERE relname = 'products'
                    """
                )
                row = cur.fetchone()
            break
        except psycopg2.errors.QueryCanceled as exc:
            conn.rollback()
            last_error = exc
    if row is None and last_error is not None:
        raise last_error
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


def upsert_canonical_throughput_row(
    conn,
    hour_start: datetime,
    stat: dict[str, Any],
    pm_start: str | None,
    hour_data: dict[str, Any] | None,
    source: str,
    note: str,
) -> dict[str, Any]:
    """Upsert one hourly row into canonical_throughput_hourly.

    Captures the pg_stat_user_tables.products counters plus ingestion_runs
    aggregates for `hour_start` so subsequent dispatches can compute deltas
    via (cur.n_tup_ins - prv.n_tup_ins) instead of relying on a local state
    file. Implements BUY-58485 v4 n_tup_ins delta spec.

    live_count is best-effort: the table scan can stall under maglev
    contention so we set statement_timeout=3s and fall back to NULL.

    ing_* aggregates come from hour_data when present (already computed for
    the just-checked window) and from ingestion_runs when not.

    Returns a dict {upserted: bool, hour_start: iso, note: str}.
    """
    hour_start_ts = hour_start.replace(minute=0, second=0, microsecond=0)
    n_tup_ins = stat.get("n_tup_ins")
    n_tup_upd = stat.get("n_tup_upd")
    n_live_tup = stat.get("n_live_tup")

    # Best-effort live_count
    live_count = None
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '3s'")
            cur.execute("SELECT count(*)::bigint FROM products")
            row = cur.fetchone()
        conn.rollback()
        if row and row[0] is not None:
            live_count = int(row[0])
    except psycopg2.errors.QueryCanceled:
        conn.rollback()
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        try:
            conn.rollback()
        except Exception:
            pass

    # ingestion_runs aggregates for this hour (best-effort, fast on 211K-row table)
    ing_runs = 0
    ing_inserted = 0
    ing_updated = 0
    hour_end_ts = hour_start_ts + timedelta(hours=1)
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '5s'")
            cur.execute(
                """
                SELECT count(*)::int AS runs,
                       COALESCE(sum(rows_inserted),0)::bigint AS ins,
                       COALESCE(sum(rows_updated),0)::bigint  AS upd
                FROM ingestion_runs
                WHERE started_at >= %s AND started_at < %s
                  AND status = 'completed'
                """,
                (hour_start_ts, hour_end_ts),
            )
            row = cur.fetchone()
        conn.rollback()
        if row:
            ing_runs = int(row[0] or 0)
            ing_inserted = int(row[1] or 0)
            ing_updated = int(row[2] or 0)
    except psycopg2.errors.QueryCanceled:
        conn.rollback()
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        try:
            conn.rollback()
        except Exception:
            pass

    # BUY-59212: compute delta_ins_from_stats, delta_upd_from_stats, and
    # stat_reset_detected from the IMMEDIATELY-PREVIOUS canonical_throughput_hourly
    # row (hour_start - INTERVAL '1 hour'). Previously the v4 spec was to compute
    # the delta via an outer LEFT JOIN with `prv.hour_start < cur.hour_start`,
    # which matched ALL prior rows and yielded garbage/0 when there were hour
    # gaps. This block reads the SINGLE preceding-hour row in the same transaction
    # so the upsert is self-contained.
    delta_ins_from_stats = None
    delta_upd_from_stats = None
    stat_reset_detected = None
    previous_n_tup_ins = None
    previous_n_tup_upd = None
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '10s'")
            cur.execute(
                """
                SELECT n_tup_ins, n_tup_upd
                FROM canonical_throughput_hourly
                WHERE hour_start = %s - INTERVAL '1 hour'
                """,
                (hour_start_ts,),
            )
            prv_row = cur.fetchone()
        conn.rollback()
        if prv_row is not None:
            prv_n_tup_ins = prv_row[0]
            prv_n_tup_upd = prv_row[1]
            previous_n_tup_ins = prv_n_tup_ins
            previous_n_tup_upd = prv_n_tup_upd
            if n_tup_ins is not None and prv_n_tup_ins is not None:
                if prv_n_tup_ins > n_tup_ins or prv_n_tup_ins == 0:
                    # Counter went backward (true reset) or prior snapshot is
                    # zero (post-reset — never a valid baseline).  Mark as
                    # reset so the decision layer falls back to other signals.
                    stat_reset_detected = True
                else:
                    stat_reset_detected = False
                    delta_ins_from_stats = int(n_tup_ins) - int(prv_n_tup_ins)
            if n_tup_upd is not None and prv_n_tup_upd is not None:
                if (prv_n_tup_upd <= n_tup_upd or prv_n_tup_upd == 0) and stat_reset_detected is not True:
                    delta_upd_from_stats = int(n_tup_upd) - int(prv_n_tup_upd)
    except psycopg2.errors.QueryCanceled:
        conn.rollback()
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        try:
            conn.rollback()
        except Exception:
            pass

    pm_start_ts = None
    if pm_start:
        try:
            pm_start_ts = datetime.fromisoformat(pm_start.replace("Z", "+00:00"))
        except ValueError:
            pm_start_ts = None

    # BUY-59212: first-write-wins for n_tup_ins/n_tup_upd. If the row already
    # has n_tup_ins set, do NOT overwrite the counter values (they represent
    # the snapshot at first write). Only refresh metadata + recompute deltas.
    existing_n_tup_ins = None
    existing_n_tup_upd = None
    existing_delta_ins = None
    existing_delta_upd = None
    existing_stat_reset = None
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '3s'")
            cur.execute(
                """SELECT n_tup_ins, n_tup_upd, delta_ins_from_stats,
                          delta_upd_from_stats, stat_reset_detected
                   FROM canonical_throughput_hourly WHERE hour_start = %s""",
                (hour_start_ts,),
            )
            existing = cur.fetchone()
        conn.rollback()
        if existing is not None:
            existing_n_tup_ins = existing[0]
            existing_n_tup_upd = existing[1]
            existing_delta_ins = existing[2]
            existing_delta_upd = existing[3]
            existing_stat_reset = existing[4]
    except psycopg2.errors.QueryCanceled:
        conn.rollback()
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        try:
            conn.rollback()
        except Exception:
            pass

    # If a prior row exists with n_tup_ins, keep its snapshot and its deltas.
    # This keeps the delta chain stable across re-runs and prevents --force
    # backfills from inflating historical deltas with current stats.
    if existing_n_tup_ins is not None:
        n_tup_ins_snap = existing_n_tup_ins
    else:
        n_tup_ins_snap = n_tup_ins
    if existing_n_tup_upd is not None:
        n_tup_upd_snap = existing_n_tup_upd
    else:
        n_tup_upd_snap = n_tup_upd
    if existing_delta_ins is not None:
        delta_ins_from_stats = existing_delta_ins
    if existing_delta_upd is not None:
        delta_upd_from_stats = existing_delta_upd
    if existing_stat_reset is not None:
        stat_reset_detected = existing_stat_reset

    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '5s'")
            cur.execute(
                """
                INSERT INTO canonical_throughput_hourly
                    (hour_start, n_tup_ins, n_tup_upd, n_live_tup, live_count,
                     ing_runs, ing_inserted, ing_updated, pm_start, source, note,
                     delta_ins_from_stats, delta_upd_from_stats,
                     stat_reset_detected, delta_computed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, now())
                ON CONFLICT (hour_start) DO UPDATE SET
                    n_live_tup  = EXCLUDED.n_live_tup,
                    live_count  = EXCLUDED.live_count,
                    ing_runs    = EXCLUDED.ing_runs,
                    ing_inserted= EXCLUDED.ing_inserted,
                    ing_updated = EXCLUDED.ing_updated,
                    pm_start    = EXCLUDED.pm_start,
                    source      = EXCLUDED.source,
                    note        = EXCLUDED.note,
                    delta_ins_from_stats = EXCLUDED.delta_ins_from_stats,
                    delta_upd_from_stats = EXCLUDED.delta_upd_from_stats,
                    stat_reset_detected  = EXCLUDED.stat_reset_detected,
                    delta_computed_at    = EXCLUDED.delta_computed_at,
                    recorded_at = now()
                RETURNING hour_start
                """,
                (
                    hour_start_ts,
                    n_tup_ins_snap,
                    n_tup_upd_snap,
                    n_live_tup,
                    live_count,
                    ing_runs,
                    ing_inserted,
                    ing_updated,
                    pm_start_ts,
                    source,
                    note,
                    delta_ins_from_stats,
                    delta_upd_from_stats,
                    stat_reset_detected,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return {
            "upserted": bool(row),
            "hour_start": hour_start_ts.isoformat(),
            "live_count": live_count,
            "ing_runs": ing_runs,
            "ing_inserted": ing_inserted,
            "delta_ins_from_stats": delta_ins_from_stats,
            "delta_upd_from_stats": delta_upd_from_stats,
            "stat_reset_detected": stat_reset_detected,
            "n_tup_ins": n_tup_ins_snap,
            "n_tup_upd": n_tup_upd_snap,
            "previous_n_tup_ins": previous_n_tup_ins,
            "previous_n_tup_upd": previous_n_tup_upd,
            "n_live_tup": n_live_tup,
            "note": "upserted",
        }
    except psycopg2.errors.QueryCanceled:
        conn.rollback()
        return {"upserted": False, "hour_start": hour_start_ts.isoformat(),
                "note": "upsert timeout (statement_timeout exceeded)"}
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return {"upserted": False, "hour_start": hour_start_ts.isoformat(),
                "note": f"upsert connection_lost: {exc.__class__.__name__}"}


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
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
        return {"error": "connection_lost", "detail": str(exc).strip()}
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
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
        return {"error": "connection_lost", "detail": str(exc).strip()}


def query_postmaster_start_time(conn) -> str | None:
    """Snapshot the current postmaster start time to validate delta semantics."""
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = %s", (f"{STMT_TIMEOUT_FAST_S}s",))
            cur.execute("SELECT pg_postmaster_start_time()")
            row = cur.fetchone()
        conn.rollback()
        return str(row[0]) if row and row[0] else None
    except (psycopg2.errors.QueryCanceled, psycopg2.OperationalError, psycopg2.InterfaceError):
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def reconnect_if_needed(conn, db_url: str):
    """Refresh the connection after a best-effort query drops the SSL session."""
    if getattr(conn, "closed", 0):
        try:
            conn.close()
        except Exception:
            pass
        return psycopg2.connect(db_url, connect_timeout=15)
    return conn


def connect_catalog(db_url: str):
    """Open the canonical catalog connection and keep failures user-readable."""
    try:
        return psycopg2.connect(db_url, connect_timeout=15)
    except psycopg2.OperationalError as exc:
        print(
            "[throughput-dispatcher] FATAL: could not connect to canonical catalog DB: "
            f"{str(exc).strip()}"
        )
        return None


# ---------------------------------------------------------------------------
# Throughput computation
# ---------------------------------------------------------------------------


# --- v6 decision layer uses canonical_throughput_hourly deltas (spec rule 5a) ---

# ---------------------------------------------------------------------------
# Paperclip API integration
# ---------------------------------------------------------------------------


def dedup_check_existing_child(hour_start: datetime) -> bool:
    """Return True if a child issue for this hour already exists under BUY-29861.

    Fix (BUY-52687): the previous implementation searched for a synthetic prefix
    ``throughput-check-{hour_tag}`` that NEVER appears in the dispatcher's own
    title format (``[BUY-33694 dispatcher] Hourly throughput check
    (YYYY-MM-DD HH:MM UTC fire, HH:MM–HH:MM window)``). The search always
    returned 0 results, so dedup silently failed and duplicate FAIL children
    were filed for the same window (BUY-52684 / BUY-52677, 2026-06-18).

    New approach: fetch children by ``parentId`` only, then in Python check the
    title for the literal hour-window substring ``HH:MM–HH:MM window`` (U+2013
    en-dash, with trailing ``window)`` to anchor). That substring is unique
    per dispatched hour and is not subject to API search-tokenization quirks.
    Belt-and-suspenders: if the parentId fetch fails, we fall through (return
    False) so the check never strands a real failure.
    """
    # Anchor on the current failure-title substring:
    # "HH:00–HH:00 UTC YYYY-MM-DD" with U+2013 en-dash. Older dispatcher
    # titles used "HH:MM–HH:MM window)"; the active format comes from
    # format_failure_issue_title(). Keep the same exact tag here so same-hour
    # reruns cannot file duplicate children when state was not advanced.
    end = hour_start + timedelta(hours=1)
    window_tag = (
        f"{hour_start.strftime('%H')}:00–{end.strftime('%H')}:00 UTC "
        f"{hour_start.strftime('%Y-%m-%d')}"
    )
    try:
        headers = _api_headers()
        if headers is None:
            print(
                "[throughput-dispatcher] dedup_check_existing_child: "
                "missing PAPERCLIP_API_KEY; skipping lookup"
            )
            return False
        r = _retry_request(
            "get",
            f"{_api_base()}/companies/{COMPANY_ID}/issues",
            params={"parentId": PARENT_ISSUE_ID, "limit": 100},
            headers=headers,
            timeout=20,
        )
    except requests.RequestException as exc:
        print(
            "[throughput-dispatcher] dedup_check_existing_child: "
            f"Paperclip API lookup failed ({exc.__class__.__name__}: {exc}); continuing"
        )
        return False
    if not r.ok:
        print(
            "[throughput-dispatcher] dedup_check_existing_child: "
            f"API returned HTTP {r.status_code}; continuing"
        )
        return False
    body = r.json()
    issues = body if isinstance(body, list) else body.get("issues", [])
    for issue in issues:
        title = (issue.get("title") or "")
        if window_tag in title:
            return True
    return False



def _retry_pending_children(state: dict[str, Any]) -> list[str]:
    """Retry filing any pending child issues that were buffered during an API outage.

    Returns a list of newly-filed identifiers for use in the run note.
    """
    pending = state.get("pending_children", [])
    if not pending:
        return []

    filed_ids = []
    remaining = []
    for entry in pending:
        hs_label = "<unknown>"
        try:
            # hour_start is stored as ISO string; parse it back for create_stall_issue.
            # BUY-61439: try hour_start_iso first (canonical field name), fall back to
            # hour_start for backward compat with pre-patch state files.
            hs_raw = entry.get("hour_start_iso") or entry.get("hour_start")
            if isinstance(hs_raw, str):
                hs = datetime.fromisoformat(hs_raw)
            elif isinstance(hs_raw, dict) and "iso" in hs_raw:
                hs = datetime.fromisoformat(hs_raw["iso"])
            else:
                hs = datetime.fromisoformat(str(hs_raw))
            hs_label = hs.strftime("%H:%M") + "Z"
            ident = create_stall_issue(
                hour_start=hs,
                real_rows=entry["real_rows"],
                source=entry["source"],
                note=entry.get("note", "retried from pending buffer"),
                hour_data=entry.get("hour_data"),
                stat=entry.get("stat", {}),
                max_created=entry.get("max_created"),
                db_host=entry.get("db_host", "unknown"),
                fire_ts=entry.get("fire_ts", ""),
            )
            filed_ids.append(ident)
            print(f"[throughput-dispatcher] RETRY filed pending child {ident} "
                  f"for {hs.strftime('%H:%M')}Z window")
        except Exception as e:
            remaining.append(entry)
            print(f"[throughput-dispatcher] RETRY failed for pending child "
                  f"({hs_label} window): {e.__class__.__name__}: {e}")
            if hs is None:
                hs = datetime.fromtimestamp(0, tz=timezone.utc)

    state["pending_children"] = remaining
    return filed_ids


def build_evidence_markdown(
    hour_start: datetime,
    real_rows: int,
    source: str,
    note: str,
    hour_data: dict | None,
    stat: dict,
    max_created: dict | None,
    db_host: str,
    fire_ts: str,
    stat_reset_detected: bool | None = None,
    ingestion_counts: dict | None = None,
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

    return f"""# Hourly Throughput Check — {hour_label}

**Result: {"PASS" if real_rows >= TARGET_ROWS_PER_HOUR else "FAIL"} — {real_rows:,} / {TARGET_ROWS_PER_HOUR:,} ({pct:.1f}%).**

Parent: [BUY-29861](/BUY/issues/BUY-29861). Dispatcher: [BUY-33694](/BUY/issues/BUY-33694). Source: `{source}`.

> {note}

## Just-completed hour: {hour_start.isoformat()} → {hour_end.isoformat()}

| Metric | Value |
|---|---|
| Canonical metric used | `{source}` |
| Real rows (per `{source}`) | **{real_rows:,}** |
| Threshold | {TARGET_ROWS_PER_HOUR:,} |
| Margin vs. threshold | **{margin:+,} ({pct - 100:.1f}%)** |
| % of 150,000/hr target | **{pct:.1f}%** |
| `pg_stat_user_tables.products.n_live_tup` | {_fmt_int(stat.get('n_live_tup'))} |
| `pg_stat_user_tables.products.n_tup_ins`  | {_fmt_int(stat.get('n_tup_ins'))} |
| `pg_stat_user_tables.products.n_tup_upd`  | {_fmt_int(stat.get('n_tup_upd'))} |
| `stat_reset_detected` flag | {stat_reset_detected if stat_reset_detected is not None else 'N/A'} |
| `MAX(created_at)` (snapshot {fire_ts}) {max_block} |

## Hour-bucket COUNT verification (best-effort)

| total_rows | real_rows | first_row | last_row |
|---:|---:|---|---|
{count_block}

## ingestion_runs (observability-only)

| Field | Value |
|---|---|
| `ing_runs` | {_fmt_int((ingestion_counts or {}).get('ing_runs'))} |
| `ing_inserted` | {_fmt_int((ingestion_counts or {}).get('ing_inserted'))} |
| `ing_updated` | {_fmt_int((ingestion_counts or {}).get('ing_updated'))} |

## canonical_throughput_hourly upsert confirmation

- Hour row upserted: `{hour_label}`
- `stat_reset_detected`: {stat_reset_detected if stat_reset_detected is not None else 'N/A'}

## DB proof (canonical PostgreSQL @ {db_host})

Connection string source: `data/.catalog_db_url` (maglev). NOT the harness `DATABASE_URL`.

- n_tup_ins delta query (best-effort secondary signal under maglev contention):
  ```sql
  SELECT n_live_tup, n_tup_ins, n_tup_upd
  FROM pg_stat_user_tables WHERE relname = 'products';
  -- {_fmt_int(stat.get('n_live_tup'), '0')} | {_fmt_int(stat.get('n_tup_ins'), '0')} | {_fmt_int(stat.get('n_tup_upd'), '0')}
  ```
- Hour-bucket COUNT (windowed signal for this hour; may time out under contention):
  ```sql
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '{hour_start.isoformat()}'
    AND created_at <  '{hour_end.isoformat()}'
  GROUP BY 1 ORDER BY 1;
  ```
"""



def write_evidence_markdown(
    hour_start: datetime,
    real_rows: int,
    source: str,
    note: str,
    hour_data: dict | None,
    stat: dict,
    max_created: dict | None,
    db_host: str,
    fire_ts: str,
    failure_child_identifier: str | None = None,
    stat_reset_detected: bool | None = None,
    ingestion_counts: dict | None = None,
) -> Path | None:
    """Write the hourly evidence report markdown to the agent workspace.

    Always writes a report for every run so the evidence is durable on disk,
    regardless of whether the hour passed or failed. The path follows the
    BUY-29861 / BUY-62317 spec:
    BUY-58452/hourly-throughput-YYYY-MM-DDTHHZ.md
    """
    try:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        md = build_evidence_markdown(
            hour_start, real_rows, source, note, hour_data, stat, max_created, db_host, fire_ts,
            stat_reset_detected=stat_reset_detected,
            ingestion_counts=ingestion_counts,
        )
        if failure_child_identifier:
            md += f"\n\nFailure child: [{failure_child_identifier}](/BUY/issues/{failure_child_identifier})\n"
        hour_label = hour_start.strftime("%Y-%m-%dT%H")
        path = EVIDENCE_DIR / f"hourly-throughput-{hour_label}Z.md"
        path.write_text(md)
        print(f"[throughput-dispatcher] evidence markdown written: {path}")
        return path
    except Exception as e:
        print(f"[throughput-dispatcher] WARNING: failed to write evidence markdown: {e.__class__.__name__}: {e}")
        return None


def post_parent_pass_comment(
    hour_start: datetime,
    real_rows: int,
    source: str,
) -> None:
    """Post a one-line PASS comment on the parent BUY-29861 issue.

    Non-blocking: a comment failure is logged but does not fail the run.
    """
    headers = _api_headers()
    if headers is None:
        print("[throughput-dispatcher] WARNING: no API key; skipping PASS comment")
        return
    hour_end = hour_start + timedelta(hours=1)
    body = (
        f"PASS — {real_rows:,} products added in "
        f"{hour_start.strftime('%H:%M')}–{hour_end.strftime('%H:%M')} UTC "
        f"{hour_start.strftime('%Y-%m-%d')} (source={source}, target=150,000)."
    )
    try:
        r = _retry_request(
            "post",
            f"{_api_base()}/issues/{PASS_COMMENT_ISSUE_ID}/comments",
            json={"body": body},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        print(f"[throughput-dispatcher] PASS comment posted on {PASS_COMMENT_ISSUE_ID}")
    except Exception as e:
        print(f"[throughput-dispatcher] WARNING: PASS comment failed: {e.__class__.__name__}: {e}")


def format_failure_issue_title(hour_start: datetime, hour_end: datetime, real_rows: int) -> str:
    return (
        f"HOURLY THROUGHPUT FAILURE — {real_rows:,} products added in "
        f"{hour_start.strftime('%H')}:00–{hour_end.strftime('%H')}:00 UTC "
        f"{hour_start.strftime('%Y-%m-%d')} (target {TARGET_ROWS_PER_HOUR:,})"
    )


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
    description = build_evidence_markdown(
        hour_start, real_rows, source, note, hour_data, stat, max_created, db_host, fire_ts
    )

    hour_end = hour_start + timedelta(hours=1)
    title = format_failure_issue_title(hour_start, hour_end, real_rows)

    payload = {
        "companyId": COMPANY_ID,
        "title": title,
        "description": description,
        "parentId": PARENT_ISSUE_ID,
        "status": "todo",
        "priority": "high",
        "assigneeUserId": ASSIGNEE_USER_ID,
    }
    headers = _api_headers()
    if headers is None:
        raise RuntimeError("missing PAPERCLIP_API_KEY; cannot file child issue")
    r = _retry_request(
        "post",
        f"{_api_base()}/companies/{COMPANY_ID}/issues",
        json=payload,
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    identifier = body.get("identifier", "BUY-????")
    issue_id = body.get("id")

    # BUY-60542: Post-creation verification. The Paperclip server can return
    # HTTP 201 with a valid-looking identifier but silently roll back the DB
    # transaction (issue sequence advances but no row persists). Verify the
    # issue actually exists before reporting success; if it doesn't, raise so
    # the caller buffers it for retry.
    #
    # BUY-60559: The original verification used
    #   GET /companies/{id}/issues?identifier=...&take=5
    # but that list endpoint IGNORES the identifier filter and returns recent
    # issues regardless, so the newly created issue rarely appears in the
    # first 5 rows — producing false "silent rollback" RuntimeErrors even when
    # the issue persisted fine. Switch to the direct
    #   GET /api/issues/{issue_id}
    # endpoint, which reliably returns the single issue by id.
    if issue_id:
        try:
            vr = _retry_request(
                "get",
                f"{_api_base()}/issues/{issue_id}",
                headers=headers,
                timeout=15,
            )
            if vr.ok:
                vbody = vr.json()
                if not (vbody.get("id") == issue_id and vbody.get("identifier") == identifier):
                    raise RuntimeError(
                        f"create_stall_issue: server returned 201 with {identifier} "
                        f"but issue did not persist (silent rollback detected)"
                    )
            elif vr.status_code == 404:
                raise RuntimeError(
                    f"create_stall_issue: server returned 201 with {identifier} "
                    f"but GET /api/issues/{issue_id} returned 404 (silent rollback detected)"
                )
            else:
                raise RuntimeError(
                    f"create_stall_issue: verification GET for {issue_id} "
                    f"returned HTTP {vr.status_code} — cannot confirm issue {identifier} persisted; "
                    f"caller MUST buffer this child for retry"
                )
        except requests.RequestException:
            raise RuntimeError(
                f"create_stall_issue: verification GET for {issue_id} failed "
                f"(verification errored) — cannot confirm issue {identifier} persisted; "
                f"caller MUST buffer this child for retry"
            )

        # BUY-61439: secondary verification — list parent children and confirm
        # the identifier appears in the list. This is advisory only: the list
        # endpoint can lag or paginate/filter inconsistently under load, while
        # direct GET by id is the authoritative persistence check.
        try:
            lr = _retry_request(
                "get",
                f"{_api_base()}/companies/{COMPANY_ID}/issues",
                params={"parentId": PARENT_ISSUE_ID, "limit": 100},
                headers=headers,
                timeout=20,
            )
            if lr.ok:
                lbody = lr.json()
                lissues = lbody if isinstance(lbody, list) else lbody.get("issues", [])
                found = any(
                    issue.get("id") == issue_id and issue.get("identifier") == identifier
                    for issue in lissues
                )
                if not found:
                    print(
                        f"[throughput-dispatcher] create_stall_issue: secondary verification "
                        f"did not find {identifier} in parent listing — continuing because "
                        f"direct GET confirmed persistence"
                    )
            else:
                print(
                    f"[throughput-dispatcher] create_stall_issue: secondary verification "
                    f"GET returned HTTP {lr.status_code} — skipping (issue {identifier} "
                    f"confirmed via direct GET already)"
                )
        except requests.RequestException as _sec_exc:
            print(
                f"[throughput-dispatcher] create_stall_issue: secondary verification "
                f"failed ({_sec_exc.__class__.__name__}: {_sec_exc}) — issue {identifier} "
                f"confirmed via direct GET already, continuing"
            )

    return identifier


def build_run_note(
    *,
    hour_start: datetime,
    hour_end: datetime,
    result: str,
    real_rows: int,
    source: str,
    delta_rows: int | None,
    stat: dict[str, Any],
    pm_start: str | None,
    failure_identifier: str | None,
    stat_reset_detected: bool | None,
    live_count_delta: int | None,
    n_live_tup_delta: int | None = None,
) -> str:
    parts = [
        (
            f"{hour_start:%Y-%m-%d %H:%M}-{hour_end:%H:%M}Z hour {result}: "
            f"{real_rows:,}/hr via {source}."
        )
    ]
    if delta_rows is not None:
        parts.append(f"n_tup_ins delta {delta_rows:,} over 1.000h = {real_rows:,}/hr.")
    else:
        parts.append("n_tup_ins delta unavailable.")
    if stat_reset_detected:
        parts.append("stat_reset_detected=True.")
    if live_count_delta is not None:
        parts.append(f"live_count delta {live_count_delta:,}.")
    if n_live_tup_delta is not None:
        parts.append(f"n_live_tup delta {n_live_tup_delta:,}.")
    parts.append(
        f"n_tup_ins={stat.get('n_tup_ins', 0):,}, n_live_tup={stat.get('n_live_tup', 0):,}."
    )
    if pm_start:
        parts.append(f"pm_start={pm_start}.")
    if failure_identifier:
        parts.append(f"Filed child {failure_identifier} under BUY-29861.")
    else:
        parts.append("No child filed.")
    return " ".join(parts)


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
        if not is_completed_hour(hour_start, now):
            print(
                "ERROR: --check-hour must target a completed UTC hour "
                f"(got {hour_start.isoformat()} → "
                f"{(hour_start + timedelta(hours=1)).isoformat()}, "
                f"now={now.isoformat()})"
            )
            return 2
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
    failure_identifier = None

    # BUY-53341: retry any pending children buffered from a previous API outage
    # before proceeding with the current hour's check.
    if not args.dry_run:
        retried = _retry_pending_children(state)
        if retried:
            print(f"[throughput-dispatcher] RETRY filed {len(retried)} previously-buffered children: {', '.join(retried)}")
            # BUY-59705: buffered retries are the only place we file a failure
            # child for an already-recorded hour, so update the latest failure
            # pointer to match the most recent retry.
            state["last_failure_child_identifier"] = retried[-1]
        if state.get("pending_children"):
            print(f"[throughput-dispatcher] RETRY still pending: {len(state['pending_children'])} child(ren) remain unbuffered")
        # BUY-59705: persist the drained pending_children list before any
        # early-exit path can return without saving state.
        save_state(state)

    # BUY-52603 fix: the prior exit-early check `(hour_start + 1h) > now` caused the
    # dispatcher to exit when it ran AT the hour boundary (window just closed but
    # condition was still true), and also fired for the wrong window when
    # source_scoped_recovery_action woke it mid-hour. The correct behaviour is:
    #   - Dedup is the sole mechanism for preventing double-fires in the same hour
    #   - We ALWAYS check the just-completed hour (hour_start = now - 1h, zeroed)
    #     regardless of wall-clock time; late-arriving data is handled by the
    #     ~30-second psql statement_timeout floor
    #   - The ONLY early-exit right is the dedup check below
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
            conn = connect_catalog(db_url)
            if conn is None:
                return 2
            stat = read_pg_stat_products(conn)
            pm_start = query_postmaster_start_time(conn)
            conn.close()
            if stat:
                state["last_n_tup_ins"] = stat.get("n_tup_ins")
                state["last_n_tup_ins_at"] = now.isoformat()
                state["last_hour_checked"] = hour_start.isoformat()
                state["last_check_result"] = "DEDUP"
                state["last_check_source"] = "n_tup_ins"
                state["last_n_live_tup"] = stat.get("n_live_tup")
                state["last_db_host"] = db_host
                state["last_hour_window_start"] = hour_start.isoformat()
                state["last_hour_window_end"] = (hour_start + timedelta(hours=1)).isoformat()
                state["last_check_threshold"] = TARGET_ROWS_PER_HOUR
                state["last_check_delta_rows"] = None
                state["last_check_delta_hours"] = None
                state["last_check_rate"] = None
                state["last_pm_start"] = pm_start
                state["last_fire_timestamp"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
                state["last_issue_identifier"] = None
                state["last_note"] = (
                    f"{hour_start:%Y-%m-%d %H:%M}-{(hour_start + timedelta(hours=1)):%H:%M}Z "
                    "hour already had a failure child filed under BUY-29861; "
                    "refreshed n_tup_ins baseline only."
                )
                save_state(state)
        except Exception as e:
            print(f"[throughput-dispatcher] baseline refresh failed: {e}")
        return 0

    conn = connect_catalog(db_url)
    if conn is None:
        return 2
    try:
        # PRIMARY: pg_stat (fast).
        try:
            stat = read_pg_stat_products(conn)
        except psycopg2.errors.QueryCanceled:
            conn.rollback()
            print(
                "[throughput-dispatcher] FATAL: pg_stat_user_tables.products timed out "
                f"after {STMT_TIMEOUT_FAST_S}s and {STMT_TIMEOUT_FAST_RETRY_S}s retries"
            )
            return 2
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
        elif hour_data and hour_data.get("error") == "statement_timeout":
            print(
                f"[throughput-dispatcher] hour_bucket_count: TIMEOUT after {hour_data['timeout_s']}s "
                "(maglev contention — using n_tup_ins delta only)"
            )
        elif hour_data and hour_data.get("error") == "connection_lost":
            print(
                "[throughput-dispatcher] hour_bucket_count: connection lost during COUNT "
                "(using n_tup_ins delta only)"
            )
        else:
            print("[throughput-dispatcher] hour_bucket_count: returned None")

        # Snapshot for staleness (best-effort).
        conn = reconnect_if_needed(conn, db_url)
        max_created = query_max_created_at(conn)
        pm_start = query_postmaster_start_time(conn)

        # --- v6 (BUY-59232): canonical upsert FIRST, then v6 decision layer ---
        # BUY-58485 v4: upsert this tick's stats + ingestion_runs aggregates
        # into canonical_throughput_hourly so the per-hour delta can be
        # computed from the table directly (n_tup_ins delta) instead of
        # only from data/.throughput_state.json. Best-effort: a failed
        # upsert does not block the dispatcher's PASS/FAIL decision.
        canonical_upsert = {}
        try:
            conn = reconnect_if_needed(conn, db_url)
            canonical_upsert = upsert_canonical_throughput_row(
                conn=conn,
                hour_start=hour_start,
                stat=stat,
                pm_start=pm_start,
                hour_data=hour_data,
                source="v6",
                note="v6 decision layer active",
            )
            if canonical_upsert.get("upserted"):
                print(
                    f"[throughput-dispatcher] canonical_throughput_hourly "
                    f"upserted for hour_start={canonical_upsert['hour_start']} "
                    f"(live_count={canonical_upsert.get('live_count')}, "
                    f"ing_inserted={canonical_upsert.get('ing_inserted')})"
                )
            else:
                print(
                    "[throughput-dispatcher] canonical_throughput_hourly "
                    f"upsert skipped: {canonical_upsert.get('note')}"
                )
        except Exception as _e:
            print(
                "[throughput-dispatcher] canonical_throughput_hourly upsert "
                f"raised: {_e.__class__.__name__}: {_e}"
            )

        # --- v6 decision layer (BUY-59232, rules 5a-5d, 6) ---
        delta_ins_from_stats = canonical_upsert.get("delta_ins_from_stats")
        delta_upd_from_stats = canonical_upsert.get("delta_upd_from_stats")
        stat_reset_detected = canonical_upsert.get("stat_reset_detected")
        canonical_ing_inserted = canonical_upsert.get("ing_inserted", 0)
        previous_n_tup_ins = canonical_upsert.get("previous_n_tup_ins")

        # A missing immediate-prior canonical row means this tick is only a
        # baseline capture. Never treat the current absolute pg_stat counter as
        # hourly throughput; doing so can turn first-row/backfill gaps into a
        # massive false PASS (for example 202M/hr at midnight).
        missing_prior_baseline = (
            canonical_upsert.get("upserted")
            and previous_n_tup_ins is None
            and canonical_upsert.get("n_tup_ins") is not None
            and delta_ins_from_stats == canonical_upsert.get("n_tup_ins")
        )
        if missing_prior_baseline:
            delta_ins_from_stats = None
            delta_upd_from_stats = None
            stat_reset_detected = None
            canonical_upsert["delta_ins_from_stats"] = None
            canonical_upsert["delta_upd_from_stats"] = None
            canonical_upsert["stat_reset_detected"] = None
            print(
                "[throughput-dispatcher] canonical baseline only: missing "
                "immediate prior hour row; ignoring absolute n_tup_ins counter "
                "for this decision"
            )

        # live_count delta from canonical_throughput_hourly (v6 fall-back #2)
        live_count_delta = None
        if canonical_upsert.get("upserted"):
            try:
                conn = reconnect_if_needed(conn, db_url)
                with conn.cursor() as _lc_cur:
                    _lc_cur.execute("SET statement_timeout = '10s'")
                    _lc_cur.execute(
                        """
                        SELECT live_count FROM canonical_throughput_hourly
                        WHERE hour_start = %s - INTERVAL '1 hour'
                        """,
                        (hour_start,),
                    )
                    _lc_prv = _lc_cur.fetchone()
                conn.rollback()
                if _lc_prv is not None and canonical_upsert.get("live_count") is not None:
                    if _lc_prv[0] is not None:
                        live_count_delta = canonical_upsert["live_count"] - int(_lc_prv[0])
            except (psycopg2.errors.QueryCanceled, psycopg2.OperationalError, psycopg2.InterfaceError):
                conn.rollback()

        # v6.2 (BUY-60573): n_live_tup delta from canonical_throughput_hourly.
        # This is the pg_stat_user_tables live-tuple *estimate*, always
        # available (no count(*) scan) and updated by ANALYZE. When the
        # authoritative delta_ins_from_stats is stale/lagged but n_live_tup
        # grew by >= 150K, real inserts demonstrably happened — the hard guard
        # blocks a false-positive FAIL.
        n_live_tup_delta = None
        if canonical_upsert.get("upserted"):
            try:
                conn = reconnect_if_needed(conn, db_url)
                with conn.cursor() as _nlt_cur:
                    _nlt_cur.execute("SET statement_timeout = '10s'")
                    _nlt_cur.execute(
                        """
                        SELECT n_live_tup, n_tup_ins FROM canonical_throughput_hourly
                        WHERE hour_start = %s - INTERVAL '1 hour'
                        """,
                        (hour_start,),
                    )
                    _nlt_prv = _nlt_cur.fetchone()
                conn.rollback()
                cur_nlt = canonical_upsert.get("n_live_tup")
                if _nlt_prv is not None and cur_nlt is not None and _nlt_prv[0] is not None:
                    n_live_tup_delta = int(cur_nlt) - int(_nlt_prv[0])
                if previous_n_tup_ins is None and _nlt_prv is not None and _nlt_prv[1] is not None:
                    previous_n_tup_ins = int(_nlt_prv[1])
            except (psycopg2.errors.QueryCanceled, psycopg2.OperationalError, psycopg2.InterfaceError):
                conn.rollback()

        # 5a: delta_ins_from_stats is the PRIMARY and ONLY authoritative signal.
        # 5b: 150K hard guard on delta_ins_from_stats AND live_count delta.
        # 5c: ingestion_runs.ing_inserted is OBSERVABILITY ONLY — never primary.
        # 5d: Fail only when ALL signals are unavailable or below 150K.
        # 6:  Forbidden patterns enforced by assertions below.
        real_rows, source = select_v6_throughput_signal(
            delta_ins_from_stats=delta_ins_from_stats,
            canonical_ing_inserted=canonical_ing_inserted,
            live_count_delta=live_count_delta,
            n_live_tup_delta=n_live_tup_delta,
        )
        note = (f"v6 metric: source={source}, delta_ins={delta_ins_from_stats}, "
                f"live_count_delta={live_count_delta}, n_live_tup_delta={n_live_tup_delta}")

        # --- v6 forbidden-pattern assertions (spec rule 6) ---
        # These run on every tick (including --dry-run) and raise AssertionError
        # with a clear message naming the violated rule. They never fire under
        # the steady-state metrics path; they exist to catch the v4 regression
        # classes documented in BUY-59214 / BUY-59220.
        assert_v6_forbidden_patterns(
            delta_ins_from_stats=delta_ins_from_stats,
            delta_upd_from_stats=delta_upd_from_stats,
            real_rows=real_rows,
            source=source,
            live_count_delta=live_count_delta,
            current_n_tup_ins=canonical_upsert.get("n_tup_ins"),
            previous_n_tup_ins=previous_n_tup_ins,
        )
        # Rule 5b invariant: if delta_ins_from_stats is non-null and >= 150K, the
        # chosen real_rows must be >= 150K. Same for live_count delta.
        # EXCEPTION (v6.3 BUY-60953): stats_mismatch_ingestion_runs_guard
        # deliberately returns real_rows < target when pg_stat counter is
        # unreliable and ing_inserted shows a genuine miss.
        if (
            delta_ins_from_stats is not None
            and delta_ins_from_stats >= TARGET_ROWS_PER_HOUR
            and real_rows < TARGET_ROWS_PER_HOUR
            and source != "stats_mismatch_ingestion_runs_guard"
        ):
            raise AssertionError(
                "v6 rule 5(b) violation: delta_ins_from_stats >= 150K but "
                f"real_rows={real_rows} < {TARGET_ROWS_PER_HOUR}. The 150K hard guard "
                "on stats delta must force a PASS."
            )
        if (
            live_count_delta is not None
            and live_count_delta >= TARGET_ROWS_PER_HOUR
            and real_rows < TARGET_ROWS_PER_HOUR
        ):
            raise AssertionError(
                "v6 rule 5(b) violation: live_count_delta >= 150K but "
                f"real_rows={real_rows} < {TARGET_ROWS_PER_HOUR}. The 150K hard guard "
                "on live_count delta must force a PASS."
            )
        is_signal_unavailable = source == "unavailable"
        pct = 100.0 * real_rows / TARGET_ROWS_PER_HOUR
        print(
            f"[throughput-dispatcher] real_rows={real_rows:,} "
            f"target={TARGET_ROWS_PER_HOUR:,} ({pct:.1f}%) source={source}"
        )

        # v6 first-baseline detection: a true first tick has NO canonical row at
        # hour_start - 1h (so both delta_ins_from_stats and live_count_delta are
        # None) AND no prior n_tup_ins reading in state. On first tick we capture
        # the baseline and exit without filing — otherwise we'd file a false
        # "stall" on a healthy fleet just because we haven't seen a prior reading.
        is_first_baseline = (
            state.get("last_n_tup_ins") is None
            and delta_ins_from_stats is None
            and live_count_delta is None
        )
        should_file_failure_ticket = should_file_v6_failure_ticket(
            delta_ins_from_stats=delta_ins_from_stats,
            canonical_ing_inserted=canonical_ing_inserted,
            live_count_delta=live_count_delta,
            n_live_tup_delta=n_live_tup_delta,
        )

        if args.dry_run:
            print("[throughput-dispatcher] --dry-run: would NOT call the Paperclip API")
            if is_first_baseline:
                print(
                    "  BASELINE_CAPTURE: persisting n_tup_ins as the first reading; "
                    "no issue filed this run."
                )
            elif is_signal_unavailable:
                print("  SKIP: no reliable throughput signal available this hour; no issue would be filed.")
            else:
                print(
                    f"  PASS={not should_file_failure_ticket} → "
                    f"{'would file under BUY-29861' if should_file_failure_ticket else 'no-op'}"
                )
        else:
            if is_first_baseline:
                print(
                    "[throughput-dispatcher] BASELINE_CAPTURE: no prior n_tup_ins "
                    "reading — persisting baseline and skipping the file/no-file decision "
                    "this run. The next hour's run will compute the delta."
                )
            elif is_signal_unavailable:
                print(
                    "[throughput-dispatcher] SKIP: throughput signal unavailable; "
                    "persisting baseline only and not filing a child issue."
                )
            elif should_file_failure_ticket and real_rows < TARGET_ROWS_PER_HOUR and not args.force:
                try:
                    failure_identifier = create_stall_issue(
                        hour_start, real_rows, source, note,
                        hour_data, stat, max_created, db_host, fire_ts,
                    )
                    print(f"[throughput-dispatcher] FAIL — filed {failure_identifier} under BUY-29861")
                    write_evidence_markdown(
                        hour_start, real_rows, source, note,
                        hour_data, stat, max_created, db_host, fire_ts,
                        failure_child_identifier=failure_identifier,
                        stat_reset_detected=stat_reset_detected,
                        ingestion_counts={
                            "ing_runs": canonical_upsert.get("ing_runs"),
                            "ing_inserted": canonical_upsert.get("ing_inserted"),
                            "ing_updated": canonical_upsert.get("ing_updated"),
                        },
                    )
                except Exception as e:
                    print(f"[throughput-dispatcher] FAIL — create_stall_issue failed: {e.__class__.__name__}: {e}")
                    # BUY-53341: buffer the failure for retry on the next fire.
                    # BUY-61439: include hour_start iso explicitly in the buffer entry
                    # for reliable retry parsing.
                    pending = state.setdefault("pending_children", [])
                    pending.append({
                        "hour_start_iso": hour_start.isoformat(),
                        "hour_start": hour_start.isoformat(),
                        "real_rows": real_rows,
                        "source": source,
                        "note": note,
                        "hour_data": hour_data,
                        "stat": stat,
                        "max_created": max_created,
                        "db_host": db_host,
                        "fire_ts": fire_ts,
                    })
                    state["pending_children"] = pending
                    print(f"[throughput-dispatcher] FAIL — buffered child for {hour_start.isoformat()} "
                          f"(real_rows={real_rows}) in pending_children "
                          f"({len(pending)} pending total)")
                    failure_identifier = None
            elif args.force and real_rows < TARGET_ROWS_PER_HOUR:
                # --force on a real FAIL: correctly report the actual result
                print(f"[throughput-dispatcher] FAIL (--force override — no issue filed): {real_rows:,} < {TARGET_ROWS_PER_HOUR:,}")
            elif real_rows >= TARGET_ROWS_PER_HOUR:
                print(f"[throughput-dispatcher] PASS — {real_rows:,} >= {TARGET_ROWS_PER_HOUR:,} (source={source}). No issue filed.")
                post_parent_pass_comment(hour_start, real_rows, source)
                write_evidence_markdown(
                    hour_start, real_rows, source, note,
                    hour_data, stat, max_created, db_host, fire_ts,
                    stat_reset_detected=stat_reset_detected,
                    ingestion_counts={
                        "ing_runs": canonical_upsert.get("ing_runs"),
                        "ing_inserted": canonical_upsert.get("ing_inserted"),
                        "ing_updated": canonical_upsert.get("ing_updated"),
                    },
                )
            else:
                # Below-target readings only reach this branch when every filing
                # path is suppressed by an explicit guard or unavailable signal.
                print(
                    f"[throughput-dispatcher] BELOW_TARGET — {real_rows:,} < {TARGET_ROWS_PER_HOUR:,} "
                    f"(source={source}). No failure child filed: guarded by v6 hard-pass logic."
                )

        if args.dry_run:
            print("[throughput-dispatcher] dry-run: leaving data/.throughput_state.json unchanged")
        else:
            # Persist the new n_tup_ins baseline and result for the next run.
            # `last_n_tup_ins_at` is the wall-clock time of THIS reading; the next
            # run's delta is then (next_now - this_now), which is the actual
            # elapsed time between the two fires and gives the correct per-hour
            # rate regardless of how often the dispatcher is invoked.
            state["last_n_tup_ins"] = stat.get("n_tup_ins")
            state["last_n_tup_ins_at"] = now.isoformat()
            state["last_hour_checked"] = hour_start.isoformat()
            # v6 fail-only filing means the result categories are not binary:
            #   PASS         — real_rows >= target (or guard upgraded via
            #                   n_live_tup_delta / live_count_delta)
            #   FAIL         — real_rows < target AND v6 rule 5a/5d opened a child
            #   BELOW_TARGET — real_rows < target but an explicit v6 hard-pass
            #                   guard or unavailable signal suppressed filing.
            #   BASELINE     — first-ever tick, no prior reading
            #   ERROR        — throughput signal unavailable
            state["last_check_result"] = (
                "BASELINE" if is_first_baseline
                else "ERROR" if is_signal_unavailable
                else "PASS" if real_rows >= TARGET_ROWS_PER_HOUR
                else "FAIL" if should_file_failure_ticket
                else "BELOW_TARGET"
            )
            state["last_check_real_rows"] = real_rows
            state["last_check_source"] = source
            state["last_n_live_tup"] = stat.get("n_live_tup")
            state["last_db_host"] = db_host
            state["last_hour_window_start"] = hour_start.isoformat()
            state["last_hour_window_end"] = (hour_start + timedelta(hours=1)).isoformat()
            state["last_check_threshold"] = TARGET_ROWS_PER_HOUR
            state["last_check_delta_rows"] = delta_ins_from_stats
            state["last_check_delta_hours"] = None
            state["last_check_rate"] = real_rows
            state["last_pm_start"] = pm_start
            state["last_fire_timestamp"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            state["last_issue_identifier"] = failure_identifier
            if failure_identifier:
                state["last_failure_child_identifier"] = failure_identifier
            run_result = state["last_check_result"]
            state["last_note"] = build_run_note(
                hour_start=hour_start,
                hour_end=hour_start + timedelta(hours=1),
                result=run_result,
                real_rows=real_rows,
                source=source,
                delta_rows=delta_ins_from_stats,
                stat=stat,
                pm_start=pm_start,
                failure_identifier=failure_identifier,
                stat_reset_detected=stat_reset_detected,
                live_count_delta=live_count_delta,
                n_live_tup_delta=n_live_tup_delta,
            )
            save_state(state)
    finally:
        conn.close()

    # BUY-39805: capture the midnight-boundary n_tup_ins snapshot if the
    # dispatcher's fire crossed a UTC day boundary. Safe to call every fire;
    # the function is a no-op when no boundary was crossed.
    try:
        import importlib.util as _ilu

        _ms_path = Path(__file__).resolve().parent / "midnight_snapshot.py"
        _spec = _ilu.spec_from_file_location("midnight_snapshot", _ms_path)
        _ms_mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_ms_mod)
        snapshot = _ms_mod.capture_closed_day_snapshot(
            fire_issue_identifier=state.get("last_issue_identifier"),
            dry_run=args.dry_run,
        )
        if snapshot is not None:
            print(
                f"[throughput-dispatcher] midnight-snapshot recorded: "
                f"closed_day={snapshot['date']} delta={snapshot['delta']:+,}"
            )
    except Exception as e:
        # Never let midnight-snapshot failure block the dispatcher's result.
        print(
            f"[throughput-dispatcher] midnight-snapshot call failed: "
            f"{e.__class__.__name__}: {e}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
