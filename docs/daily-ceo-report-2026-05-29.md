# DAILY CEO REPORT — 2026-05-29

Report date: 2026-05-29 UTC
Correction added: 2026-05-30 05:44 UTC
Contract update: 2026-05-30 06:10 UTC
Status: corrected for Rich review
Issue: BUY-26382

## Executive Summary

- The standing workflow contract is now tighter: every KPI row must carry either a day-over-day delta or an explicit blocked/disputed reason in the `Current` cell; bare `Blocked` or unlabeled stale values are no longer acceptable.
- The prior report missed the larger Oracle discovery/runtime surface. The exact products index is `2,767,644` real rows in `public.products` at `2026-05-30 05:41 UTC`, but the live public runtime is now advertising `16,815,356` approximate products from `pg_class_fallback`; the correction is that both numbers need to be shown, with the `16.8M` figure clearly marked non-canonical until [BUY-25133](/BUY/issues/BUY-25133) and [BUY-22720](/BUY/issues/BUY-22720) are resolved.
- The exact products index is moving, but far too slowly. The closed `2026-05-29` UTC day added only `4,741` active products and `4,933` real products, which is materially better than the prior zero-growth day but still nowhere near the `2,947,042/day` active-product pace Oracle needed for that day.
- The prior Lyra traffic claim was overstated. Raw PostHog month-to-date pageviews are `35,196`, but `34,713` of them are `pageview_server` events with `is_bot = false` even though the top URL is `https://0.0.0.0:8080/` and the top user agent is `UptimeRobot/2.0`; only `483` MTD browser `$pageview` events are currently cleanly separable. This is now tracked in [BUY-27385](/BUY/issues/BUY-27385).
- Reed's core product KPI is still a complete failure: canonical search success remains `0%`, so rising website pageviews do not contradict the product result. The live blocker chain remains [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446), and the usage-source regression remains open in [BUY-26393](/BUY/issues/BUY-26393).
- The largest June 30 gaps remain Oracle real products, Reed search success, Reed usage scale, and Lyra's lack of trustworthy visibility instrumentation.

## Daily Failure Summary

1. **Oracle still does not have one executive-safe product count.**
   Lesson learned: the report must show both the exact index count and the larger approximate discovery/runtime surface until the reconciliation line is fixed.

2. **Oracle growth resumed but remains functionally flat against target scale.**
   Lesson learned: `+4,741` active products on the closed `2026-05-29` UTC day is still a severe miss when the required pace is in the millions per day.

3. **Lyra's traffic KPI is contaminated by monitors and crawlers.**
   Lesson learned: a raw event total is not a marketing KPI if server-side pageview events are marking `UptimeRobot` and `ClueWeb-Crawler` as `is_bot = false`.

4. **Reed search quality is still at the floor.**
   Lesson learned: top-of-funnel traffic or marketing activity does not matter while the canonical product-success KPI remains `0%`.

5. **Reed's telemetry source path is still unstable.**
   Lesson learned: usage counters are not operationally trustworthy when the previously canonical `/v1/usage/summary` endpoint has regressed to `404`.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---:|---:|---:|---|
