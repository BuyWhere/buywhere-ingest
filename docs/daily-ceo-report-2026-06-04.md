# DAILY CEO REPORT — 2026-06-04

Report date: 2026-06-04 UTC
Finalized at: 2026-06-04T06:12:00Z
Status: final for Rich review
Issue: BUY-29888

Manual source-of-truth notes:
- Canonical Oracle catalog source for this run: `data/.catalog_db_url` -> `maglev.proxy.rlwy.net:31310/railway?sslmode=require`.
- I did not use the harness `DATABASE_URL`.
- Fresh exact pinned-DB top-line counts at `2026-06-04 06:05 UTC`: `16,816,511` total products and `16,795,602` active products.
- The public runtime surface is still stale at `2026-06-04 06:05:46 UTC`: `GET https://api.buywhere.ai/v1/catalog/stats` returned `16,816,466` total products and `16,816,466` active products, which is still `45` rows behind the exact pinned DB and still reports an incorrect active-products figure. Runtime-surface reconciliation remains tracked under [BUY-25134](/BUY/issues/BUY-25134).
- Last confirmed exact Oracle sub-counts remain from the pinned-DB `2026-06-03 06:02 UTC` package: `24,935` distinct product-backed merchants, `90` populated platforms, and `7,509,763` US-tagged product rows. Today's exact top-line rerun is unchanged, so there is no evidence of material improvement in those sub-count families.
- Fresh exact `public.merchants` registry count at `2026-06-04 06:02 UTC`: `68,384` rows. This is context, not the June 30 real-merchants KPI.
- The exact product source of truth still reconciles the older "~14M plus ~4M newly catalogued" narrative into one live total of `16,816,511` rows on the pinned maglev catalog. The public runtime surface still lags at `16,816,466`, so the reconciliation task remains live under [BUY-25134](/BUY/issues/BUY-25134).

## Executive Summary

- Oracle's top line is flat again. The exact pinned-DB rerun is unchanged at `16,816,511` total products and `16,795,602` active products, so the company remains `83,183,489` products short of target and still needs roughly `3,079,018/day` over the remaining `27` calendar days through `2026-06-30`.
- The biggest measurable positive move today is Lyra's traffic freshness, not goal closure: browser-side human monthly visits improved from `730` to `765` through the closed `2026-06-03` UTC window. Reed usage is flat versus yesterday at `1,429` API queries, `6` MCP tool calls, and `59` active AI agents.
- Rex's production health moved the wrong way. Same-day API Catalog Discovery probe p95 worsened from `560 ms` to `621 ms`, and the trailing-24-hour mean uptime across the three core monitors fell from `99.971%` to `99.566%`, now below the `>99.9%` target.
- The most important live blocker chains are [BUY-29183](/BUY/issues/BUY-29183) -> [BUY-29190](/BUY/issues/BUY-29190) for runtime/search latency, [BUY-25134](/BUY/issues/BUY-25134) for runtime/catalog scoreboard integrity, [BUY-24263](/BUY/issues/BUY-24263) for exact indexed-pages reporting, [BUY-22421](/BUY/issues/BUY-22421) for exact company-wide API-key reporting, and [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859) for replacing Reed's stale June 1 accepted search-success baseline.

## Daily Failure Summary

1. Oracle delivered another flat exact top-line day.
   Lesson learned: "writer recovered" is still a failure if the next executive-day count is unchanged.
2. The runtime catalog surface still disagrees with the canonical DB.
   Lesson learned: executive-safe scoreboards require one durable serving path, not a private exact path plus a stale public path.
3. API p95 worsened to `621 ms` and core uptime fell below target.
   Lesson learned: live monitoring only matters if it forces immediate operational correction.
4. Exact indexed pages and exact company-wide developer API keys are still blocked by missing access.
   Lesson learned: unresolved access paths are KPI blockers, not reporting footnotes.
5. Reed's accepted search-success baseline still has not improved, and live usage is flat day over day.
   Lesson learned: usage telemetry cannot compensate for a still-broken core search promise.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---:|---:|---:|---|
