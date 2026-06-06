#!/usr/bin/env python3
"""Ingest brand-direct SG NDJSON artifacts into the canonical catalog DB.

After each successful upsert AND Cloudflare R2 upload, writes a per-file
completion marker (`<file>.ingested.json`) so the safe-data-cleanup.sh
routine (Gate B) can confirm ingest without falling back to the slow
100-URL catalog sample. See BUY-33089 / DATA_CLEANUP_PROTOCOL.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ingested_marker import finalize_marker
from src.catalog_ingest import upsert_products


def load_ndjson(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apple-path",
        type=Path,
        default=REPO_ROOT / "merchants" / "apple_sg_buy_xml_full_2026-06-06.ndjson",
    )
    parser.add_argument(
        "--samsung-path",
        type=Path,
        default=REPO_ROOT / "merchants" / "samsung_sg_sitemap_full_2026-06-06.ndjson",
    )
    parser.add_argument(
        "--skip-marker",
        action="store_true",
        help="Do not write the per-file .ingested.json marker after ingest.",
    )
    parser.add_argument(
        "--lenient-marker",
        action="store_true",
        help="Write the marker even if R2 is not configured (records r2Uploaded=false).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    db_url = (REPO_ROOT / "data" / ".catalog_db_url").read_text().strip()

    apple_path: Path = args.apple_path
    samsung_path: Path = args.samsung_path

    apple_records = load_ndjson(apple_path)
    samsung_records = load_ndjson(samsung_path)

    print(f"Apple records:   {len(apple_records)} ({apple_path})")
    print(f"Samsung records: {len(samsung_records)} ({samsung_path})")

    apple_defaults = {
        "source": "apple_sg_buy_xml",
        "merchant_id": "apple_sg",
        "platform": "direct_http",
        "region": "SG",
        "country_code": "SG",
        "currency": "SGD",
        "is_active": True,
        "in_stock": True,
    }
    samsung_defaults = {
        "source": "samsung_sg_sitemap",
        "merchant_id": "samsung_sg",
        "platform": "direct_http",
        "region": "SG",
        "country_code": "SG",
        "currency": "SGD",
        "is_active": True,
        "in_stock": True,
    }

    apple_tag = {
        "issue": "BUY-32061",
        "path": "scripts/ingest_brand_direct_sg.py",
        "mode": "full_drain",
    }
    samsung_tag = {
        "issue": "BUY-32061",
        "path": "scripts/ingest_brand_direct_sg.py",
        "mode": "full_drain",
    }

    apple_written = upsert_products(
        apple_records,
        source="apple_sg_buy_xml",
        merchant_id="apple_sg",
        defaults=apple_defaults,
        metadata_tag=apple_tag,
        db_url=db_url,
    )
    print(f"Apple upserted: {apple_written} rows")

    samsung_written = upsert_products(
        samsung_records,
        source="samsung_sg_sitemap",
        merchant_id="samsung_sg",
        defaults=samsung_defaults,
        metadata_tag=samsung_tag,
        db_url=db_url,
    )
    print(f"Samsung upserted: {samsung_written} rows")
    print(f"Total: {apple_written + samsung_written}")

    marker_summaries: dict[str, dict] = {}
    if not args.skip_marker:
        if apple_written > 0:
            marker_summaries["apple"] = finalize_marker(
                apple_path,
                record_count=len(apple_records),
                inserted=apple_written,
                errors=0,
                writer="ingest_brand_direct_sg.py:BUY-32061",
                require_r2=not args.lenient_marker,
            )
        if samsung_written > 0:
            marker_summaries["samsung"] = finalize_marker(
                samsung_path,
                record_count=len(samsung_records),
                inserted=samsung_written,
                errors=0,
                writer="ingest_brand_direct_sg.py:BUY-32061",
                require_r2=not args.lenient_marker,
            )

    if marker_summaries:
        print("\nIngest markers:")
        print(json.dumps(marker_summaries, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