| **ORACLE** | | | | |
| Products found / runtime surface | `16,815,356` approx runtime at `2026-05-30 05:40 UTC`; disputed because the prior stored runtime snapshot (`1,575,624` on `2026-05-28 06:12 UTC`) is not yet reconciled to the same canonical surface | 100,000,000 | 83,184,644 short on the approximate surface | [BUY-25133](/BUY/issues/BUY-25133) -> [BUY-22720](/BUY/issues/BUY-22720) |
| Products index | `2,767,644` exact DB; `+4,933` on the closed `2026-05-29` UTC day | 100,000,000 | 97,232,356 short | [BUY-22739](/BUY/issues/BUY-22739) -> [BUY-24283](/BUY/issues/BUY-24283) |
| Real merchants | `15,077` exact DB; `+4` versus the `2026-05-29 06:10 UTC` report snapshot | 150,000 | 134,923 short | Same growth chain; merchant definition is catalog-backed merchants in `public.products` |
| US coverage | `5.90%` exact DB; `+0.01 pp` versus the prior report snapshot | 50% | 44.10 pp short | Overall ingestion and coverage gap |
| Platforms | `48` exact active; `0 d/d` in the stored reporting path | 35 | 13 above target | None on count; growth path still blocked |
| **LYRA** | | | | |
| Indexed pages | Blocked; exact count blocked pending Search Console access | 50,000 | Exact count blocked | [BUY-24263](/BUY/issues/BUY-24263) |
| Developer API keys | Blocked; exact count blocked because persisted `api_keys` row creation is not live end-to-end | 1,000 | Exact count blocked | [BUY-22421](/BUY/issues/BUY-22421) |
| Monthly visits | `35,196` raw MTD, but `34,713` are contaminated `pageview_server`; only `483` browser `$pageview` events are cleanly separable | 25,000 | Disputed: raw is `10,196` above target, browser-only is `24,517` short | [BUY-27385](/BUY/issues/BUY-27385) |
| Directory listings | `2`; `0 d/d` | 25 | 23 short | Execution lag; source path on [BUY-22687](/BUY/issues/BUY-22687) |
| Framework integrations | `0`; `0 d/d` | 5 | 5 short | Execution lag |
| **REED** | | | | |
| API queries / month | `348` direct PostHog MTD; `+29` versus the last confirmed `319` MTD package | 500,000 | 499,652 short | Disputed against runtime snapshot; [BUY-26393](/BUY/issues/BUY-26393) |
| MCP tool calls / month | `81` direct PostHog MTD; disputed because same-day runtime-source refresh is unavailable in this path | 200,000 | 199,919 short | Disputed against runtime snapshot; [BUY-26393](/BUY/issues/BUY-26393) |
| Search success | `0%` canonical; `0 pp d/d` | 85% | 85 pp short | [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446) |
| Roadmap Phase 1 + 2 | `4` banked P-items last confirmed; `0 d/d` in this report path | >=9 of 14 | 5 short | Search-state delay reduces roadmap confidence |
| Active AI agents / month | `184` last confirmed runtime snapshot; disputed because same-day refresh is unavailable in this path | 100 | 84 above target | Same-day refresh path now tracked in [BUY-26393](/BUY/issues/BUY-26393) |
| **REX** | | | | |
| API p95 latency | `613 ms` last confirmed probe; `0 d/d` in this report path because no fresh same-day latency artifact was published | <100 ms | 513 ms above target | No fresh same-day artifact; lane tracked on [BUY-22685](/BUY/issues/BUY-22685) |
| Engineering deliverables | `0` exact in the June window; June has not started yet in this dated report | 40 / month | 40 short once June opens | Counting rule artifact on [BUY-24542](/BUY/issues/BUY-24542) |
| Catalog-growth unblock | `No`; `0 d/d` | Yes | Not complete | [BUY-22739](/BUY/issues/BUY-22739) -> [BUY-24283](/BUY/issues/BUY-24283) |
| Core uptime | `99.985%` last confirmed; `0 d/d` in this report path | >99.9% | On target | None |

## Vera

Current focus:
- publish a corrected dated CEO report that separates Oracle's exact index from the larger approximate runtime surface, adds visible deltas, and stops treating Lyra's contaminated pageview stream as a clean win

24-hour movement and required pace:
- the report lane now has a corrected Oracle denominator split: `2,767,644` exact indexed products versus `16,815,356` approximate runtime-surface products
- the closed `2026-05-29` UTC day did show Oracle growth again, but only `+4,741` active products and `+4,933` real products
- Lyra's visit KPI moved from "above target" to "instrumentation-disputed" after direct event inspection
- Reed's quality lane remains unchanged at `0%` canonical search success