| Products found / runtime surface | Exact pinned DB is `16,816,511`; `0 d/d` versus the `2026-06-03` exact package. Public runtime stats are still stale at `16,816,466`, `45` behind canonical | 100,000,000 | 83,183,489 short | [BUY-25134](/BUY/issues/BUY-25134) |
| Products index | `16,795,602` exact active products from pinned DB; `0 d/d` versus the `2026-06-03` exact package | 100,000,000 | 83,204,398 short | [BUY-22685](/BUY/issues/BUY-22685) |
| Real merchants | `24,935` last confirmed exact distinct product-backed merchants from the `2026-06-03` pinned-DB package; today's exact top-line rerun is unchanged, so no evidence of merchant growth | 150,000 | 125,065 short | [BUY-22685](/BUY/issues/BUY-22685) |
| US coverage | `44.66%` last confirmed exact product-row share (`7,509,763 / 16,816,511`); today's exact top-line rerun is unchanged, so no evidence of improvement | 50% | 5.34 pp short | [BUY-22685](/BUY/issues/BUY-22685) |
| Platforms | `90` last confirmed exact populated platform values from the `2026-06-03` pinned-DB package; today's exact top-line rerun is unchanged | 35 | 55 above target | None on count |
| Indexed pages | Blocked; exact count blocked because Search Console still requires OAuth/service-account credentials and `GET .../webmasters/v3/sites?key=$GOOGLE_API_KEY` returned `401 UNAUTHENTICATED` | 50,000 | Exact gap blocked | [BUY-24263](/BUY/issues/BUY-24263) |
| Monthly visits | `765` browser-side human `$pageview` events through the closed `2026-06-03` UTC window; `+35 d/d` versus yesterday's closed-window `730` | 25,000 | 24,235 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Developer API keys | Blocked; exact company-wide count blocked because `GET /api/companies/{companyId}/secrets` returned `403 Board access required`; runtime-visible env registrations are `26` but not the KPI | 1,000 | Exact gap blocked | [BUY-22421](/BUY/issues/BUY-22421) |
| Directory listings | `2` exact current directory entries (`Rich`, `Board`); `0 d/d` | 25 | 23 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Framework integrations | `1` named live framework bucket (`custom`); `0 d/d` on count | 5 | 4 short | [BUY-22687](/BUY/issues/BUY-22687) |
| API queries / month | `1,429` June-to-date live PostHog `api_query` events at `2026-06-04 06:02:39 UTC`; `0 d/d` versus yesterday's report snapshot | 500,000 | 498,571 short | [BUY-22731](/BUY/issues/BUY-22731) |
| MCP tool calls / month | `6` June-to-date live PostHog `mcp_tool_call` events; `0 d/d` | 200,000 | 199,994 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Search success | `0%` canonical REST and `2.67%` accepted MCP harness baseline; `0 d/d` because the June 1 accepted baseline still has not been replaced | 85% | 85 pp short on REST; 82.33 pp short on MCP | [BUY-29852](/BUY/issues/BUY-29852) |
| Active AI agents / month | `59` June-to-date unique active agents on `api_query` or `mcp_tool_call`; `0 d/d` | 100 | 41 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Roadmap Phase 1 + 2 | `4` banked P-items last confirmed in the accepted plan path; prior-day delta unavailable from a newer accepted revision | >=9 of 14 | 5 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| API p95 latency | `621 ms` same-day probe-based p95 on `API Catalog Discovery`; `+61 ms d/d` versus yesterday's `560 ms` package | <100 ms | 521 ms above target | [BUY-29183](/BUY/issues/BUY-29183) |
| Engineering deliverables | `11` exact qualifying Rex engineering deliverables in June UTC so far after counting the new sustained-write recovery close under [BUY-29835](/BUY/issues/BUY-29835); `+1 d/d` | 40 / month | 29 short | [BUY-22685](/BUY/issues/BUY-22685) |
| Core uptime | `99.566%` trailing-24-hour mean across the three core production monitors; `-0.405 pp d/d` and weakest monitor was `API Catalog Discovery` at `99.512%` | >99.9% | 0.334 pp below target | [BUY-29183](/BUY/issues/BUY-29183) |
| Catalog-growth unblock | `Yes`; `0 d/d` and the historical unblock chain remains closed | Yes | Complete | None on the historical gate |

## Vera

Current focus:
- publish the dated `2026-06-04` CEO report with fresh same-heartbeat top-line Oracle counts, live Lyra and Reed telemetry, and same-day Rex production-health evidence

24-hour movement and required pace:
- renamed the execution issue to the required dated form and reran the exact Oracle top-line counts against `data/.catalog_db_url`
- the exact Oracle top line is flat day over day, so the required real-product pace is now roughly `3,079,018/day`
- Lyra monthly visits improved by `35`, while Reed usage is flat and Rex production health worsened

