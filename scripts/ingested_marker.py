#!/usr/bin/env python3
"""Per-file ingestion completion marker helper — BUY-33089 / BUY-33127.

After a scrape lane has uploaded the raw artifact to Cloudflare R2, the lane
teardown (``scripts/lib/lane_r2_teardown.mjs``) writes a small JSON marker
next to the source file:

    <file>.ingested.json

with this payload:

    {
      "r2":   {"bucket", "key", "authMode", "bytes", "contentLength",
               "etag", "lastModified"},
      "local": {"path", "size", "sha256"},
      "uploadedAt": "<iso8601>",
      "uploader":   "lane_r2_teardown.mjs",
      "ticket":     "<PAPERCLIP_TASK_ID or null>"
    }

The marker is the durable "Gate D" signal that the safe-data-cleanup.sh
routine consumes (it greps ``"key":"..."`` out of the file). That covers
R2 presence but does NOT cover ingest confirmation.

After the ingester loads a file into ``public.products`` it must
**OVERWRITE** this marker with one that *also* carries the ingest evidence
per BUY-33127 / the DATA_CLEANUP_PROTOCOL.md pipeline. The ingester-side
marker shape is:

    {
      "schemaVersion": 2,
      "r2":   { ... preserved from lane teardown ... },
      "local": { ... preserved from lane teardown ... },
      "uploadedAt": "...",
      "uploader":   "...",
      "ticket":     "...",
      "ingest": {
        "records":  <int>,    # records parsed from the file
        "inserted": <int>,    # rows actually upserted
        "errors":   <int>,    # per-row error count
        "at":       "<iso>",  # UTC timestamp
        "partial":  <bool>    # True iff inserted < records OR errors > 0
      }
    }

The Gate D grep for ``"key":"..."`` still matches inside the nested ``r2``
block, so the cleanup script continues to work without changes. The
``ingest.partial = true`` flag is the explicit signal to Gate B-style
follow-ups that this file was NOT fully ingested and should be retained
for re-drives (cf. DATA_CLEANUP_PROTOCOL.md §Gate B / BUY-33127 partial
behavior).

R2 credentials are read from the same env vars as
``scripts/export_catalog_to_r2.py``:
    CLOUDFLARE_R2_BUCKET (or CLOUDFLARE_BUCKET, default "buywhere-data")
    CLOUDFLARE_R2_ACCOUNT_ID (or CLOUDFLARE_ACCOUNT_ID, required)
    CLOUDFLARE_R2_ACCESS_KEY_ID (or CLOUDFLARE_R2_ACCESS_KEY, required)
    CLOUDFLARE_R2_SECRET_ACCESS_KEY (or CLOUDFLARE_SECRET_ACCESS_KEY, required)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
PARTIAL_FLAG_THRESHOLD = 0  # errors strictly > 0 OR inserted < records => partial


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compute_sha256(path: Path, *, chunk_bytes: int = 1 << 20) -> str:
    """Return the hex sha256 of the file at ``path``."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_bytes), b""):
            h.update(chunk)
    return h.hexdigest()


def marker_path_for(file_path: Path) -> Path:
    """Return the marker path associated with a given source file.

    Example: ``data/foo.ndjson`` -> ``data/foo.ndjson.ingested.json``.
    The trailing ``.ingested.json`` suffix keeps the marker as a separate
    file from the artifact itself, and the safe-data-cleanup.sh glob picks
    it up via a targeted ``-name '*.ingested.json'`` test rather than
    matching the artifact glob patterns.
    """
    return file_path.with_name(file_path.name + ".ingested.json")


