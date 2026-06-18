# PostHog Marketing Analytics Audit

Date: 2026-05-24
Issue: BUY-23137
Project: PostHog `415112`

## Summary

Human-web analytics are live in PostHog for `buywhere.ai`, but the current implementation is not
coming from a browser `posthog-js` snippet. As of 2026-05-24, the live site HTML still loads
Plausible and does not include PostHog client instrumentation.

Despite that, PostHog is receiving website pageview data through the existing pageview event stream:

- `$pageview`
- `pageview_server`

The canonical marketing dashboard is now:

- `BuyWhere - Marketing Web Analytics (Canonical)` dashboard id `1622959`

## Live Findings

### Site instrumentation state

- `https://buywhere.ai` responds `200`
- The rendered HTML includes a Plausible script
- The rendered HTML does not include `posthog-js`

Conclusion:

- PostHog browser autocapture is not the current source of truth for website traffic
- Website pageviews reaching PostHog today are being emitted by server-side or proxy-side capture

### PostHog project state

Observed in project `415112`:

- pageview event definitions exist for `$pageview`, `$autocapture`, and `pageview_server`
- agent segmentation properties already exist:
  - `is_bot`
  - `agent_family`
  - `$virt_traffic_type`
  - `$virt_traffic_category`
  - `$virt_bot_name`

The segmentation properties exist, but they are not currently trustworthy for `pageview_server`.
As of `2026-05-30`, monitor and crawler traffic including `UptimeRobot/2.0`,
`Consolidated-Health-Check/1.0`, and `A2A-Registry-TaskProbe/1.0` is still appearing with
`is_bot = false` on `pageview_server`.

## Dashboard Created

Canonical dashboard id: `1622959`

Panels:

1. `Canonical Marketing — Human Pageviews (30d)`
2. `Canonical Marketing — Human Traffic Sources (30d)`
3. `Canonical Marketing — Human Top Pages (30d)`
4. `Canonical Marketing — Agent vs Human Split (30d)`

Query conventions:

- Temporary human traffic filter: `event = '$pageview' AND properties.is_bot = false`
- Agent/bot split: `multiIf(properties.is_bot = true, 'agent_or_bot', properties.is_bot = false, 'human', 'unknown')`
- Combined `('$pageview', 'pageview_server')` is suspended as a human-web KPI until `pageview_server`
  classification is repaired

## Caveats

- A non-canonical dashboard named `BuyWhere - Marketing Web Analytics` with duplicate tiles was
  created during API retries. Use dashboard `1622959` as the source of truth.
- Because the live site is not loading `posthog-js`, browser-only web analytics features are still
  not actually wired from the public site HTML.
- The prior combined human-pageview definition is now known to be contaminated by `pageview_server`
  traffic hitting `0.0.0.0:8080` with monitor and crawler user agents. See
  [docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md).

## External Dependency

Google Search Console access is still a dependency for Lyra's broader marketing measurement scope.
PostHog covers visits and traffic behavior, but GSC is still required for:

- indexed page coverage
- search query impressions
- indexing errors

Owner to provision access: Rich and/or Rex.