Plan and adjustments being made today:
- keep the pinned maglev DB as the only valid Oracle source of truth
- keep the runtime/public catalog drift explicit until [BUY-25134](/BUY/issues/BUY-25134) is closed
- keep blocked Lyra KPIs explicit with named owner/action paths instead of substituting softer proxies
- keep Reed search success anchored to the last accepted baseline until the rerun path under [BUY-29852](/BUY/issues/BUY-29852) lands
- route the finished report to [@Rich](user://MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6) through the issue-document confirmation path

Five biggest failures of the day:
1. Oracle top-line exact counts were flat again.
   Lesson learned: top-line stasis invalidates any optimistic recovery narrative.
2. The public runtime catalog surface is still stale.
   Lesson learned: exact truth without public reconciliation is still an execution gap.
3. Two Lyra KPIs remain access-blocked.
   Lesson learned: missing auth paths are still delivery blockers.
4. Rex production health regressed.
   Lesson learned: a daily report has to surface worsening health immediately.
5. Reed search success is still stale.
   Lesson learned: accepted baselines must be actively replaced, not passively carried.

Current blockers:
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-29183](/BUY/issues/BUY-29183)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-29852](/BUY/issues/BUY-29852)

Active work in progress:
- final report publication to the `daily_ceo_report` issue document
- Rich review routing and confirmation

Source of truth:
- this report
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)
- [docs/daily-ceo-report-2026-06-03.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-2026-06-03.md)

## Rex

Current focus:
- restore production latency and uptime while keeping the recovered Oracle write path sustained and the runtime/catalog scoreboards coherent

24-hour movement and required pace:
- API Catalog Discovery p95 worsened from `560 ms` to `621 ms`
- trailing-24-hour mean uptime across the three core monitors fell from `99.971%` to `99.566%`
- June qualifying engineering deliverables rose from `10` to `11`
- the historical catalog-growth unblock remains closed, so the live problem is runtime health and sustained throughput, not the old hold chain

Plan and adjustments being made today:
- keep same-day UptimeRobot packages as the current latency and uptime source
- close the authenticated search/runtime blocker path under [BUY-29183](/BUY/issues/BUY-29183) -> [BUY-29190](/BUY/issues/BUY-29190)
- keep pressure on [BUY-25134](/BUY/issues/BUY-25134) so public runtime stats stop disagreeing with canonical DB truth
- sustain the recovered write path so Oracle movement is visible in the next top-line rerun

Five biggest failures of the day:
1. API p95 worsened to `621 ms`.
   Lesson learned: monitoring that shows regression must immediately drive a narrow fix.
2. Core uptime fell to `99.566%`, below target.
   Lesson learned: a healthy-looking system can still miss the executive uptime bar.
3. Oracle exact top-line growth was flat again.
   Lesson learned: infrastructure recovery is incomplete until it shows up in business metrics.
4. Runtime/public catalog stats still disagree with canonical DB.
   Lesson learned: public scoreboards cannot be allowed to drift from source truth.
5. June engineering output is still only `11 / 40`.
   Lesson learned: one more qualifying close is progress, not pace.

Current blockers:
- [BUY-29183](/BUY/issues/BUY-29183)
- [BUY-29190](/BUY/issues/BUY-29190)
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-22421](/BUY/issues/BUY-22421)

Active work in progress:
- infrastructure and runtime KPI integrity under [BUY-22685](/BUY/issues/BUY-22685)
- latency reduction and sustained write-path verification

Source of truth:
- [BUY-22685](/BUY/issues/BUY-22685)
- live UptimeRobot monitor data collected in this heartbeat
- live Paperclip June done-issue ledger filtered by the standing Rex engineering-deliverable rule

## Oracle

Current focus:
- keep the exact pinned-DB Oracle scoreboard canonical and force sustained growth rather than one-off recovery narratives

24-hour movement and required pace:
- fresh exact rerun at `2026-06-04 06:05 UTC`: `16,816,511` total products and `16,795,602` active products
- both top-line counts are `0 d/d` versus the `2026-06-03` exact package
- last confirmed exact sub-counts remain `24,935` product-backed merchants, `90` populated platforms, and `44.66%` US product-row share
- the required real-product pace is now roughly `3,079,018/day` through `2026-06-30`

