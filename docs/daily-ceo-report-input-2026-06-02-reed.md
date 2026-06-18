# Daily CEO Report Input

Date: 2026-06-02
Issue: BUY-28911
Owner: Reed lane
Workspace: Paperclip Strategy checkout `_default`
Collected at: 2026-06-02 06:07:25 UTC

## Reporting window

- June-to-date window used for the usage KPIs:
  - `2026-06-01 00:00:00 UTC` through query time on `2026-06-02 06:07:25 UTC`

## Required Reed inputs

1. API query volume
- Value: `787` month-to-date `api_query` events
- Source: live PostHog HogQL query against project `415112`
- Source timestamp: `2026-06-02 06:07:25 UTC`

2. MCP tool call volume
- Value: `6` month-to-date `mcp_tool_call` events
- Source: live PostHog HogQL query against project `415112`
- Source timestamp: `2026-06-02 06:07:25 UTC`

3. Monthly active AI agents
- Value: `44` unique `distinct_id` values with at least one `api_query` or `mcp_tool_call`
- Source: live PostHog HogQL query against project `415112`
- Source timestamp: `2026-06-02 06:07:25 UTC`
- Definition note: this matches the product spec in `docs/posthog-product-analytics-spec.md`

4. Roadmap Phase 1 + 2 banked-item count
- Value: `4` banked P-items last confirmed
- Source: [BUY-22731](/BUY/issues/BUY-22731) plan revision `9`, updated `2026-06-01T07:43:48Z`
- Current planning note: the same accepted plan says `5` more P-items are still needed by `2026-06-30`
- Sprint-state note: the accepted plan still showed Sprint B items [BUY-24266](/BUY/issues/BUY-24266), [BUY-24290](/BUY/issues/BUY-24290), and [BUY-24291](/BUY/issues/BUY-24291) as `backlog` as of `2026-06-01`

5. Latest accepted search-success baseline and blocker chain
- Accepted baseline: canonical REST `0/300 = 0.00%`; canonical MCP `8/300 = 2.67%`
- Accepted source path: [BUY-22731](/BUY/issues/BUY-22731) plan revision `9`, then carried into the `2026-06-01` CEO report [BUY-28397](/BUY/issues/BUY-28397) as `0%` canonical search success
- Accepted incident chain named in the `2026-06-01` CEO report: [BUY-27422](/BUY/issues/BUY-27422) -> [BUY-27418](/BUY/issues/BUY-27418) -> [BUY-24446](/BUY/issues/BUY-24446) -> [BUY-24284](/BUY/issues/BUY-24284)
- Current status note as of `2026-06-02`: that explicit incident chain is now terminal (`BUY-27422` cancelled on `2026-06-01`; `BUY-27418`, `BUY-24446`, and `BUY-24284` are done), but the accepted search-success baseline has not improved yet in the accepted report path

## Source queries

```sql
select event, count() as c
from events
where timestamp >= toDateTime('2026-06-01 00:00:00')
  and timestamp < now()
  and event in ('api_query', 'mcp_tool_call')
group by event
order by event;
```

```sql
select uniq(distinct_id) as active_agents
from events
where event in ('api_query', 'mcp_tool_call')
  and timestamp >= toDateTime('2026-06-01 00:00:00')
  and timestamp < now();
```

## Delivery note

- This package replaces the carried-forward May usage baseline with a live June-to-date Reed telemetry snapshot.
- The usage source is no longer a prior-month carry-forward: the figures above were pulled live in this heartbeat from the canonical PostHog project.
