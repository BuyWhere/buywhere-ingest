# BUY-29210 Durable Maglev Writer Restoration

Date: 2026-06-02 UTC

## Summary

Restored a repo-local non-emergency catalog writer path that scrapes live
merchant pages and upserts directly into the canonical catalog DB pinned in
`data/.catalog_db_url`.

This closes the repo-side gap left after the BUY-29199 emergency recovery:

- emergency path: `scripts/emergency_catalog_ingest.py` writes existing NDJSON
  artifacts into canonical `maglev`
- durable non-emergency path:
  `scripts/catalog_live_ingest.py` scrapes supported merchants live and writes
  the resulting products into canonical `maglev`

## What Changed

- added
  [scripts/catalog_live_ingest.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/catalog_live_ingest.py)
  as the normal scrape-to-canonical writer for:
  - `paper_source`
  - `floor_and_decor`
  - `the_body_shop`
- added
  [scripts/catalog_target_report.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/catalog_target_report.py)
  to expose the canonical pin vs harness `DATABASE_URL` split explicitly
- extended
  [scripts/ingestion_guard.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/ingestion_guard.py)
  with `configured_database_targets()` so runtime tooling can report which DB
  surface is canonical and which one is stale harness context

## Runtime Target Diagnosis

`python3 scripts/catalog_target_report.py` now reports:

- `catalog_pin_host = maglev.proxy.rlwy.net:31310/railway`
- `harness_database_host = roundhouse.proxy.rlwy.net:27479/railway`
- `active_database_host = maglev.proxy.rlwy.net:31310/railway`
- `surfaces_diverge = true`

That makes the current incident rule explicit inside the repo:
when `data/.catalog_db_url` is present, treat the harness `DATABASE_URL` as
stale secondary context for catalog writes.

## Verification

Commands run:

```bash
python3 -m py_compile \
  scripts/ingestion_guard.py \
  scripts/catalog_live_ingest.py \
  scripts/catalog_target_report.py \
  src/catalog_ingest.py \
  src/scrapers/paper_source.py \
  src/scrapers/floor_and_decor.py \
  src/scrapers/the_body_shop.py

python3 scripts/catalog_target_report.py
python3 scripts/catalog_live_ingest.py paper_source --limit 3 --dry-run
python3 scripts/catalog_live_ingest.py paper_source --limit 3
```

Observed:

- compile passed for all touched files
- dry-run scraped `3` live `paper_source` products and resolved the active
  writer target to the pinned `maglev` DB
- live run wrote `3` rows into canonical `maglev`

Canonical DB verification after the live run:

- source: `paper_source`
- SKUs:
  - `0196940140866`
  - `0196940140910`
  - `0196940140927`
- `updated_at`: `2026-06-02 21:41:51.297873+00`
- metadata `_writer`:
  - `mode = live_scrape`
  - `path = scripts/catalog_live_ingest.py`
  - `issue = BUY-29210`

## Handoff

Repo-local durable write path for the recovered merchants:

```bash
python3 scripts/catalog_live_ingest.py paper_source --limit 10
python3 scripts/catalog_live_ingest.py floor_and_decor --limit 10
python3 scripts/catalog_live_ingest.py the_body_shop --limit 10
```

This path writes directly to canonical `maglev` through the shared guarded
writer in [src/catalog_ingest.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/src/catalog_ingest.py),
without depending on the emergency NDJSON replay script.
