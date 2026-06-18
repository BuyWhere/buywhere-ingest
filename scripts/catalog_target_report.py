#!/usr/bin/env python3
"""Report the canonical catalog DB target vs harness DB env for BUY-29210."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ingestion_guard import configured_database_targets


def _describe_host(url: str) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    database = parsed.path.lstrip("/")
    return f"{host}{port}/{database}" if host else parsed.path.lstrip("/") or None


def main() -> int:
    targets = configured_database_targets()
    catalog_host = _describe_host(targets["catalog_pin_url"])
    harness_host = _describe_host(targets["harness_database_url"])
    print(
        json.dumps(
            {
                **targets,
                "catalog_pin_host": catalog_host,
                "harness_database_host": harness_host,
                "active_database_host": _describe_host(targets["active_database_url"]),
                "surfaces_diverge": bool(
                    targets["catalog_pin_url"]
                    and targets["harness_database_url"]
                    and targets["catalog_pin_url"] != targets["harness_database_url"]
                ),
                "note": (
                    "Repo-local catalog writers use active_database_url. "
                    "When catalog_pin_url is set, treat harness_database_url as stale secondary context."
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
