#!/usr/bin/env python3
"""Filter the Samsung SG full-drain NDJSON to rows that pass the strict
brand-direct schema (name + required fields) and rewrite the artifact plus
its sidecar so that every record on disk satisfies the acceptance criteria.

The 309 rows that fall back to modelCode-only (no JSON-LD name) are already
captured in the existing sidecar's `invalid_schema` array; this script moves
them out of the primary NDJSON but leaves the sidecar intact as the per-URL
error ledger.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APPLE_NDJSON = REPO_ROOT / "merchants" / "apple_sg_buy_xml_full_2026-06-06.ndjson"
SAMSUNG_NDJSON = REPO_ROOT / "merchants" / "samsung_sg_sitemap_full_2026-06-06.ndjson"
APPLE_SIDECAR = REPO_ROOT / "data" / "brand_direct" / "apple_sg_buy_xml_full_2026-06-06_failures.json"
SAMSUNG_SIDECAR = REPO_ROOT / "data" / "brand_direct" / "samsung_sg_sitemap_full_2026-06-06_failures.json"
SUMMARY_PATH = REPO_ROOT / "data" / "brand_direct" / "brand_direct_sg_full_drain_2026-06-06.json"


REQUIRED = ("sku", "name", "url", "source", "region", "platform")


def validate(record: dict, source: str) -> str | None:
    for field in REQUIRED:
        if not record.get(field):
            return f"missing {field}"
    if record.get("source") != source:
        return f"wrong source={record.get('source')}"
    if record.get("region") != "SG":
        return f"wrong region={record.get('region')}"
    if record.get("platform") != "direct_http":
        return f"wrong platform={record.get('platform')}"
    if record.get("currency") != "SGD":
        return f"wrong currency={record.get('currency')}"
    return None


def clean(ndjson_path: Path, sidecar_path: Path, source: str) -> tuple[int, int, int]:
    raw = []
    with ndjson_path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                raw.append(json.loads(line))

    keep: list[dict] = []
    drop_invalid: list[dict] = []
    for record in raw:
        err = validate(record, source=source)
        if err is None:
            keep.append(record)
        else:
            drop_invalid.append({"url": record.get("url", ""), "error": err})

    # Dedupe by (sku, source) — keep the first occurrence so DB upserts don't
    # collide on the (sku, source) ON CONFLICT key.
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    drop_dupe: list[dict] = []
    for record in keep:
        key = (record.get("sku"), record.get("source"))
        if key in seen:
            drop_dupe.append({"url": record.get("url", ""), "error": "duplicate (sku, source)"})
            continue
        seen.add(key)
        deduped.append(record)

    with ndjson_path.open("w", encoding="utf-8") as fh:
        for record in deduped:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    sidecar = json.loads(sidecar_path.read_text()) if sidecar_path.exists() else {}
    sidecar["record_count"] = len(deduped)
    sidecar["unique_records"] = len(deduped)
    sidecar["invalid_count"] = len(drop_invalid) + len(drop_dupe)
    sidecar["invalid_schema"] = drop_invalid + drop_dupe
    sidecar["generated_at"] = datetime.now(timezone.utc).isoformat()
    sidecar_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    return len(deduped), len(drop_invalid), len(drop_dupe)


def main() -> int:
    apple_kept, apple_invalid, apple_dupe = clean(APPLE_NDJSON, APPLE_SIDECAR, "apple_sg_buy_xml")
    samsung_kept, samsung_invalid, samsung_dupe = clean(SAMSUNG_NDJSON, SAMSUNG_SIDECAR, "samsung_sg_sitemap")

    summary = json.loads(SUMMARY_PATH.read_text()) if SUMMARY_PATH.exists() else {}
    summary["apple"] = {
        "source": "apple_sg_buy_xml",
        "ndjson_path": str(APPLE_NDJSON.relative_to(REPO_ROOT)),
        "failures_path": str(APPLE_SIDECAR.relative_to(REPO_ROOT)),
        "record_count": apple_kept,
        "unique_records": apple_kept,
        "invalid_count": apple_invalid + apple_dupe,
        "dropped_invalid_schema": apple_invalid,
        "dropped_duplicate_sku_source": apple_dupe,
    }
    summary["samsung"] = {
        "source": "samsung_sg_sitemap",
        "ndjson_path": str(SAMSUNG_NDJSON.relative_to(REPO_ROOT)),
        "failures_path": str(SAMSUNG_SIDECAR.relative_to(REPO_ROOT)),
        "record_count": samsung_kept,
        "unique_records": samsung_kept,
        "invalid_count": samsung_invalid + samsung_dupe,
        "dropped_invalid_schema": samsung_invalid,
        "dropped_duplicate_sku_source": samsung_dupe,
    }
    summary["combined_record_count"] = apple_kept + samsung_kept
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Apple: kept={apple_kept} dropped_invalid={apple_invalid} dropped_dupe={apple_dupe}")
    print(f"Samsung: kept={samsung_kept} dropped_invalid={samsung_invalid} dropped_dupe={samsung_dupe}")
    print(f"Combined: {apple_kept + samsung_kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
