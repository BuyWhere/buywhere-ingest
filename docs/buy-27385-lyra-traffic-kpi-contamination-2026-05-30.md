# BUY-27385 Lyra Traffic KPI Contamination

Date: 2026-05-30
Issue: BUY-27385
Owner path: Rex runtime instrumentation, Lyra KPI signoff
Project: PostHog `415112`

## Summary

The previously reported Lyra monthly-visits KPI was contaminated by server-side `pageview_server`
events that were marked `is_bot = false` even when the traffic was clearly monitor, crawler, or
internal probe traffic.

For the bounded month-to-date window `2026-05-01 00:00:00 UTC` through `2026-05-29 23:59:59 UTC`:

- previously reported "human" pageviews from `('$pageview', 'pageview_server')`: `35,196`
- contaminated `pageview_server` rows within that count: `34,713`
- safe browser-only human `$pageview` rows: `483`

## Evidence

Top contaminated `pageview_server` rows marked `is_bot = false`:

- `https://0.0.0.0:8080/` with `Mozilla/5.0+(compatible; UptimeRobot/2.0; http://www.uptimerobot.com/)`: `15,423`
- `https://0.0.0.0:8080/developers` with `Mozilla/5.0+(compatible; UptimeRobot/2.0; http://www.uptimerobot.com/)`: `7,684`
- `https://0.0.0.0:8080/` with Chrome `120.0.0.0`: `3,060`
- `https://0.0.0.0:8080/` with empty user agent: `1,102`
- `https://0.0.0.0:8080/` with `undici`: `439`
- `https://0.0.0.0:8080/` with `A2A-Registry-TaskProbe/1.0`: `280`
- `https://0.0.0.0:8080/` with `node`: `248`
- `https://0.0.0.0:8080/` with `Consolidated-Health-Check/1.0`: `203`
- `https://0.0.0.0:8080/` with `BUY-24505-Enhanced-Frontend-Health-Check/1.1`: `175`

Representative safe browser `$pageview` rows marked `is_bot = false`:

- `/search?q=Rice&country=us`: `52`
- `/search?q=Rice&country=sg`: `51`
- `/search?q=running+shoes&country=us`: `51`
- `/search?country=us`: `51`

## Canonical Query

Use this query for Lyra's human-web KPI until `pageview_server` classification is fixed:

```sql
select count() as human_browser_pageviews
from events
where team_id = 415112
  and event = '$pageview'
  and timestamp >= toDateTime('2026-05-01 00:00:00')
  and timestamp < toDateTime('2026-05-30 00:00:00')
  and coalesce(JSONExtractBool(properties, 'is_bot'), false) = false
```

This produces `483` safe browser-side pageviews for the bounded report window.

## Owner And Exit Criteria

- Report owner: Lyra should use the browser-only query as the source of truth for the CEO report
  until runtime remediation is complete.
- Runtime owner: Rex should update `pageview_server` capture so monitor, crawler, proxy, and health
  check traffic is either not emitted as human traffic or is always marked `is_bot = true`.
- Re-enable the combined `('$pageview', 'pageview_server')` KPI only after validation proves:
  - `0.0.0.0:8080` URLs are absent from human traffic
  - known monitor and crawler user agents are absent from human traffic
  - sampled `pageview_server` human rows correspond to real public-site visits
