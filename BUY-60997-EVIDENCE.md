# BUY-60997 — Tranco list discovery fetching a dead 404 URL (~16K failures/7d)

**Agent:** Hunt (`f6a39f3c-210b-479b-a8e7-c78491c120e9`)
**Heartbeat:** 2026-07-08T16:45Z
**Repo:** `BuyWhere/buywhere-ingest` (worker; not in `buywhere-api`)
**Files changed:** `src/trancoDiscovery.js`, `tests/trancoDiscovery.test.js`

## Root cause

The `tranco_*_discover` ingestion jobs (~16K failures/7d) are produced by the
**buywhere-ingest worker**, not the `buywhere-api` repo. The worker's
`src/trancoDiscovery.js` → `fetchTrancoList()` resolves the Tranco list in two
steps, and the Tranco project reorganized both endpoints:

1. **Metadata lookup** — `GET https://tranco-list.eu/api/lists/latest`
   now returns **HTTP 404**. The deployed version had either no fallback
   (older revision) or only a single yesterday-fallback that was insufficient.

2. **CSV download** — the legacy `https://tranco-list.eu/lists/<id>/full`
   path is dead (**HTTP 404**). The canonical path is now
   `https://tranco-list.eu/download/<id>/<prefix>`.

Either failure surfaces in `ingestion_runs` as:
`Tranco list csv fetch failed: 404 404: Not Found`

## Live endpoint verification (2026-07-08)

| URL | Status |
| --- | --- |
| `https://tranco-list.eu/api/lists/latest` | **404** (dead) |
| `https://tranco-list.eu/api/lists/date/2026-07-07` | **200** → `{list_id:"JZK4Y", download:".../download/JZK4Y/1000000"}` |
| `https://tranco-list.eu/download/JZK4Y/1000000` | **200** (valid CSV) |
| `https://tranco-list.eu/lists/JZK4Y/full` | **404** (dead legacy path) |

## Fix

`fetchTrancoList()` now:

- Tries metadata endpoints in order: `/api/lists/latest` →
  `/api/lists/date/<today>` → `<yesterday>` → `<2-days-ago>`, stopping at the
  first 200. Non-404 client errors short-circuit immediately.
- Reads the API-provided `download` URL from the metadata response and prefers it.
- Falls back through CSV candidates: `opts.downloadUrl` → `meta.download` →
  `/download/<id>/<limit>` → `/download/<id>/full`.
- Enriches the csv-fetch error with the attempted URL for faster triage.

## Verification

### Unit tests
```
node --test tests/trancoDiscovery.test.js
# tests 27  pass 27  fail 0
```
Two new regression tests cover (a) the `/api/lists/latest` → date fallback and
(b) canonical `/download/<id>/<limit>` resolution when the metadata omits
`download`. All four other test suites in the repo also pass (78 tests total).

### Live integration
```
node --input-type=module -e 'import { fetchTrancoList } from "./src/trancoDiscovery.js";
  const t = await fetchTrancoList({ limit: 10 }); console.log(t.listId, t.availableDate, t.rows.length);'
→ OK listId=JZK4Y availableDate=2026-07-07T22:00:02.509152 rows=10
  first 3: [{"rank":1,"domain":"google.com"},{"rank":2,...}]
```

## Deploy note

This change is committed to `main` of `BuyWhere/buywhere-ingest`. The Railway
`buywhere-ingest-worker-production` service must be redeployed (or auto-deploys
from `main`) for the fix to take effect. Once deployed, the four
`tranco_*_discover` sources should return to >0% success and the
`ingestion_pipeline_healthcheck.py` exclusion workaround (BUY-60464) can be
retired once 7-day failures clear.
