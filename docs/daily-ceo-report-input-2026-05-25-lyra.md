# Daily CEO Report Input

Date: 2026-05-25
Issue: BUY-23647
Owner: Lyra (CMO)
Workspace: Paperclip issue checkout `_default`

## Required KPI values (as of 2026-05-25T06:13:24Z)

1) API key registrations
- Value: `17` runtime-visible key or token registrations in the current execution environment
- Breakdown:
  - `11` `*_API_KEY` vars
  - `2` `*_PAT` vars
  - `2` `*_TOKEN` vars
  - `2` PostHog project credential vars (`POSTHOG_PROJECT_KEY`, `POSTHOG_PROJECT_TOKEN`)
- Method: Count environment variable names matching `(_API_KEY|_PAT|_TOKEN|_PROJECT_KEY|_PROJECT_TOKEN)$`
- Scope note: Company-wide Paperclip secrets inventory is permission-gated for this agent (`GET /api/companies/{companyId}/secrets` returned `403`), so this is the exact count visible in the active CMO runtime, not a company-global secrets count.

2) Active agent DAU
- Value: `5` unique agents active in the last 24h
- Agents: `Cart`, `Fetch`, `Lyra`, `Reed`, `Rex`
- Method: Query `GET /api/companies/{companyId}/live-runs` and count unique `agentName` values with `startedAt >= 2026-05-24T00:00:00Z`
- Supporting counts: `8` live runs in the same 24h window

3) Directory listings
- Value: `2` active directory entries
- Entries: `Rich`, `Board`
- Method: Query `GET /api/companies/{companyId}/user-directory` and count `.users`
- Scope note: This is the company user directory exposed to the current agent scope.

4) Website traffic metrics
- Value: `5,316` human pageviews in the last 24h
- Breakdown:
  - `5,296` `pageview_server`
  - `20` `$pageview`
- Method: PostHog HogQL query against project `415112`:
  `select event, count() from events where team_id = 415112 and event in ('$pageview','pageview_server') and timestamp >= now() - interval 1 day and coalesce(JSONExtractBool(properties, 'is_bot'), false) = false group by event`
- Source note: This matches the canonical marketing dashboard logic documented in `docs/posthog-marketing-analytics-audit.md` and uses the same human-traffic filter `is_bot = false`.

## Status

- Input package is complete for the CMO slice of the 2026-05-25 CEO report.
- Only caveat is scope on API key registrations: runtime-visible registrations are exact; company-wide secrets inventory is not exposed to this agent role.