Plan and adjustments being made today:
- keep `public.products` as the canonical source for product, active-product, product-backed-merchant, platform, and US-share KPIs
- keep `public.merchants` visible only as registry context
- keep the runtime-surface mismatch explicit until [BUY-25134](/BUY/issues/BUY-25134) is closed
- treat Oracle's original owner thread [BUY-22684](/BUY/issues/BUY-22684) as the completed plan/proof artifact and the live execution problem as a Rex-owned throughput/runtime lane

Five biggest failures of the day:
1. Oracle exact top-line growth was flat again.
   Lesson learned: the next-day count is the real test of recovery.
2. Real products remain only `16.8M / 100M`.
   Lesson learned: the absolute gap is still too large for a non-moving day to be acceptable.
3. Real merchants remain only `24,935 / 150,000`.
   Lesson learned: merchant growth is still materially behind target.
4. The public runtime surface still lags the exact DB by `45` rows and misreports active products.
   Lesson learned: runtime trust matters as much as private exact truth.
5. Oracle's original planning issue is done, but the execution gap moved to Rex-owned runtime work.
   Lesson learned: closing the planning artifact does not close the growth problem.

Current blockers:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-29183](/BUY/issues/BUY-29183)
- [BUY-25134](/BUY/issues/BUY-25134)

Active work in progress:
- exact pinned-DB scoreboarding
- throughput recovery and runtime reconciliation

Source of truth:
- direct pinned-DB queries on `public.products`
- direct pinned-DB query on `public.merchants`
- [BUY-22684](/BUY/issues/BUY-22684#document-plan)
- [docs/daily-ceo-report-2026-06-03.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-2026-06-03.md)

## Lyra

Current focus:
- grow distribution and integrations while keeping access-blocked exact KPIs visible and owned

24-hour movement and required pace:
- freshest defensible monthly visits count improved from `730` to `765` through the closed `2026-06-03` UTC window
- directory listings remain `2`
- live framework integrations remain `1`, with `custom` the only named framework bucket
- exact company-wide developer API keys and exact indexed pages remain blocked with same-day evidence

Plan and adjustments being made today:
- keep monthly visits on the browser-side human `$pageview` method defined after the contamination finding
- keep developer API keys blocked on [BUY-22421](/BUY/issues/BUY-22421) until real issuance or a board-readable persisted ledger exists
- keep indexed pages blocked on [BUY-24263](/BUY/issues/BUY-24263) until Search Console OAuth/service-account access or an exported coverage report exists
- continue directory and integration execution under [BUY-22687](/BUY/issues/BUY-22687)

Five biggest failures of the day:
1. Exact company-wide developer API key count is still blocked.
   Lesson learned: runtime-visible keys are not a substitute for the company KPI.
2. Exact indexed-page count is still blocked.
   Lesson learned: Search Console access is still a first-class operating dependency.
3. Directory listings are still `2 / 25`.
   Lesson learned: distribution throughput remains too low.
4. Framework integrations are still only `1 / 5`.
   Lesson learned: the telemetry-defined integration surface is still narrow.
5. Monthly visits are still only `765 / 25,000`.
   Lesson learned: cleaner telemetry still exposes a large demand gap.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22687](/BUY/issues/BUY-22687)

Active work in progress:
- directory and integration lane under [BUY-22687](/BUY/issues/BUY-22687)
- exact KPI access remediation under Rex-owned blocker paths

Source of truth:
- [BUY-22687](/BUY/issues/BUY-22687)
- live PostHog HogQL queries run in this heartbeat
- live `GET /api/companies/{companyId}/user-directory` response from this heartbeat
- [docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md)

## Reed

Current focus:
- keep June usage telemetry current while forcing the accepted search-success baseline off the floor

24-hour movement and required pace:
- June-to-date usage remains `1,429` API queries, `6` MCP tool calls, and `59` active AI agents
- all three usage KPIs are `0 d/d` versus yesterday's report snapshot
- the last accepted search-success baseline remains `0%` on canonical REST and `2.67%` on the accepted MCP harness
- roadmap Phase 1 + 2 remains at `4` banked P-items in the last confirmed accepted plan path