def read_marker(file_path: Path) -> dict[str, Any] | None:
    """Read and return the marker for ``file_path`` if it exists.

    Returns None if the marker does not exist or is unreadable JSON.
    The caller decides how to interpret the shape (lane teardown vs.
    ingester). The ``schemaVersion`` field distinguishes v1 (flat,
    ingester-only) from v2 (nested, lane teardown + ingester).
    """
    mp = marker_path_for(file_path)
    if not mp.is_file():
        return None
    try:
        return json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _coerce_preserved_block(existing: dict[str, Any]) -> dict[str, Any]:
    """Return the r2/local/uploadedAt/uploader/ticket blocks from an
    existing marker, normalising legacy v1 flat shape into the v2
    nested form so the OVERWRITE produces a uniform marker.

    Legacy v1 markers look like::

        {"schemaVersion": 1, "sha256": "...", "r2Key": "...",
         "r2Uploaded": true, "ingestedAt": "..."}

    Lane teardown v2 markers look like::

        {"r2": {"bucket": ..., "key": ...}, "local": {...},
         "uploadedAt": "...", "uploader": "...", "ticket": ...}

    We want the OVERWRITE marker to be readable by both Gate D (cleanup
    script grep for ``"key":"..."``) and by future Gate B consumers that
    will look for ``"ingest":"..."``.
    """
    if not existing:
        return {}
    r2 = existing.get("r2")
    local = existing.get("local")
    if r2 is None and existing.get("r2Key"):
        r2 = {
            "bucket": existing.get("r2Bucket"),
            "key": existing.get("r2Key"),
            "authMode": existing.get("r2AuthMode"),
            "bytes": existing.get("r2Bytes") or existing.get("bytes"),
            "contentLength": existing.get("r2ContentLength"),
            "etag": existing.get("r2Etag") or existing.get("etag"),
            "lastModified": existing.get("r2LastModified") or existing.get("lastModified"),
        }
    if local is None and existing.get("sha256"):
        local = {
            "path": existing.get("sourcePath") or existing.get("localPath"),
            "size": existing.get("localSize"),
            "sha256": existing.get("sha256"),
        }
    preserved: dict[str, Any] = {}
    if isinstance(r2, dict) and r2:
        preserved["r2"] = {k: v for k, v in r2.items() if v is not None}
    if isinstance(local, dict) and local:
        preserved["local"] = {k: v for k, v in local.items() if v is not None}
    for k in ("uploadedAt", "uploader", "ticket"):
        v = existing.get(k)
        if v is not None:
            preserved[k] = v
    return preserved


@dataclass
class MarkerPayload:
    schemaVersion: int = SCHEMA_VERSION
    sha256: str = ""
    recordCount: int = 0
    inserted: int = 0
    errors: int = 0
    r2Uploaded: bool = False
    r2Key: str = ""
    r2Error: str | None = None
    ingestedAt: str = field(default_factory=_now_iso)
    writer: str = ""
    sourcePath: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {k: v for k, v in asdict(self).items() if v is not None}
        if out.get("r2Key") and "key" not in out:
            out["key"] = out["r2Key"]
        return out


def write_marker(
    file_path: Path,
    *,
    sha256_hex: str,
    record_count: int,
    inserted: int,
    errors: int,
    r2_uploaded: bool,
    r2_key: str = "",
    r2_error: str | None = None,
    writer: str = "",
    source_path: Path | None = None,
) -> Path:
    """Atomically write the ``.ingested.json`` marker next to ``file_path``."""
    payload = MarkerPayload(
        sha256=sha256_hex,
        recordCount=record_count,
        inserted=inserted,
        errors=errors,
        r2Uploaded=r2_uploaded,
        r2Key=r2_key,
        r2Error=r2_error,
        writer=writer,
        sourcePath=str(source_path or file_path),
    )
    mp = marker_path_for(file_path)
    mp.parent.mkdir(parents=True, exist_ok=True)
    tmp = mp.with_suffix(mp.suffix + ".tmp")
    tmp.write_text(json.dumps(payload.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, mp)
    return mp


def write_marker_v2(
    file_path: Path,
    *,
    existing_marker: dict[str, Any] | None,
    records: int,
    inserted: int,
    errors: int,
    writer: str,
    extra_r2: dict[str, Any] | None = None,
    extra_local: dict[str, Any] | None = None,
) -> tuple[Path, dict[str, Any], bool]:
    """Write a v2 ingest-evidence marker next to ``file_path``.

    Preserves the r2 / local / uploadedAt / uploader / ticket blocks from
    ``existing_marker`` (typically written by the lane teardown) and
    OVERWRITES the file with a new marker that *also* contains the
    ``ingest`` block per BUY-33127. Returns ``(marker_path, marker_dict,
    partial)`` so callers can log the result and decide downstream
    behavior (e.g. whether to flag the file for re-drive).

    The function is atomic: it writes to a sibling ``.tmp`` file and
    ``os.replace``s into place so a concurrent reader never sees a
    half-written marker.

    Partial-detection: ``inserted < records`` OR ``errors > 0`` triggers
    ``ingest.partial = true``. The cleanup script Gate B should keep
    files whose marker has ``ingest.partial = true``.
    """
    preserved = _coerce_preserved_block(existing_marker or {})
    if extra_r2:
        r2 = dict(preserved.get("r2") or {})
        r2.update({k: v for k, v in extra_r2.items() if v is not None})
        preserved["r2"] = r2
    if extra_local:
        local = dict(preserved.get("local") or {})
        local.update({k: v for k, v in extra_local.items() if v is not None})
        preserved["local"] = local
    local_block = preserved.get("local") or {}
    if not local_block.get("path"):
        local_block["path"] = str(file_path)
    try:
        local_block.setdefault("size", file_path.stat().st_size)
    except OSError:
        pass
    if not local_block.get("sha256"):
        try:
            local_block["sha256"] = compute_sha256(file_path)
        except OSError:
            pass
    preserved["local"] = {k: v for k, v in local_block.items() if v is not None}

    partial = (inserted < records) or (errors > PARTIAL_FLAG_THRESHOLD)
    ingest_block: dict[str, Any] = {
        "records": int(records),
        "inserted": int(inserted),
        "errors": int(errors),
        "at": _now_iso(),
        "partial": bool(partial),
    }

    marker: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        **preserved,
        "ingest": ingest_block,
        "ingestedBy": writer,
    }

    mp = marker_path_for(file_path)
    mp.parent.mkdir(parents=True, exist_ok=True)
    tmp = mp.with_suffix(mp.suffix + ".tmp")
    tmp.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, mp)
    return mp, marker, partial