Plan and adjustments being made today:
- keep exact Postgres `public.products` metrics as the canonical products index
- show the approximate runtime/discovery surface separately until [BUY-25133](/BUY/issues/BUY-25133) and [BUY-22720](/BUY/issues/BUY-22720) are resolved
- replace the prior Lyra traffic claim with a source-quality caveat and route the instrumentation repair to [BUY-27385](/BUY/issues/BUY-27385)
- keep Reed's blocker chain explicit rather than hiding behind volume or traffic proxies

Five biggest failures of the day:
1. The original report did not reflect the larger `16.8M` Oracle runtime-surface number.
   Lesson learned: denominator disputes must be surfaced, not normalized away.
2. The report treated raw Lyra pageviews as trustworthy human visits.
   Lesson learned: event-source inspection is mandatory before calling a KPI a win.
3. Reed still has no usable same-day canonical usage endpoint.
   Lesson learned: reporting durability is part of product execution.
4. I still depend on owner-thread blocker state rather than one self-healing scoreboard path.
   Lesson learned: daily executive reporting is exposing product-system seams that remain unresolved.
5. Search success is still pinned at `0%`.
   Lesson learned: the product remains a failure until the canonical success metric moves.

Current blockers:
- [BUY-24283](/BUY/issues/BUY-24283) still gates Oracle growth recovery
- [BUY-24446](/BUY/issues/BUY-24446) still gates Reed search-quality recovery
- [BUY-26393](/BUY/issues/BUY-26393) still gates Reed usage-source reconciliation
- [BUY-27385](/BUY/issues/BUY-27385) now gates trust in Lyra's visits KPI

Active work in progress:
- corrected report publication and Rich re-review
- same-day source-of-truth reconciliation across Oracle, Lyra, and Reed

Source of truth:
- this report
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)
- [BUY-24539](/BUY/issues/BUY-24539)
- [BUY-24540](/BUY/issues/BUY-24540)
- [BUY-24541](/BUY/issues/BUY-24541)

## Rex

Current focus:
- keep uptime above target, reduce latency, own runtime metric integrity, and clear the unblock chain that gates Oracle's catalog-growth target

24-hour movement and required pace:
- core uptime remains `99.985%`, which is on target
- API p95 remains `613 ms` on the last confirmed probe package; there is still no fresh same-day latency artifact in this report path
- the public runtime now reports `16,815,356` approximate products, which makes the catalog-stats/source-of-truth drift more visible, not less
- a new same-day runtime-quality follow-up now exists in [BUY-27385](/BUY/issues/BUY-27385) because Lyra's server-side pageview stream is misclassifying monitors and crawlers as human traffic

Plan and adjustments being made today:
- keep probe-backed uptime/latency visible until a fresh same-day package is published
- continue the unblock chain under [BUY-22685](/BUY/issues/BUY-22685) and [BUY-22739](/BUY/issues/BUY-22739)
- restore runtime metric integrity on both `/v1/catalog/stats` and the server-side PostHog pageview path

Five biggest failures of the day:
1. API p95 is still `613 ms` against a `<100 ms` target.
   Lesson learned: uptime alone is not enough.
2. The catalog-growth unblock is still incomplete.
   Lesson learned: Oracle's headline target is still an engineering dependency.
3. The public catalog stats endpoint still serves approximate counts from `pg_class_fallback`.
   Lesson learned: shared runtime metrics need canonical flags or they create executive confusion.
4. The Lyra pageview stream still marks monitors/crawlers as `is_bot = false`.
   Lesson learned: analytics infrastructure is production infrastructure.
5. No fresh same-day latency artifact was available in this run.
   Lesson learned: operational KPIs need reproducible refresh paths.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-22720](/BUY/issues/BUY-22720)
- [BUY-22739](/BUY/issues/BUY-22739)
- [BUY-24283](/BUY/issues/BUY-24283)
- [BUY-27385](/BUY/issues/BUY-27385)

Active work in progress:
- infra and catalog work continue under [BUY-22685](/BUY/issues/BUY-22685)
- runtime integrity of reporting surfaces remains a standing concern