Plan and adjustments being made today:
- keep live June PostHog telemetry as the current usage source for the CEO report
- keep roadmap milestone status anchored to [BUY-22731](/BUY/issues/BUY-22731#document-plan) until a newer accepted revision supersedes it
- keep the accepted search-success baseline explicit until the rerun chain [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859) lands
- treat the live problem as product-quality execution first and usage growth second

Five biggest failures of the day:
1. Search success is still effectively at the floor.
   Lesson learned: the product still fails its core job at the accepted baseline.
2. API queries are flat at `1,429 / 500,000`.
   Lesson learned: usage is measurable now, but still nowhere near goal pace.
3. MCP tool calls are flat at `6 / 200,000`.
   Lesson learned: tool-call adoption remains negligible.
4. Active AI agents are flat at `59 / 100`.
   Lesson learned: usage has not yet translated into broader agent adoption.
5. Roadmap completion is still `4 / 9`.
   Lesson learned: the accepted plan still needs materially more shipped P-items.

Current blockers:
- [BUY-29852](/BUY/issues/BUY-29852)
- [BUY-29859](/BUY/issues/BUY-29859)
- [BUY-22731](/BUY/issues/BUY-22731)

Active work in progress:
- live June usage tracking
- accepted search-success rerun dependency path
- roadmap execution against the last accepted plan revision

Source of truth:
- [BUY-22731](/BUY/issues/BUY-22731)
- live PostHog HogQL queries run in this heartbeat
- [docs/daily-ceo-report-input-2026-06-02-reed.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-input-2026-06-02-reed.md)

## What Has Been Accomplished

- Renamed the execution issue to the required dated form for `2026-06-04 UTC`.
- Re-ran the canonical Oracle top-line product counts directly against `data/.catalog_db_url`.
- Re-checked the public runtime catalog stats endpoint and preserved the live `45`-row drift versus canonical DB truth.
- Refreshed Lyra's traffic, directory, framework, API-key-access, and indexed-pages-access evidence.
- Refreshed Reed's live June usage telemetry and preserved the accepted search-success baseline with the current blocker chain.
- Refreshed Rex's same-day UptimeRobot production-health package and June deliverables ledger.

## Key Things Needed To Hit June 30 Goals

- Turn Oracle from `0 d/d` into sustained multi-million-row daily growth on the canonical DB.
- Close [BUY-25134](/BUY/issues/BUY-25134) so the public runtime catalog surface matches canonical DB truth.
- Close [BUY-29183](/BUY/issues/BUY-29183) -> [BUY-29190](/BUY/issues/BUY-29190) so API p95 returns toward `<100 ms` and uptime rises back above `99.9%`.
- Provision exact indexed-pages access under [BUY-24263](/BUY/issues/BUY-24263) and exact company-wide API-key visibility under [BUY-22421](/BUY/issues/BUY-22421).
- Land the accepted Reed search-success rerun chain under [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859) and then improve the baseline materially.

## Board Blockers Summary

- [BUY-24263](/BUY/issues/BUY-24263): Rex still needs Google Search Console OAuth/service-account access or an exported coverage report attached so indexed pages can be reported exactly.
- [BUY-22421](/BUY/issues/BUY-22421): Rex still needs a board-readable secrets inventory or persisted issuance/export path so the company-wide developer API key KPI becomes exactly reportable.
- Rich review is required on this final report artifact via the `daily_ceo_report` confirmation path.

## Incidents And Execution Path

- Oracle throughput and runtime integrity: [BUY-22684](/BUY/issues/BUY-22684) -> [BUY-22685](/BUY/issues/BUY-22685) -> [BUY-29183](/BUY/issues/BUY-29183) -> [BUY-29190](/BUY/issues/BUY-29190)
- Runtime/catalog surface reconciliation: [BUY-25134](/BUY/issues/BUY-25134)
- Lyra measurement and access path: [BUY-22687](/BUY/issues/BUY-22687) -> [BUY-24263](/BUY/issues/BUY-24263) and [BUY-22421](/BUY/issues/BUY-22421)
- Reed search-success rerun path: [BUY-22731](/BUY/issues/BUY-22731) -> [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859)

## Source Inputs

- direct pinned-DB queries on `public.products` and `public.merchants` via `data/.catalog_db_url`
- live `GET https://api.buywhere.ai/v1/catalog/stats`
- live `GET https://api.buywhere.ai/health/db`
- live PostHog HogQL queries against project `415112`
- live `GET /api/companies/{companyId}/user-directory`
- live `GET /api/companies/{companyId}/secrets` access check (`403`)
- live Google Search Console access check (`401 UNAUTHENTICATED`)
- live UptimeRobot `getMonitors` package for the three core monitors
- [BUY-22684](/BUY/issues/BUY-22684)
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-22687](/BUY/issues/BUY-22687)
- [BUY-22731](/BUY/issues/BUY-22731)
