#!/usr/bin/env python3
"""Ingestion target resolver + write guard — BUY-22332.

Two responsibilities:

1. `database_url()` — resolve the ingestion target DB URL. Prefers
   `data/.catalog_db_url` (a workspace-level pin) over the harness-injected
   `DATABASE_URL` env var. The harness sets `DATABASE_URL` to the Paperclip
   control-plane DB and is outside our control; the catalog DB file is how
   we durably repoint ingestion without changing the harness.

2. `check_ingestion_allowed()` / `assert_ingestion_allowed()` — refuse
   product/merchant writes when EITHER:
     - the manual hold file `data/INGESTION_HOLD` exists, or
     - the resolved URL points at the Paperclip control-plane DB.

   The control-plane DB is identified by its table fingerprint (agents,
   companies, approvals, board_api_keys, budget_policies), not by host
   string — so the guard keeps working regardless of URL spelling.

Data-team ingestion must never write into the platform DB. The fingerprint
check is a permanent safety net even after the repoint.
"""

import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLD_FILE = os.path.join(_REPO_ROOT, "data", "INGESTION_HOLD")
_CATALOG_DB_URL_FILE = os.path.join(_REPO_ROOT, "data", ".catalog_db_url")

_CONTROL_PLANE_TABLES = (
    "agents",
    "companies",
    "approvals",
    "board_api_keys",
    "budget_policies",
)
_CONTROL_PLANE_THRESHOLD = 3


class IngestionHoldError(RuntimeError):
    """Raised when ingestion writes are not permitted."""


def database_url():
    """Resolve the ingestion target DB URL."""
    if os.path.exists(_CATALOG_DB_URL_FILE):
        with open(_CATALOG_DB_URL_FILE) as fh:
            url = fh.read().strip()
        if url:
            return url
    return os.environ.get("DATABASE_URL", "")


def configured_database_targets():
    """Return the configured catalog-pin and harness DB URLs."""
    catalog_pin_url = ""
    if os.path.exists(_CATALOG_DB_URL_FILE):
        with open(_CATALOG_DB_URL_FILE) as fh:
            catalog_pin_url = fh.read().strip()
    harness_db_url = os.environ.get("DATABASE_URL", "")
    return {
        "catalog_pin_path": _CATALOG_DB_URL_FILE,
        "catalog_pin_url": catalog_pin_url,
        "harness_database_url": harness_db_url,
        "active_database_url": catalog_pin_url or harness_db_url,
    }


def _control_plane_table_count(db_url):
    in_list = ",".join("'%s'" % t for t in _CONTROL_PLANE_TABLES)
    sql = (
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name IN (%s);" % in_list
    )
    try:
        out = subprocess.run(
            ["psql", db_url, "-tAc", sql],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        raise IngestionHoldError(
            "Could not verify the ingestion target DB is safe: %s" % exc
        )
    if out.returncode != 0:
        raise IngestionHoldError(
            "Could not verify the ingestion target DB is safe: %s"
            % out.stderr.strip()[:200]
        )
    try:
        return int(out.stdout.strip())
    except ValueError:
        raise IngestionHoldError(
            "Could not parse control-plane table check result: %r"
            % out.stdout.strip()[:200]
        )


def check_ingestion_allowed(db_url=None):
    """Return None if ingestion writes are allowed, else raise IngestionHoldError."""
    if os.path.exists(HOLD_FILE):
        with open(HOLD_FILE) as fh:
            reason = fh.read().strip()
        raise IngestionHoldError(
            "Ingestion hold active — %s\n%s" % (HOLD_FILE, reason)
        )

    db_url = db_url or database_url()
    if not db_url:
        raise IngestionHoldError(
            "No ingestion target DB URL — set data/.catalog_db_url or DATABASE_URL"
        )

    matched = _control_plane_table_count(db_url)
    if matched >= _CONTROL_PLANE_THRESHOLD:
        raise IngestionHoldError(
            "Refusing to write: the resolved ingestion DB URL points at the "
            "Paperclip control-plane production DB (matched %d/%d control-plane "
            "tables). Data-team ingestion must not write into the platform DB. "
            "Pin the dedicated catalog DB URL in data/.catalog_db_url. "
            "See BUY-22332." % (matched, len(_CONTROL_PLANE_TABLES))
        )


def assert_ingestion_allowed(db_url=None):
    """Exit the process if ingestion writes are blocked; return otherwise."""
    try:
        check_ingestion_allowed(db_url)
    except IngestionHoldError as exc:
        sys.stderr.write(
            "\n[ingestion-guard] BLOCKED — no rows written.\n%s\n\n" % exc
        )
        sys.exit(3)
    sys.stderr.write("[ingestion-guard] OK — ingestion target verified safe.\n")


if __name__ == "__main__":
    assert_ingestion_allowed()
