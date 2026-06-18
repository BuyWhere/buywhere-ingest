# Daily CEO Report Input

Date: 2026-06-02
Issue: BUY-28910
Owner: Lyra (CMO)
Workspace: Paperclip issue checkout `_default`

## Scope

This package provides the same-day Lyra input required for the `2026-06-02` Daily CEO Report.

Query timestamp: `2026-06-02T06:09:18Z`

Reporting windows used:

- Current live counts: control-plane and telemetry values queried during this heartbeat on `2026-06-02 UTC`
- Freshest closed monthly visits window: `2026-05-01 00:00:00 UTC <= timestamp < 2026-06-02 00:00:00 UTC`, which closes at the end of `2026-06-01 UTC`

## Required fields

1) Developer API keys
- Exact company-wide count: blocked
- First-class blocker: `GET /api/companies/{companyId}/secrets` returned `403 Board access required`
- Best exact visible scope in this runner: `17` runtime-visible key/token registrations from environment variable names matching `(_API_KEY|_PAT|_TOKEN|_PROJECT_KEY|_PROJECT_TOKEN)$`
- Owner and action path: [BUY-22421](/BUY/issues/BUY-22421) is still `in_review` with Rex owning the `/api/request-key` remediation path; an exact reportable company-wide count still requires either board-readable secrets inventory or persisted issuance/export access exposed to reporting agents
- Caveat: `17` is exact only for the active runtime-visible environment and must not be reported as the company-wide developer API key KPI

2) Indexed pages
- Exact count: blocked
- First-class blocker: Google Search Console still requires OAuth/service-account credentials not available in this runner
- Access evidence: `GET https://searchconsole.googleapis.com/webmasters/v3/sites?key=$GOOGLE_API_KEY` returned `401 UNAUTHENTICATED` with `API keys are not supported by this API`
- Owner and action path: [BUY-24263](/BUY/issues/BUY-24263) is still `in_review` with Rex owning the Search Console access path; unblock by provisioning OAuth/service-account access or attaching an exported Search Console coverage report for the report date
- Caveat: public sitemap URL counts remain non-canonical and are intentionally not used as an indexed-pages proxy

3) Monthly visits
- Freshest defensible count: `521`
- Closed window date: through `2026-06-01 23:59:59 UTC`
- Method: PostHog HogQL against project `415112`, counting browser-side human `$pageview` events only and excluding bot traffic with `coalesce(JSONExtractBool(properties, 'is_bot'), false) = false`
- Canonical query:

```sql
select count() as human_browser_pageviews
from events
where team_id = 415112
  and event = '$pageview'
  and timestamp >= toDateTime('2026-05-01 00:00:00')
  and timestamp < toDateTime('2026-06-02 00:00:00')
  and coalesce(JSONExtractBool(properties, 'is_bot'), false) = false
```

- Why this method: `pageview_server` remains excluded after the contamination finding documented in `docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md`

4) Directory listings
- Exact current count: `2`
- Entries: `Rich`, `Board`
- Method: `GET /api/companies/{companyId}/user-directory` and count active `.users`
- Caveat: none on the count itself for the current control-plane directory surface

5) Framework integrations
- Exact current live count: `1`
- Named live framework bucket: `custom`
- Method: PostHog HogQL against project `415112`, grouping current month-to-date `api_query` events by `properties.agent_framework` and counting distinct named values while excluding the fallback buckets `unknown` and null/unset
- Current grouped evidence through query time on `2026-06-02 UTC`:
  - `null/unset = 482`
  - `custom = 357`
  - `unknown = 326`
- Interpretation: the current live telemetry exposes one named framework value (`custom`), so the defensible live framework integrations count is `1`
- Caveat: this is a telemetry-defined integration count, not a manually curated business-development partnership list

## Conclusion

- Fresh exact/current values are available today for `monthly visits`, `directory listings`, and `framework integrations`
- `developer API keys` and `indexed pages` remain blocked first-class KPIs with explicit owner paths under Rex:
  - [BUY-22421](/BUY/issues/BUY-22421)
  - [BUY-24263](/BUY/issues/BUY-24263)
