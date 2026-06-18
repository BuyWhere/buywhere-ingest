#!/usr/bin/env python3
"""Smoke test for scripts.ingested_marker BUY-33127 behavior.

Verifies the four contracts:

  1. When a lane teardown marker already exists (the BUY-33090 nested
     shape with r2.* + local.* + uploadedAt + uploader + ticket), the
     ingester OVERWRITES the marker so it ALSO contains
     ``ingest.{records, inserted, errors, at}`` while preserving the
     r2.* + local.* + uploadedAt blocks (so Gate D cleanup still works).

  2. The Gate D1 grep for ``"key":"..."`` still matches the new nested
     marker, so the cleanup script does not need to be touched.

  3. On partial failure (inserted < records or errors > 0), the marker
     is written with ``ingest.partial = true`` so Gate B consumers
     retain the file for re-drive.

  4. When the existing marker is the legacy v1 flat shape (written by
     older finalize_marker calls), the OVERWRITE migrates it into the
     v2 nested form with the ingest block on top.

Run:
  PYTHONPATH=. python3 scripts/_test_ingested_marker_buy33127.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ingested_marker import (  # noqa: E402
    SCHEMA_VERSION,
    compute_sha256,
    marker_path_for,
    read_marker,
    write_marker_v2,
)


def _write_ndjson(path: Path, lines: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for i in range(lines):
            fh.write(
                json.dumps(
                    {
                        "sku": f"SKU-{i:04d}",
                        "title": f"Test Product {i}",
                        "price": "9.99",
                        "url": f"https://example.test/p/{i}",
                    }
                )
                + "\n"
            )


def _write_lane_teardown_marker(file_path: Path, *, key_suffix: str) -> Path:
    """Simulate the marker written by scripts/lib/lane_r2_teardown.mjs."""
    sha = compute_sha256(file_path)
    size = file_path.stat().st_size
    marker = {
        "r2": {
            "bucket": "buywhere-data",
            "key": f"scrape/3ec8f6dd/crate/{key_suffix}-{file_path.name}",
            "authMode": "s3_sigv4",
            "bytes": size,
            "contentLength": size,
            "etag": "d41d8cd98f00b204e9800998ecf8427e",
            "lastModified": "2026-06-06T20:00:00.000Z",
        },
        "local": {
            "path": str(file_path),
            "size": size,
            "sha256": sha,
        },
        "uploadedAt": "2026-06-06T20:00:00.000Z",
        "uploader": "lane_r2_teardown.mjs",
        "ticket": "BUY-33090",
    }
    mp = marker_path_for(file_path)
    mp.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return mp


def _write_legacy_v1_marker(file_path: Path) -> Path:
    sha = compute_sha256(file_path)
    mp = marker_path_for(file_path)
    legacy = {
        "schemaVersion": 1,
        "sha256": sha,
        "recordCount": 0,
        "inserted": 0,
        "errors": 0,
        "r2Uploaded": True,
        "r2Key": f"scrape-artifacts/2026-06-06/{file_path.name}",
        "ingestedAt": "2026-06-06T20:00:00.000Z",
        "writer": "ingested_marker:legacy",
        "sourcePath": str(file_path),
        "key": f"scrape-artifacts/2026-06-06/{file_path.name}",
    }
    mp.write_text(json.dumps(legacy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return mp


def _read_marker(file_path: Path) -> dict:
    return json.loads(marker_path_for(file_path).read_text(encoding="utf-8"))


def test_lane_teardown_marker_preserved_and_ingest_added() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "data" / "crate"
        ndjson = work / "cycle-1.ndjson"
        _write_ndjson(ndjson, 10)
        _write_lane_teardown_marker(ndjson, key_suffix="cycle-1")

        before = _read_marker(ndjson)
        assert "r2" in before and before["r2"].get("key"), "precondition: lane teardown marker present"
        assert "ingest" not in before, "precondition: no ingest block yet"

        mp, marker, partial = write_marker_v2(
            ndjson,
            existing_marker=before,
            records=10,
            inserted=10,
            errors=0,
            writer="scripts/emergency_catalog_ingest.py:BUY-29199",
        )

        assert partial is False, "10/10 with 0 errors must not be partial"
        assert marker["schemaVersion"] == SCHEMA_VERSION == 2
        assert marker["r2"] == before["r2"], "r2 block must be preserved verbatim"
        assert marker["local"] == before["local"], "local block must be preserved verbatim"
        assert marker["uploadedAt"] == before["uploadedAt"], "uploadedAt must be preserved"
        assert marker["uploader"] == before["uploader"], "uploader must be preserved"
        assert marker["ticket"] == before["ticket"], "ticket must be preserved"
        assert marker["ingest"] == {
            "records": 10,
            "inserted": 10,
            "errors": 0,
            "at": marker["ingest"]["at"],
            "partial": False,
        }
        assert marker["ingestedBy"] == "scripts/emergency_catalog_ingest.py:BUY-29199"

        # Gate D grep contract: safe-data-cleanup.sh looks for `"key":"..."`
        raw = mp.read_text(encoding="utf-8")
        assert '"key"' in raw, "nested r2.key must be present for Gate D1 grep"
        # Specifically, the Gate D1 grep pattern
        import re
        match = re.search(r'"key"\s*:\s*"[^"]+"', raw)
        assert match is not None, "Gate D1 grep pattern must match the nested marker"
        assert match.group(0).startswith('"key"'), f"matched: {match.group(0)!r}"

    print("OK: lane teardown marker preserved, ingest block added, Gate D grep still matches")


def test_partial_ingest_sets_partial_true() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "data" / "crate"
        ndjson = work / "cycle-2.ndjson"
        _write_ndjson(ndjson, 10)
        _write_lane_teardown_marker(ndjson, key_suffix="cycle-2")

        before = _read_marker(ndjson)
        _, marker, partial = write_marker_v2(
            ndjson,
            existing_marker=before,
            records=10,
            inserted=7,
            errors=3,
            writer="scripts/emergency_catalog_ingest.py:BUY-29199",
        )

        assert partial is True, "inserted=7/10 with errors=3 must be partial"
        assert marker["ingest"]["partial"] is True
        assert marker["ingest"]["records"] == 10
        assert marker["ingest"]["inserted"] == 7
        assert marker["ingest"]["errors"] == 3
        assert marker["r2"] == before["r2"], "r2 still preserved on partial"

    print("OK: partial ingest sets ingest.partial=true and preserves r2.*")


def test_errors_only_partial() -> None:
    """inserted == records but errors > 0 must still be partial."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "data" / "crate"
        ndjson = work / "cycle-3.ndjson"
        _write_ndjson(ndjson, 5)
        before = _read_marker(ndjson) if marker_path_for(ndjson).is_file() else None
        _, marker, partial = write_marker_v2(
            ndjson,
            existing_marker=before,
            records=5,
            inserted=5,
            errors=2,
            writer="scripts/ingest_brand_direct_sg.py:BUY-32061",
        )
        assert partial is True
        assert marker["ingest"]["partial"] is True
        assert marker["ingest"]["errors"] == 2

    print("OK: errors > 0 alone triggers ingest.partial=true")


