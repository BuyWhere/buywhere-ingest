# BUY-29199 Canonical Write Recovery

Date: 2026-06-02 UTC

## Summary

The immediate freeze on canonical `public.products` writes was recovered by
writing directly to the pinned canonical catalog DB in `data/.catalog_db_url`
using a guarded emergency upsert script.

The strongest confirmed failure point from this workspace is that canonical
`maglev` writes had stalled, while this workspace also exposed a split database
configuration:

- harness `DATABASE_URL` still points at `roundhouse.proxy.rlwy.net:27479`
- canonical catalog pin `data/.catalog_db_url` points at
  `maglev.proxy.rlwy.net:31310`
- the only code in this workspace that resolves the canonical pin is
  `scripts/ingestion_guard.py`
- this workspace did not contain an existing canonical writer that consumed the
  pinned maglev URL

User clarification on the issue thread after this recovery: `maglev.proxy.rlwy.net:31310`
is the current database being used.

That means the `roundhouse` URL found in the harness environment should be
treated as stale secondary configuration from this workspace, not as proof that
the live production writer was still targeting `roundhouse`.

What this run does prove:

- canonical `maglev` writes had stalled before recovery
- this workspace did not contain an existing repo-local writer consuming the
  pinned maglev URL
- `maglev` was still writable once targeted explicitly

## Database Evidence

### Canonical maglev before recovery

- source: `data/.catalog_db_url`
- `max(created_at)`: `2026-05-29 06:26:05.894316+00`
- `max(updated_at)`: `2026-05-29 06:26:05.894316+00`
- rows created since `2026-05-30 00:00:00+00`: `0`
- rows updated since `2026-05-30 00:00:00+00`: `0`

### Harness roundhouse state

- source: harness `DATABASE_URL`
- host: `roundhouse.proxy.rlwy.net:27479`
- total products: `2,767,644`
- active products: `2,752,385`
- `max(updated_at)`: `2026-05-29 10:38:13.878247+00`

This shows the older roundhouse catalog visible from the harness environment was
also frozen, but on a different timeline and at a much smaller row count than
maglev. After the thread clarification, this is evidence of stale or secondary
environment state, not evidence that roundhouse was the current production
writer target.

## Recovery Action

Added [scripts/emergency_catalog_ingest.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/scripts/emergency_catalog_ingest.py),
which:

- uses `scripts/ingestion_guard.py`
- resolves the pinned canonical DB via `data/.catalog_db_url`
- upserts NDJSON artifacts into `public.products` on `(sku, source)`

Executed:

```bash
python3 scripts/emergency_catalog_ingest.py \
  paper_source merchants/paper_source_2026-05-29.ndjson
```

## Recovery Evidence

The emergency writer restored active cataloging on current `maglev` for three
verified merchant artifact sets:

- `paper_source`: `10` rows
- `floor_and_decor`: `3` rows
- `the_body_shop`: `5` rows

Fresh canonical evidence on maglev after the write:

- `paper_source / 0196940140866 / Pure White 4 Bar Folded Cards`
  - `created_at = updated_at = 2026-06-02 21:08:54.832313+00`
- `the_body_shop / 1026960 / Vitamin E Gentle Face Wash`
  - `created_at = updated_at = 2026-06-02 21:37:55.168409+00`
- `floor_and_decor / 101254522 / Peachtree 33 in. Painted Bright White Lift Up Wall Cabinet`
  - `created_at = updated_at = 2026-06-02 21:37:55.179077+00`
- latest verified `updated_at` across those recovered sources:
  `2026-06-02 21:37:55.179077+00`

Sample recovered canonical rows:

- `paper_source / 0196940140859 / Superfine White 4 Bar Folded Cards`
- `paper_source / 0196940140866 / Pure White 4 Bar Folded Cards`
- `the_body_shop / 1026960 / Vitamin E Gentle Face Wash`
- `floor_and_decor / 101254522 / Peachtree 33 in. Painted Bright White Lift Up Wall Cabinet`

This is sufficient to show that Oracle can actively continue cataloging into the
current canonical database from this workspace via the emergency path. It is not
yet sufficient to claim that the durable non-emergency catalog writer path has
been restored.

## Durable Capability Restoration

After child follow-up completion, Oracle directly verified the restored
non-emergency writer path from this parent issue using:

```bash
python3 scripts/catalog_target_report.py
python3 scripts/catalog_live_ingest.py paper_source --limit 3 --dry-run
python3 scripts/catalog_live_ingest.py paper_source --limit 3
```

Observed on `2026-06-02 UTC`:

- `scripts/catalog_target_report.py` resolved
  `active_database_host = maglev.proxy.rlwy.net:31310/railway`
- dry-run scraped `3` live `paper_source` products while targeting canonical
  `maglev`
- live run wrote `3` rows through the normal non-emergency path

Canonical verification after the live run:

- `paper_source / 0196940140866`
- `paper_source / 0196940140910`
- `paper_source / 0196940140927`
- all three rows had `updated_at = 2026-06-02 21:41:51.297873+00`
- all three rows had `metadata._writer = {"mode":"live_scrape","path":"scripts/catalog_live_ingest.py","issue":"BUY-29210","merchant_key":"paper_source"}`

This is the stronger end-state required by the reopened issue comment:
Oracle can now continue cataloging through a normal live scrape -> canonical DB
writer path, not only through the emergency NDJSON replay path.

## Team-Execution Catch-Up Verification

After the Oracle-team execution lanes completed, Oracle ran the expanded normal
writer path directly from the parent issue:

```bash
python3 scripts/catalog_live_ingest.py --all --limit 2 --concurrency 3 --dry-run
python3 scripts/catalog_live_ingest.py --all --limit 2 --concurrency 3
```

Observed:

- merchants targeted: `courts_sg`, `floor_and_decor`, `paper_source`,
  `the_body_shop`
- scraped counts in that run:
  - `courts_sg`: `15`
  - `floor_and_decor`: `2`
  - `paper_source`: `2`
  - `the_body_shop`: `2`
- total written in the live run: `21`

Canonical verification after the live run:

- `courts_sg / COURTS_SG_215549`
  - `updated_at = 2026-06-02 22:09:16.396113+00`
- `floor_and_decor / 100902774`
  - `updated_at = 2026-06-02 22:09:16.546927+00`
- `paper_source / 0196940140866`
  - `updated_at = 2026-06-02 22:09:16.702280+00`
- `the_body_shop / 1026960`
  - `updated_at = 2026-06-02 22:09:16.840521+00`

All sampled rows carried:

```json
{"mode":"live_scrape","path":"scripts/catalog_live_ingest.py","issue":"BUY-29216"}
```

That is the final acceptance signal for this issue: canonical writes are
restored, the durable non-emergency writer path is restored, and the expanded
team-execution lane is actively writing across four merchants through the normal
path.

## Follow-up Needed

The incident-level recovery is complete, but the permanent fix still belongs in
runtime/infra ownership:

1. keep using the repo-local canonical writer surfaces that target
   `data/.catalog_db_url`
2. treat harness `DATABASE_URL` as stale secondary context whenever the
   canonical pin is present
3. extend the restored durable writer to additional merchants as cataloging
   coverage expands