Source of truth:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-24542](/BUY/issues/BUY-24542#document-june_engineering_deliverables_count)
- [BUY-25133](/BUY/issues/BUY-25133)

## Oracle

Current focus:
- grow the indexed catalog, keep exact DB-backed scoreboard values current, and reconcile the larger discovery/runtime surface into one trustworthy executive line

24-hour movement and required pace:
- exact live DB snapshot at `2026-05-30 05:41 UTC` shows `2,752,385` active products, `2,767,644` real products, `15,077` catalog-backed merchants, and `163,167 / 2,767,644 = 5.90%` US product-row coverage
- the closed `2026-05-29` UTC day added `4,741` active products and `4,933` real products
- the public runtime now reports `16,815,356` approximate products from `pg_class_fallback`; that is the larger "products found" number the prior report failed to surface
- real indexed products still need `97,232,356` more, or about `3.04M/day` over the remaining `32` days after the closed day

Plan and adjustments being made today:
- keep the exact Postgres `public.products` / `count(distinct merchant_id)` definitions as the canonical products-index source of truth
- show the larger approximate runtime surface as a separate line item instead of burying it
- keep the exact-vs-approximate boundary explicit until [BUY-25133](/BUY/issues/BUY-25133) and [BUY-22720](/BUY/issues/BUY-22720) land

Five biggest failures of the day:
1. The exact products index is still only `2,767,644 / 100,000,000`.
   Lesson learned: the growth gap is too large for partial progress to count as comfort.
2. The closed `2026-05-29` UTC day added only `4,741` active products.
   Lesson learned: growth existing at all is not the same as growth at target scale.
3. The report path still lacks one reconciled discovery -> index -> runtime product count.
   Lesson learned: denominator drift creates executive confusion and hides operational truth.
4. US coverage is still only `5.90%`.
   Lesson learned: footprint breadth remains far behind scale goals.
5. Merchant scale remains only `15,077 / 150,000`.
   Lesson learned: merchant expansion is not tracking the target path either.

Current blockers:
- [BUY-22739](/BUY/issues/BUY-22739)
- [BUY-24283](/BUY/issues/BUY-24283)
- [BUY-25133](/BUY/issues/BUY-25133)
- [BUY-22720](/BUY/issues/BUY-22720)

Active work in progress:
- Oracle daily shortfall reporting remains active
- historical reconciliation and source-of-truth guidance remain active in [BUY-24539](/BUY/issues/BUY-24539)

Source of truth:
- [docs/daily-product-target-shortfall-2026-05-29.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-05-29.md)
- [docs/daily-product-target-shortfall-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-05-30.md)
- [BUY-24539](/BUY/issues/BUY-24539)
- [BUY-25133](/BUY/issues/BUY-25133)
- direct Postgres query on `public.products`
- live `GET https://api.buywhere.ai/v1/catalog/stats`

## Lyra

Current focus:
- grow distribution and integrations while replacing the contaminated raw pageview total with a trustworthy human-web KPI

24-hour movement and required pace:
- raw PostHog month-to-date pageviews are `35,196`, but `34,713` of those events are contaminated `pageview_server` rows; only `483` browser `$pageview` events are cleanly separable today
- the raw pageview stream rose because the dominant source is server-side traffic emitted on `https://0.0.0.0:8080/...`, not because the business has validated a comparable rise in real human marketing demand
- directory listings remain `2`; Lyra still needs `23`, or about `0.70/day`
- integrations remain `0`; Lyra still needs `5`, or about `0.15/day`

Plan and adjustments being made today:
- stop treating `('$pageview','pageview_server')` with `is_bot = false` as a clean visits KPI
- route the instrumentation repair to [BUY-27385](/BUY/issues/BUY-27385)
- keep indexed pages blocked on [BUY-24263](/BUY/issues/BUY-24263)
- keep developer keys blocked on [BUY-22421](/BUY/issues/BUY-22421)

Five biggest failures of the day:
1. The top claimed Lyra KPI win was not clean.
   Lesson learned: raw pageview volume can be worse than no KPI if it is polluted by monitors and crawlers.
2. `UptimeRobot/2.0` is the top "human" user agent in the server-side pageview stream at `23,107` MTD events.
   Lesson learned: bot classification is broken on the current path.
3. The top pageview URLs are `https://0.0.0.0:8080/` and `https://0.0.0.0:8080/developers`.
   Lesson learned: the current source is a server-side/proxy path, not a trustworthy website-visits dashboard.
4. Directory listings are still only `2 / 25`.
   Lesson learned: distribution work needs throughput discipline.
5. Integrations are still `0 / 5`.
   Lesson learned: zero integrations is a real miss, not a placeholder.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22703](/BUY/issues/BUY-22703)
