# BUY-29201 Canonical Writer Repoint

Date: 2026-06-02 UTC

## Summary

This checkout now has one repo-local canonical catalog writer path instead of
split per-script behavior:

- added [src/catalog_ingest.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/src/catalog_ingest.py)
  as the shared upsert path for `public.products`
- refactored
  [scripts/emergency_catalog_ingest.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/emergency_catalog_ingest.py)
  onto that shared writer
- changed
  [src/scrapers/ikea_sg.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/src/scrapers/ikea_sg.py)
  so ingest mode now defaults to the guarded canonical DB pin rather than API
  posting

## What Changed

The shared writer:

- resolves the target DB via `scripts.ingestion_guard.database_url()`
- therefore prefers `data/.catalog_db_url` over harness `DATABASE_URL`
- refuses writes when the target fingerprints as the Paperclip control-plane DB
- upserts on `(sku, source)` into `public.products`

The IKEA scraper now has three explicit modes:

- default ingest mode: canonical DB via `data/.catalog_db_url`
- `--ingest-via-api`: legacy API posting fallback
- `--scrape-only`: JSONL artifact output only

This removes the silent default where a repo-local ingestion run could still
avoid the canonical pin and rely on whichever runtime/API deployment it hit.

## Verification

Ran:

```bash
python3 -m py_compile src/catalog_ingest.py scripts/emergency_catalog_ingest.py src/scrapers/ikea_sg.py
python3 scripts/emergency_catalog_ingest.py paper_source merchants/paper_source_2026-05-29.ndjson --dry-run
python3 src/scrapers/ikea_sg.py --help
```

Observed:

- compilation succeeded for all changed Python files
- emergency dry-run passed the ingestion guard and resolved
  `data/.catalog_db_url` to the pinned maglev URL
- IKEA CLI now documents `--ingest-via-api`, making API mode an explicit
  override rather than the default writer path

## Scope Boundary

Within this checkout, the verified durable writers are now pinned to the
canonical catalog path. If other production runtimes outside this repo still
write through `roundhouse` or another non-canonical path, that remaining work
belongs to the runtime/infra owners of those external deployments.