# ---------------------------------------------------------------------------
# R2 upload
# ---------------------------------------------------------------------------


def _get_env(*names: str, default: str | None = None, required: bool = False) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    if required:
        raise KeyError(
            "Missing required environment variable. Set one of: " + ", ".join(names)
        )
    return default


def _build_s3_client():
    """Construct a boto3 S3 client for Cloudflare R2.

    Imported lazily so this module can be imported in environments without
    boto3 (e.g. linters / the safe-data-cleanup.sh subprocess) without
    failing at import time.
    """
    import boto3  # type: ignore

    account_id = _get_env(
        "CLOUDFLARE_R2_ACCOUNT_ID", "CLOUDFLARE_ACCOUNT_ID", required=True
    )
    access_key = _get_env(
        "CLOUDFLARE_R2_ACCESS_KEY_ID",
        "CLOUDFLARE_R2_ACCESS_KEY",
        required=True,
    )
    secret_key = _get_env(
        "CLOUDFLARE_R2_SECRET_ACCESS_KEY",
        "CLOUDFLARE_SECRET_ACCESS_KEY",
        required=True,
    )
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        region_name="auto",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def _r2_bucket() -> str:
    return (
        _get_env("CLOUDFLARE_R2_BUCKET", "CLOUDFLARE_BUCKET", default="buywhere-data")
        or "buywhere-data"
    ).lower()


def r2_configured() -> bool:
    """Return True iff the R2 credentials look usable in this environment."""
    try:
        _get_env("CLOUDFLARE_R2_ACCOUNT_ID", "CLOUDFLARE_ACCOUNT_ID", required=True)
        _get_env(
            "CLOUDFLARE_R2_ACCESS_KEY_ID",
            "CLOUDFLARE_R2_ACCESS_KEY",
            required=True,
        )
        _get_env(
            "CLOUDFLARE_R2_SECRET_ACCESS_KEY",
            "CLOUDFLARE_SECRET_ACCESS_KEY",
            required=True,
        )
    except KeyError:
        return False
    return True