def test_legacy_v1_marker_is_migrated_to_v2() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "data" / "legacy"
        ndjson = work / "cycle-old.ndjson"
        _write_ndjson(ndjson, 4)
        _write_legacy_v1_marker(ndjson)

        before = _read_marker(ndjson)
        assert before.get("schemaVersion") == 1
        assert "r2Key" in before, "precondition: legacy v1 has flat r2Key"

        _, marker, partial = write_marker_v2(
            ndjson,
            existing_marker=before,
            records=4,
            inserted=4,
            errors=0,
            writer="scripts/emergency_catalog_ingest.py:BUY-29199",
        )

        assert marker["schemaVersion"] == 2
        assert "r2" in marker and marker["r2"].get("key"), "legacy r2Key must migrate into nested r2.key"
        assert marker["r2"]["key"] == before["r2Key"]
        assert "local" in marker and marker["local"].get("sha256") == before["sha256"]
        assert partial is False
        assert marker["ingest"]["records"] == 4
        assert marker["ingest"]["inserted"] == 4

    print("OK: legacy v1 flat marker migrates to v2 nested shape with ingest block")


def test_no_existing_marker_still_writes_ingest_block() -> None:
    """Cold path: the ingester is the first writer (no lane teardown marker).
    The marker must still contain ingest.* (the Gate D fallback is via r2.*)."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "data" / "cold"
        ndjson = work / "cycle-cold.ndjson"
        _write_ndjson(ndjson, 3)
        assert not marker_path_for(ndjson).is_file(), "precondition: no existing marker"

        _, marker, partial = write_marker_v2(
            ndjson,
            existing_marker=None,
            records=3,
            inserted=3,
            errors=0,
            writer="scripts/emergency_catalog_ingest.py:BUY-29199",
            extra_r2={"key": "scrape-artifacts/2026-06-06/cycle-cold.ndjson", "bucket": "buywhere-data"},
        )

        assert marker["schemaVersion"] == 2
        assert marker["r2"]["key"] == "scrape-artifacts/2026-06-06/cycle-cold.ndjson"
        assert marker["local"]["sha256"]  # computed
        assert marker["ingest"]["records"] == 3
        assert partial is False

    print("OK: cold path (no existing marker) still writes r2.* + ingest.* + local.*")


def main() -> int:
    tests = [
        test_lane_teardown_marker_preserved_and_ingest_added,
        test_partial_ingest_sets_partial_true,
        test_errors_only_partial,
        test_legacy_v1_marker_is_migrated_to_v2,
        test_no_existing_marker_still_writes_ingest_block,
    ]
    failed: list[str] = []
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failed.append(f"FAIL {t.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed.append(f"ERROR {t.__name__}: {exc!r}")
    if failed:
        print("\n".join(failed), file=sys.stderr)
        return 1
    print(f"\nAll {len(tests)} tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
