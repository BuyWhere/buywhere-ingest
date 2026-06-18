# Daily CEO Report Format Contract

This document defines the standing contract for all future dated daily CEO reports.

## Required section order

Every report must keep this order:

1. `# DAILY CEO REPORT — YYYY-MM-DD`
2. `Report date`, correction timestamp if needed, status, issue
3. `## Executive Summary`
4. `## Daily Failure Summary`
5. `## June 30 KPI Summary`
6. Per-agent sections in this order: `Vera`, `Rex`, `Oracle`, `Lyra`, `Reed`
7. Closing accomplishment / needs / blocker sections when applicable
8. `## Source Inputs`

## KPI table contract

The KPI table format is non-negotiable:

`| KPI | Current | Target | Gap | Blocker |`

No extra columns may be added.

Oracle rows must appear first, then Lyra, then Reed, then Rex.

## KPI row evidence rule

Every KPI row must include one of the following in the `Current` cell:

- an explicit day-over-day delta such as `+4,933`, `0 d/d`, or `+0.01 pp`
- an explicit blocked reason such as `Blocked; exact count blocked pending Search Console access`
- an explicit disputed reason such as `Disputed; raw counter contaminated by bot traffic`

It is not acceptable to show a KPI row with only a bare current value and no movement/reason qualifier.
It is not acceptable to show only `Blocked` or only `Disputed` without the reason.

If no defensible prior-day comparison exists, say that directly in the row, for example:

- `15,070 exact DB; prior-day delta unavailable from stored artifacts`
- `Blocked; exact count blocked because persisted key issuance is not live`

## Interpretation rules

- Exact and approximate surfaces must be labeled separately when both are shown.
- If a metric is blocked, the blocking issue belongs in `Blocker`, but the reason it is blocked must still be written in `Current`.
- If a metric is disputed, the dispute source must be written in `Current`, and the owning follow-up belongs in `Blocker`.
- Use percentage-point deltas (`pp`) for rates and percentages.
- Use the closed report day for daily deltas when the metric is day-bounded.

## Standing correction rules

- Search must be reported in two separate ways:
  - `Live search health` is the primary operational metric and must come from live request telemetry such as `query_log` with an explicit window, zero-result rate, and latency statistic.
  - The `35-query relevance benchmark` is a separate acceptance metric and must never be presented as if it were a live uptime or live success-rate metric.
- API-key `tier` labels such as `enterprise`, `pro`, or `partner` are signup metadata, not paid subscriptions. Do not present them as revenue, customers, or subscription traction unless a real payment rail and entitlement gate exist.
- `Active users` for BuyWhere means distinct API keys that actually queried in a stated window. Always state the window. Do not use email verification, verified-vs-unverified splits, or cumulative registered totals as engagement metrics.
- The `Daily Failure Summary` and each executive section's failure list must include:
  - what failed
  - the specific remediation action / issue / PR
  - current status (`fixed`, `in_progress`, or `blocked-on-X`)
  Lessons learned may remain, but they are additive.
- Every headline number in the `Executive Summary` and `Daily Failure Summary` must be traceable to a direct query, product endpoint, or a dated source issue/document/comment that itself contains the query evidence. The report must include that source path in `Source Inputs`.

## Catalog total — single source of truth rule

The catalog total KPI row must cite only ONE source:

- **Canonical DB**: `data/.catalog_db_url` (maglev) via `pg_class.reltuples` or exact `count(*)`, with the source explicitly named as `canonical DB`.
- The runtime `/v1/catalog/stats` surface (`api.buywhere.ai`) is **operational telemetry only** and must **not** be cited as a KPI source in the daily CEO report. It is not canonical when it diverges from the canonical DB (confirmed drift of 2–3% and growing in recent days).
- When both surfaces are available, show only the canonical DB number. If the canonical exact count is not available within heartbeat budget, use `pg_class.reltuples` from the canonical DB with an explicit `approximate` label — but still cite only that one source.

## Merchant KPI — single source of truth rule

The merchant KPI row must measure only product-backed merchants:

- **Canonical merchant metric**: `COUNT(DISTINCT public.products.merchant_id)` from the canonical DB (`data/.catalog_db_url`).
- `public.merchants` is a registry / dimension table, not the CEO merchant KPI surface. Do **not** substitute `count(*)`, `reltuples`, or any other `public.merchants`-derived value into the merchant KPI slot.
- If the exact distinct-merchant query is too expensive to refresh within heartbeat budget, carry the **last confirmed exact** `COUNT(DISTINCT public.products.merchant_id)` with its as-of timestamp and explicitly label the row as stale / blocked for fresh exact refresh.
- If you need additional context, mention `public.merchants` only in prose as a separate registry-size/supporting metric, never as the KPI itself.

## Delivery rules

- The report must optimize for scan speed before completeness.
- Any report that breaks this contract is an execution failure and must be corrected the same day.
