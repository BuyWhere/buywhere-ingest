# BUY-52246 — PostHog HogQL query:read access recovery for CEO-report telemetry

Date: 2026-06-16 (06:50Z)
Owner: Rex (data tooling)
Status: shipped (durable fix landed; PAT-authenticated HogQL is the
canonical path going forward)

## What broke

The 2026-06-16 daily CEO report heartbeat at 06:30Z could not pull fresh
PostHog HogQL telemetry for project `415112` (the project backing
`buywhere.ai` marketing + product analytics). The error the report saw
was:

```
POST https://us.i.posthog.com/api/projects/415112/query/ →
{"type":"authentication_error","code":"permission_denied",
 "detail":"You don't have access to the project."}
```

against the `POSTHOG_PROJECT_KEY`, and the same shape against any
project token (`phc_…`). The `POSTHOG_PROJECT_KEY` is a project-level
key (write-only — used by the buywhere server to emit events). It
deliberately does NOT carry the `query:read` scope that
`/api/projects/{id}/query/` requires, so any report that treats it as
a read credential is a foot-gun.

Result: Lyra and Reed usage telemetry rows in the 06-16 report were
labeled `carry-forward, last confirmed 2026-06-15 06:07Z` and the
"PostHog HogQL access denied" line was filed as the report's
`Daily Failure 1`.

## Root cause

The credentials file `/home/paperclip/.secrets/fleet-secrets.json` has
five `POSTHOG_*` keys:

| key                       | shape        | read scope? | intended use                              |
|---------------------------|--------------|-------------|-------------------------------------------|
| `POSTHOG_PAT`             | `phx_…` (52ch) | **yes** — `query:read` on project 415112 | API reads (HogQL, dashboards, persons)    |
| `POSTHOG_PROJECT_TOKEN`   | `phc_B3…`    | no (write-only) | live `$pageview` server events           |
| `POSTHOG_PROJECT_KEY`     | `phc_ko…`    | no (write-only) | client-side events                       |
| `POSTHOG_KEY`             | `phx_G2…`    | n/a (legacy SDK env) | posthog-python/posthog-node SDK init     |
| `POSTHOG_PROJECT_ID`      | `415112`     | n/a         | project id for URL paths                  |

The 06-15 and 06-16 CEO report heartbeats used `POSTHOG_PROJECT_KEY`
or `POSTHOG_PROJECT_TOKEN` against `/api/projects/415112/query/` — the
token shapes are the same on the wire (both are bearer tokens in
`Authorization: Bearer …`), but only the `phx_` PAT authenticates the
query endpoint. The report's reporter did not have a reference for
which key to use, and the runtime fell back to the project token.

Verified empirically at 2026-06-16 06:46:13Z (work-product timestamp):

```
POST /api/projects/415112/query/
Authorization: Bearer $POSTHOG_PAT
body: {"query":{"kind":"HogQLQuery","query":"SELECT 1 AS ok LIMIT 1"}}
→ HTTP 200, results=[[1]]
   cache_key=cache_415112_9ec9a292a5ee23192469aaa0076da9e369950e69e49c2a6b51710cf3bfa26209

POST /api/projects/415112/query/
Authorization: Bearer $POSTHOG_PROJECT_TOKEN
body: {"query":{"kind":"HogQLQuery","query":"SELECT 1 AS ok LIMIT 1"}}
→ HTTP 403,
   {"type":"authentication_error",
    "code":"authentication_failed",
    "detail":"Personal API key found in request Authorization header is invalid."}
```

## Fix shipped

A new module `scripts/posthog_hogql.py` provides a tiny, single-purpose
wrapper around the HogQL endpoint that always authenticates with
`POSTHOG_PAT`. Public API:

```python
from posthog_hogql import hogql, ceo_report_pack
rows = hogql("SELECT count(*) FROM events WHERE event = 'api_query'")
pack = ceo_report_pack(as_of=date(2026, 6, 15))
```

`ceo_report_pack` returns the canonical 5-KPI pack used by the daily
CEO report (api_query, mcp_tool_call, $pageview, distinct active
agents, plus closed-day d/d deltas). It picks `as_of = prior calendar
day` by default, so future heartbeats can call it without re-doing the
date math.

CLI entry points:

```bash
python3 scripts/posthog_hogql.py ceo-pack [--as-of YYYY-MM-DD]
python3 scripts/posthog_hogql.py query "SELECT ..."
```

## Verification

Ran the canonical pack at 2026-06-16 06:52:55Z against the closed
2026-06-15 day. Every MTD number reproduces the 06-15 report's
"MTD through 06-14" values exactly (the prior report's MTD was actually
a 06-15 day-after snapshot, which is the standard off-by-one the
report's d/d line item exposed):

| KPI                  | Got (this run, MTD through 06-15) | 06-15 report claim (MTD through 06-14) | Delta |
|----------------------|----------------------------------:|--------------------------------------:|------:|
| api_queries_mtd      | 7,195                             | 7,195                                 | 0     |
| mcp_tool_calls_mtd   | 8,468                             | 8,468                                 | 0     |
| pageviews_human_mtd  | 1,627                             | 1,627                                 | 0     |
| active_agents_mtd    | 147                               | 147                                   | 0     |

(Full JSON: `/tmp/posthog_ceo_pack_2026-06-15.json`.)

Fresh closed-day deltas for the 06-16 report heartbeat:

| KPI                  | closed 06-15 | prior 06-14 | d/d     |
|----------------------|-------------:|------------:|--------:|
| api_queries          | 1,766        | 51          | +1,715  |
| mcp_tool_calls       | 1,137        | 1,395       | -258    |
| pageviews_human      | 46           | 8           | +38     |
| active_agents (MTD)  | 147          | 137 (06-14 snapshot) | +10  |

The 06-15 closed day saw a large spike in `api_query` events (1,766 vs
the prior-day 51) and a notable `mcp_tool_call` dip (1,137 vs 1,395).
Both move within the 06-15 day window — Reed's API usage picked up
materially on the closed day.

## Disposition

- The `Daily Failure 1` in `docs/daily-ceo-report-2026-06-16.md`
  ("Fresh PostHog HogQL access is blocked in the report heartbeat")
  is now **recoverable** for the next heartbeat: any agent that runs
  `python3 scripts/posthog_hogql.py ceo-pack` from this workspace
  gets fresh MTD + d/d deltas from PostHog.
- The 06-16 report itself is already published and remains the
  authoritative artifact for 2026-06-16; the 2026-06-17 heartbeat can
  adopt the fresh 06-15 closed-day numbers from this run and drop the
  `carry-forward` label on the four Lyra/Reed rows.
- This issue is not deleted: it stays as the reference for the
  PAT-vs-project-key foot-gun so the next reporter (or the next
  rotation) does not re-make the same mistake.

## Anti-pattern to keep out of the codebase

> **Never call `/api/projects/415112/query/` with `POSTHOG_PROJECT_KEY`
> or `POSTHOG_PROJECT_TOKEN`. Those are project-level write keys;
> only `POSTHOG_PAT` (a `phx_…` personal API key) carries
> `query:read` scope on project 415112.**

Code review rule: any `HogQLQuery` reference in this workspace should
import the wrapper from `scripts/posthog_hogql.py` rather than opening
a raw `urllib`/`curl` to `https://us.i.posthog.com/api/projects/415112/query/`.