- [BUY-22704](/BUY/issues/BUY-22704)
- [BUY-27385](/BUY/issues/BUY-27385)

Active work in progress:
- directory inventory and submission path under [BUY-22687](/BUY/issues/BUY-22687)
- traffic instrumentation correction is now active in [BUY-27385](/BUY/issues/BUY-27385)

Source of truth:
- [BUY-24541](/BUY/issues/BUY-24541)
- direct PostHog query on `('$pageview','pageview_server')` with live event inspection
- [BUY-22687](/BUY/issues/BUY-22687)

## Reed

Current focus:
- repair search quality, reconcile the KPI-source regression, and keep adoption metrics visible without pretending disputed counters are canonical

24-hour movement and required pace:
- direct same-day PostHog still shows only `348` API queries MTD and `81` MCP tool calls MTD on the disputed direct source
- last confirmed runtime snapshot still shows `184` monthly active AI agents, which is `84` above target
- canonical search success remains `0%`
- the reason traffic can rise while search success stays at zero is simple: Lyra pageviews are a top-of-funnel website metric, while Reed's search-success KPI is a basket-based product-quality metric blocked by unresolved search-state/FTS issues

Plan and adjustments being made today:
- keep the disputed volume counters visible with explicit source labels
- use [BUY-26393](/BUY/issues/BUY-26393) to restore one canonical usage-source path before the next report
- keep search quality anchored to the basket-based canonical KPI instead of softer proxies
- keep the live blocker chain explicit: [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446)

Five biggest failures of the day:
1. Search success is still `0%`.
   Lesson learned: the product-quality lane is still failing at the core task.
2. The previously canonical `/v1/usage/summary` path still returns `404`.
   Lesson learned: reporting endpoints need ownership and durability, not one-off success.
3. Same-day PostHog usage counts still do not reconcile to the last runtime snapshot.
   Lesson learned: metric-source drift is itself a product execution failure.
4. API queries remain tiny against target even on the more favorable last confirmed snapshot.
   Lesson learned: demand remains far below goal.
5. MCP tool-call adoption remains tiny against target even before the source dispute is resolved.
   Lesson learned: telemetry maturity still has not translated into meaningful usage scale.

Current blockers:
- [BUY-24284](/BUY/issues/BUY-24284)
- [BUY-24439](/BUY/issues/BUY-24439)
- [BUY-24446](/BUY/issues/BUY-24446)
- [BUY-26393](/BUY/issues/BUY-26393)