def r2_key_for(file_path: Path, *, prefix: str = "scrape-artifacts") -> str:
    """Compute a deterministic R2 key for a local file.

    Layout: ``<prefix>/<date>/<basename>`` with the date captured at write
    time. The basename is kept as-is so a re-run uploads to the same key,
    which is what we want (idempotent re-ingest of the same artifact).
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{prefix}/{today}/{file_path.name}"


def upload_to_r2(
    file_path: Path,
    *,
    key: str | None = None,
    bucket: str | None = None,
    extra_metadata: dict[str, str] | None = None,
) -> tuple[bool, str, str | None]:
    """Upload ``file_path`` to R2. Returns ``(success, key, error)``.

    On success: ``(True, key, None)`` where ``key`` is the object key.
    On failure: ``(False, key, error_message)`` — never raises. Callers
    decide whether to write the marker based on the success bool.
    """
    object_key = key or r2_key_for(file_path)
    if not r2_configured():
        return False, object_key, "R2 credentials not configured in environment"
    try:
        client = _build_s3_client()
    except Exception as exc:  # noqa: BLE001
        return False, object_key, f"failed to build s3 client: {exc}"
    bucket_name = (bucket or _r2_bucket()).lower()
    sha_hex = compute_sha256(file_path)
    metadata = {"sha256": sha_hex}
    if extra_metadata:
        for k, v in extra_metadata.items():
            metadata[k] = str(v)[:512]
    try:
        with file_path.open("rb") as body:
            client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=body,
                ContentType="application/x-ndjson",
                Metadata=metadata,
            )
    except Exception as exc:  # noqa: BLE001
        return False, object_key, f"put_object failed: {exc}"
    return True, object_key, None


def _extract_r2_from_existing(marker: dict[str, Any] | None) -> dict[str, Any]:
    """Pull r2.* fields out of an existing marker in a shape suitable for
    the R2 upload helper's ``extra_metadata``/key handling. Used so the
    ingester can SKIP re-upload when the lane teardown already wrote
    ``r2.key`` and ``r2.uploadedAt``."""
    if not marker:
        return {}
    r2 = marker.get("r2") or {}
    if not r2 and marker.get("r2Key"):
        r2 = {
            "bucket": marker.get("r2Bucket"),
            "key": marker.get("r2Key"),
            "authMode": marker.get("r2AuthMode"),
            "bytes": marker.get("r2Bytes") or marker.get("bytes"),
        }
    out: dict[str, Any] = {}
    if r2.get("key"):
        out["key"] = r2["key"]
    if r2.get("bucket"):
        out["bucket"] = r2["bucket"]
    return out


def finalize_marker(
    file_path: Path,
    *,
    record_count: int,
    inserted: int,
    errors: int = 0,
    writer: str,
    require_r2: bool = True,
) -> dict[str, Any]:
    """End-to-end finalize helper (BUY-33127 update).

    Computes SHA, optionally uploads to R2, then OVERWRITES the
    ``.ingested.json`` marker with a v2 marker that preserves the lane
    teardown's ``r2``/``local``/``uploadedAt``/``uploader``/``ticket``
    blocks and adds the ``ingest`` evidence block.

    The strict invariant (BUY-33089 / BUY-33127):

      * If a lane teardown marker already exists with ``r2.key``, the
        ingester treats that as R2-durable and does NOT re-upload.
      * If no marker exists, the ingester uploads to R2 (unless
        ``require_r2=False``, e.g. for legacy /ad-hoc paths).
      * The v2 marker is written ONLY if BOTH the catalog upsert
        returned ``inserted > 0`` AND the R2 evidence is present.
      * On partial ingest (``inserted < record_count`` or
        ``errors > 0``) the marker is still written but with
        ``ingest.partial = true`` so Gate B keeps the file for re-drive.

    Returns a summary dict suitable for logging or for the ingester's
    stdout payload. The strict invariant is enforced here: marker is
    written ONLY if BOTH the catalog caller (signalled by ``inserted > 0``)
    AND the R2 evidence is present (or R2 is intentionally skipped via
    ``require_r2=False`` for legacy files that pre-date the R2 migration).
    """
    summary: dict[str, Any] = {
        "file": str(file_path),
        "marker": str(marker_path_for(file_path)),
        "markerWritten": False,
        "partial": False,
        "schemaVersion": SCHEMA_VERSION,
    }
    if not file_path.is_file():
        summary["error"] = "source file not found"
        return summary
    if inserted <= 0:
        summary["error"] = "catalog upsert returned 0 rows; marker suppressed"
        return summary

    existing = read_marker(file_path)
    summary["existingMarker"] = bool(existing)
    existing_r2 = _extract_r2_from_existing(existing)
    r2_uploaded = False
    r2_key = ""
    r2_error: str | None = None
    r2_bucket: str | None = None

    if existing_r2.get("key"):
        r2_uploaded = True
        r2_key = existing_r2["key"]
        r2_bucket = existing_r2.get("bucket")
    elif r2_configured() or require_r2:
        r2_uploaded, r2_key, r2_error = upload_to_r2(file_path)
        if r2_uploaded:
            r2_bucket = _r2_bucket()
    else:
        r2_error = "R2 not configured; require_r2=False (legacy path)"

    summary["r2Uploaded"] = r2_uploaded
    summary["r2Key"] = r2_key
    summary["r2Error"] = r2_error

    if require_r2 and not r2_uploaded:
        summary["error"] = "R2 upload failed; marker suppressed"
        return summary

    extra_r2: dict[str, Any] = {}
    if r2_key:
        extra_r2["key"] = r2_key
    if r2_bucket:
        extra_r2["bucket"] = r2_bucket

    mp, marker_dict, partial = write_marker_v2(
        file_path,
        existing_marker=existing,
        records=record_count,
        inserted=inserted,
        errors=errors,
        writer=writer,
        extra_r2=extra_r2 or None,
    )
    summary["markerWritten"] = True
    summary["marker"] = str(mp)
    summary["partial"] = partial
    summary["ingest"] = marker_dict.get("ingest")
    return summary


if __name__ == "__main__":  # pragma: no cover - manual debug helper
    if len(sys.argv) < 2:
        print("usage: ingested_marker.py <file> [<inserted>]", file=sys.stderr)
        sys.exit(2)
    target = Path(sys.argv[1])
    inserted = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    record_count = sum(1 for _ in target.open()) if target.is_file() else 0
    print(json.dumps(finalize_marker(target, record_count=record_count, inserted=inserted, errors=0, writer="cli"), indent=2))
