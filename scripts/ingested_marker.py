#!/usr/bin/env python3
"""Per-file ingestion completion marker helper — BUY-33089.

After an ingester has loaded a scrape artifact into the canonical catalog AND
uploaded the raw output to Cloudflare R2, it writes a small JSON marker next to
the source file:

    <file>.ingested.json

with this payload:

    {
      "sha256":      "<hex>",        # sha256 of the source file content
      "recordCount": <int>,          # records parsed from the file
      "inserted":    <int>,          # rows actually upserted
      "errors":      <int>,          # per-row error count
      "r2Uploaded":  <bool>,         # raw file successfully uploaded to R2
      "r2Key":       "<key>",        # the R2 object key (when uploaded)
      "ingestedAt":  "<iso8601>"     # UTC timestamp
    }

The marker is the durable "Gate B" signal that the safe-data-cleanup.sh routine
consumes. The cleanup script looks for ``<file>.ingested.json`` next to a
candidate file and treats presence as full ingest confirmation, skipping the
slow 100-URL catalog sample (Gate B3).

Strict invariant from the parent directive (BUY-32826 follow-up comment):
the marker is written ONLY after BOTH the catalog upsert returned
successfully (inserted > 0) AND the R2 upload returned 2xx. If either side
fails, no marker is written and the file remains unconfirmed so the cleanup
protocol will fall back to the slower gates.

R2 credentials are read from the same env vars as
``scripts/export_catalog_to_r2.py``:
    CLOUDFLARE_R2_BUCKET (or CLOUDFLARE_BUCKET, default "buywhere-data")
    CLOUDFLARE_R2_ACCOUNT_ID (or CLOUDFLARE_ACCOUNT_ID, required)
    CLOUDFLARE_R2_ACCESS_KEY_ID (or CLOUDFLARE_R2_ACCESS_KEY, required)
    CLOUDFLARE_R2_SECRET_ACCESS_KEY (or CLOUDFLARE_SECRET_ACCESS_KEY, required)

If R2 env is not configured, ``upload_to_r2`` returns ``(False, "", reason)``
and the caller is expected to NOT write a marker (the strict invariant is
"both must succeed"). This keeps the marker contract honest: a missing
marker is always a "not yet proven" signal.
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


SCHEMA_VERSION = 1


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
        # Cross-script interop: the 3ec8f6dd cleanup script and r2_head.py
        # look for a top-level "key" field. Emit it as an alias of r2Key so
        # both Gate B0 (this script) and Gate D (that script) recognise the
        # same marker. r2Key remains the canonical name per the issue
        # schema in BUY-33089.
        if out.get("r2Key") and "key" not in out:
            out["key"] = out["r2Key"]
        return out


def read_marker(file_path: Path) -> dict[str, Any] | None:
    """Read and return the marker for ``file_path`` if it exists."""
    mp = marker_path_for(file_path)
    if not mp.is_file():
        return None
    try:
        return json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


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


def finalize_marker(
    file_path: Path,
    *,
    record_count: int,
    inserted: int,
    errors: int,
    writer: str,
    require_r2: bool = True,
) -> dict[str, Any]:
    """End-to-end finalize helper: compute SHA, upload to R2, write marker.

    Returns a summary dict suitable for logging or for the ingester's
    stdout payload. The strict invariant is enforced here: marker is
    written ONLY if BOTH the catalog caller (signalled by ``inserted > 0``)
    AND the R2 upload returned 2xx (or R2 is intentionally skipped via
    ``require_r2=False`` for legacy files that pre-date the R2 migration).

    A marker is NEVER written for ``inserted == 0`` — that means the
    catalog upsert did not actually persist anything, so the file is not
    proven ingested.
    """
    summary: dict[str, Any] = {
        "file": str(file_path),
        "marker": str(marker_path_for(file_path)),
        "markerWritten": False,
    }
    if not file_path.is_file():
        summary["error"] = "source file not found"
        return summary
    if inserted <= 0:
        summary["error"] = "catalog upsert returned 0 rows; marker suppressed"
        return summary
    sha_hex = compute_sha256(file_path)
    summary["sha256"] = sha_hex
    summary["recordCount"] = record_count
    summary["inserted"] = inserted
    summary["errors"] = errors
    r2_uploaded = False
    r2_key = ""
    r2_error: str | None = None
    if r2_configured() or require_r2:
        r2_uploaded, r2_key, r2_error = upload_to_r2(file_path)
    else:
        r2_error = "R2 not configured; require_r2=False (legacy path)"
    summary["r2Uploaded"] = r2_uploaded
    summary["r2Key"] = r2_key
    summary["r2Error"] = r2_error
    if require_r2 and not r2_uploaded:
        summary["error"] = "R2 upload failed; marker suppressed"
        return summary
    mp = write_marker(
        file_path,
        sha256_hex=sha_hex,
        record_count=record_count,
        inserted=inserted,
        errors=errors,
        r2_uploaded=r2_uploaded,
        r2_key=r2_key,
        r2_error=r2_error,
        writer=writer,
    )
    summary["markerWritten"] = True
    summary["marker"] = str(mp)
    return summary


if __name__ == "__main__":  # pragma: no cover - manual debug helper
    if len(sys.argv) < 2:
        print("usage: ingested_marker.py <file> [<inserted>]", file=sys.stderr)
        sys.exit(2)
    target = Path(sys.argv[1])
    inserted = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    record_count = sum(1 for _ in target.open()) if target.is_file() else 0
    print(json.dumps(finalize_marker(target, record_count=record_count, inserted=inserted, errors=0, writer="cli"), indent=2))
