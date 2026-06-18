#!/usr/bin/env python3
"""Emergency canonical catalog writer for BUY-29199.

Upserts NDJSON product artifacts into the pinned canonical catalog DB using the
existing ingestion guard. This is a narrow recovery tool for verified merchant
artifacts when the normal writer path is unavailable or misrouted.

After a successful catalog upsert AND a Cloudflare R2 upload of the raw file,
writes a per-file completion marker (`<file>.ingested.json`) so the
safe-data-cleanup.sh routine (Gate B) can confirm ingest without falling back
to the slow 100-URL catalog sample. See BUY-33089 / DATA_CLEANUP_PROTOCOL.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ingested_marker import finalize_marker, r2_configured
from scripts.ingestion_guard import assert_ingestion_allowed, database_url
from src.catalog_ingest import upsert_products


MERCHANT_DEFAULTS: dict[str, dict[str, str]] = {
    "paper_source": {
        "merchant_id": "paper_source",
        "source": "paper_source",
        "platform": "shopify",
        "region": "US",
        "country_code": "US",
        "currency": "USD",
    },
    "floor_and_decor": {
        "merchant_id": "floor_and_decor",
        "source": "floor_and_decor",
        "platform": "custom",
        "region": "US",
        "country_code": "US",
        "currency": "USD",
    },
    "the_body_shop": {
        "merchant_id": "the_body_shop",
        "source": "the_body_shop",
        "platform": "shopify",
        "region": "UK",
        "country_code": "GB",
        "currency": "GBP",
    },
    "woocommerce": {
        "merchant_id": "woocommerce",
        "source": "woocommerce",
        "platform": "woocommerce",
        "region": "US",
        "country_code": "US",
        "currency": "USD",
    },
    "courts_sg": {
        "merchant_id": "courts_sg",
        "source": "courts_sg",
        "platform": "custom",
        "region": "SG",
        "country_code": "SG",
        "currency": "SGD",
    },
    "guardian_sg": {
        "merchant_id": "guardian_sg",
        "source": "guardian_sg",
        "platform": "custom",
        "region": "SG",
        "country_code": "SG",
        "currency": "SGD",
    },
    "zalora_sg": {
        "merchant_id": "zalora_sg",
        "source": "zalora_sg",
        "platform": "custom",
        "region": "SG",
        "country_code": "SG",
        "currency": "SGD",
    },
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("merchant_key", choices=sorted(MERCHANT_DEFAULTS))
    parser.add_argument("ndjson_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-marker",
        action="store_true",
        help=(
            "Do not write the per-file .ingested.json marker after ingest. "
            "Useful when running ad-hoc re-ingestion and you do not want to "
            "claim confirmation for the cleanup protocol."
        ),
    )
    parser.add_argument(
        "--lenient-marker",
        action="store_true",
        help=(
            "Write the marker even if R2 is not configured (records "
            "r2Uploaded=false). Defaults to strict mode: R2 must succeed."
        ),
    )
    return parser.parse_args()


def _normalize_product(merchant_key: str, raw_line: str) -> dict[str, Any]:
    payload = json.loads(raw_line)
    defaults = MERCHANT_DEFAULTS[merchant_key]
    raw_data = payload.get("raw_data") or {}
    payload["merchant_id"] = defaults["merchant_id"]
    payload["source"] = defaults["source"]
    payload["platform"] = defaults["platform"]
    payload["region"] = defaults["region"]
    payload["country_code"] = defaults["country_code"]
    payload["currency"] = payload.get("currency") or defaults["currency"]
    payload["description"] = payload.get("description") or raw_data.get("description")
    return payload


def _load_products(merchant_key: str, ndjson_path: Path) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    with ndjson_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            products.append(_normalize_product(merchant_key, line))
    return products


def main() -> int:
    args = _parse_args()
    assert_ingestion_allowed()
    products = _load_products(args.merchant_key, args.ndjson_path)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "merchant_key": args.merchant_key,
                    "ndjson_path": str(args.ndjson_path),
                    "rows": len(products),
                    "database_url": database_url(),
                    "r2_configured": r2_configured(),
                    "dry_run": True,
                },
                indent=2,
            )
        )
        return 0

    record_count = len(products)
    inserted = upsert_products(
        products,
        source=MERCHANT_DEFAULTS[args.merchant_key]["source"],
        merchant_id=MERCHANT_DEFAULTS[args.merchant_key]["merchant_id"],
        defaults=MERCHANT_DEFAULTS[args.merchant_key],
        metadata_tag={
            "issue": "BUY-29199",
            "merchant_key": args.merchant_key,
            "path": "scripts/emergency_catalog_ingest.py",
        },
        db_url=database_url(),
    )

    marker_summary: dict[str, Any] | None = None
    if not args.skip_marker and inserted > 0:
        partial_errors = max(0, record_count - inserted)
        marker_summary = finalize_marker(
            args.ndjson_path,
            record_count=record_count,
            inserted=inserted,
            errors=partial_errors,
            writer="emergency_catalog_ingest.py:BUY-29199",
            require_r2=not args.lenient_marker,
        )
    elif args.skip_marker:
        marker_summary = {"skipped": "--skip-marker"}

    payload = {
        "merchant_key": args.merchant_key,
        "ndjson_path": str(args.ndjson_path),
        "record_count": record_count,
        "rows_written": inserted,
        "rows_skipped": max(0, record_count - inserted),
        "partial": bool(marker_summary and marker_summary.get("partial")),
        "database_url": database_url(),
        "marker": marker_summary,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if marker_summary and marker_summary.get("partial"):
        print(
            f"WARNING: partial ingest — {payload['rows_skipped']} of {record_count} records were not upserted. "
            f"Marker written with ingest.partial=true so Gate B retains the file for re-drive.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
