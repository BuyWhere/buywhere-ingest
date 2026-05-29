# Daily CEO Report Follow-up

Date: 2026-05-26
Issue: BUY-24449
Owner: Lyra (CMO)
Workspace: Paperclip issue checkout `_default`

## Scope

This follow-up fills the Lyra KPI freshness gaps called out on `BUY-24087` for the dated
`2026-05-26` CEO report. All metrics below are bounded to the report date, not the next UTC day.

Reporting cutoffs used:

- Paperclip/API spot checks: queried during this follow-up on `2026-05-27`, representing current
  live state for control-plane objects that do not expose historical snapshots in this runner.
- PostHog month-to-date queries: `timestamp >= 2026-05-01 00:00:00 UTC` and
  `timestamp < 2026-05-27 00:00:00 UTC`, so the values stop at the end of `2026-05-26 UTC`.

## Required KPI values

1) Directory listings
- June 30 target: `25`
- Exact current value: `2`
- Gap vs target: `23`
- Source of truth: `GET /api/companies/{companyId}/user-directory`
- Evidence: active directory entries are `Rich` and `Board`
- Caveat: none on the count itself; this is the live company directory visible to the current agent

2) Integrations
- June 30 target: `5`
- Exact current value: `0`
- Gap vs target: `5`
- Source of truth: PostHog project `415112`, month-to-date `api_query` telemetry grouped by
  `properties.agent_framework`
- Method: count distinct non-null, non-`unknown` framework values through `2026-05-26 23:59:59 UTC`
- Evidence: grouped results for the bounded report window were `unknown = 309`, `null = 10`, with
  no named framework bucket
- Caveat: this is exact for the current live telemetry definition, but it is still a telemetry-based
  integration count rather than a manually curated partnership list

3) Developer API keys
- June 30 target: `1,000`
- Exact current value: unavailable from this agent scope
- Best visible value in this runner: `17` runtime-visible key/token registrations
- Source of truth attempted: `GET /api/companies/{companyId}/secrets`
- Result: `403 Board access required`
- Gap note: a company-wide exact count cannot be produced from this role because the secrets inventory
  is permission-gated
- Caveat: the prior `17` figure is exact only for the active runtime environment and should not be
  represented as the company-wide developer API key count

4) Indexed pages
- June 30 target: `50,000`
- Exact current value: unavailable from current access
- Closest public surface observed: `77` submitted sitemap URLs
- Public sitemap breakdown:
  - `33` URLs in `sitemap-pages.xml`
  - `32` URLs in `sitemap-categories.xml`
  - `12` URLs in `sitemap-compare.xml`
- Source of truth required for the KPI: Google Search Console indexed-page coverage
- Access result: the available Google credential in this runner is an API key, not a Search Console
  OAuth token; Search Console requests returned `401 Invalid Credentials`
- Caveat: sitemap URL count is not equivalent to indexed pages and should not replace the indexed-page KPI

5) Monthly visits
- June 30 target: `25,000`
- Exact current value: `20,361` human pageviews month to date through `2026-05-26 23:59:59 UTC`
- Gap vs target: `4,639`
- Source of truth: PostHog project `415112`
- Method: count events in `('$pageview', 'pageview_server')` with `coalesce(JSONExtractBool(properties, 'is_bot'), false) = false`
- Caveat: this is exact for the canonical human-web PostHog definition documented in
  `docs/posthog-marketing-analytics-audit.md`; it is a pageview-based visit KPI, not a session metric

## Conclusion

- Fresh exact values are now available for `directory listings`, `integrations`, and `monthly visits`
  on the `2026-05-26` report date.
- The remaining gaps are confirmed blockers, not stale drafting:
  - company-wide developer API key count requires board-level secrets access
  - indexed-page count requires Google Search Console OAuth access or a separately exported coverage report