Active work in progress:
- roadmap plan remains active in [BUY-22731](/BUY/issues/BUY-22731#document-plan)
- telemetry-source reconciliation is now active in [BUY-26393](/BUY/issues/BUY-26393)

Source of truth:
- [BUY-24540](/BUY/issues/BUY-24540)
- direct PostHog query on `api_query` and `mcp_tool_call`
- [BUY-22731](/BUY/issues/BUY-22731#document-plan)

## What Has Been Accomplished

- Corrected the report to surface the larger `16,815,356` approximate Oracle runtime/discovery number alongside the exact `2,767,644` indexed-product count.
- Added daily or latest-available change notes into the KPI table so flat or tiny movement is visible.
- Reclassified Lyra's monthly-visits metric from "above target" to "instrumentation-disputed" after direct event inspection.
- Created same-day follow-up [BUY-27385](/BUY/issues/BUY-27385) so the Lyra traffic instrumentation defect has a named owner path.
- Preserved the existing same-day follow-up [BUY-26393](/BUY/issues/BUY-26393) so Reed's disputed usage-source path remains owned before the next report cycle.

## Key Things Needed To Hit June 30 Goals

- Oracle needs [BUY-22739](/BUY/issues/BUY-22739) and [BUY-24283](/BUY/issues/BUY-24283) cleared so growth resumes immediately and materially.
- Oracle also needs [BUY-25133](/BUY/issues/BUY-25133) and [BUY-22720](/BUY/issues/BUY-22720) resolved so one product denominator can be trusted in executive reporting.
- Reed needs [BUY-24446](/BUY/issues/BUY-24446) completed so the canonical search-success KPI can move off `0%`.
- Reed needs [BUY-26393](/BUY/issues/BUY-26393) completed so the next report can use one canonical same-day usage source.
- Lyra needs [BUY-27385](/BUY/issues/BUY-27385) completed so website visits become a trustworthy KPI again.
- Lyra still needs [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263) resolved so blocked KPIs become exact numbers.

## Board Blockers Summary

- [BUY-24283](/BUY/issues/BUY-24283): Oracle ingestion recovery still terminally blocks catalog growth.
- [BUY-22720](/BUY/issues/BUY-22720): public catalog-stats parity is still unresolved, so the runtime product denominator remains non-canonical.
- [BUY-24446](/BUY/issues/BUY-24446): live search-state repair still blocks Reed's headline quality KPI.
- [BUY-26393](/BUY/issues/BUY-26393): same-day follow-up for Reed usage-source reconciliation before the next CEO report cycle.
- [BUY-27385](/BUY/issues/BUY-27385): same-day follow-up for Lyra pageview bot/monitor contamination before the next CEO report cycle.
- [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263): blocked Lyra KPI surfaces remain unresolved.

## Incidents And Execution Path

- Oracle incident path: [BUY-22684](/BUY/issues/BUY-22684) -> [BUY-22739](/BUY/issues/BUY-22739) -> [BUY-24283](/BUY/issues/BUY-24283)
- Oracle reporting-integrity path: [BUY-24539](/BUY/issues/BUY-24539) -> [BUY-25133](/BUY/issues/BUY-25133) -> [BUY-22720](/BUY/issues/BUY-22720)
- Reed incident path: [BUY-22731](/BUY/issues/BUY-22731) -> [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446)
- Reed reporting-integrity path: [BUY-26382](/BUY/issues/BUY-26382) -> [BUY-26393](/BUY/issues/BUY-26393)
- Lyra measurement path: [BUY-22687](/BUY/issues/BUY-22687) -> [BUY-27385](/BUY/issues/BUY-27385)

## Source Inputs

- [docs/daily-product-target-shortfall-2026-05-29.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-05-29.md)
- [docs/daily-product-target-shortfall-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-05-30.md)
- [docs/oracle-catalog-stats-reconciliation-2026-05-28.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/oracle-catalog-stats-reconciliation-2026-05-28.md)
- [docs/posthog-marketing-analytics-audit.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/posthog-marketing-analytics-audit.md)
- [BUY-24539](/BUY/issues/BUY-24539)
- [BUY-24540](/BUY/issues/BUY-24540)
- [BUY-24541](/BUY/issues/BUY-24541)
- [BUY-24542](/BUY/issues/BUY-24542#document-june_engineering_deliverables_count)
- [BUY-25133](/BUY/issues/BUY-25133)
- [BUY-26393](/BUY/issues/BUY-26393)
- [BUY-27385](/BUY/issues/BUY-27385)
- direct Postgres queries on `public.products`
- direct PostHog queries on project `415112`
- live `GET https://api.buywhere.ai/v1/catalog/stats`
