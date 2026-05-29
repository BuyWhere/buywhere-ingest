# DAILY CEO REPORT — 2026-05-28

Report date: 2026-05-28 UTC
Status: final for Rich review
Issue: BUY-25128

## Executive Summary

- The biggest measurable move today is negative in Oracle's lane: the closed `2026-05-27` UTC day added `0` active products, which pushed the required active-product pace up to `2,860,364/day` for the remaining `34` calendar days to June 30.
- Reed's live usage telemetry was refreshed from the product API at `2026-05-28` and shows `563` API queries month-to-date, `3,921` MCP tool calls month-to-date, and `184` trailing-30-day active AI agents. Active agents are already above target; usage scale and search quality are still far behind.
- The biggest reporting failure is now source-of-truth drift in the catalog: Oracle's exact shortfall report for `2026-05-28 00:15 UTC` shows `2,747,644` active products and `2,762,711` real products, while the live public `/v1/catalog/stats` endpoint at `2026-05-28 06:07:58 UTC` still reports only `1,575,624` approximate active products from `pg_class_fallback`. This is a material operating-system failure and is now tracked in same-day follow-up [BUY-25133](/BUY/issues/BUY-25133).
- The most important live blocker chains remain unchanged: Oracle growth is still gated by [BUY-22739](/BUY/issues/BUY-22739) -> [BUY-24283](/BUY/issues/BUY-24283), and Reed's search-success recovery is still gated by [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446).

## Daily Failure Summary

1. **Oracle's catalog growth engine produced a zero-growth day.** The active catalog stayed flat at `2,747,644` through the full `2026-05-27` UTC day against a required pace of `2,778,639/day`.
   Lesson learned: missed days compound immediately at this scale; one flat day steepened the remaining required pace to `2,860,364/day`.

2. **The catalog source of truth is still internally inconsistent.** The public stats endpoint and the exact Oracle DB reports disagree materially on active-product totals.
   Lesson learned: the CEO report cannot rely on any fallback endpoint that can drift from the exact DB-backed scoreboard without explicit warning.

3. **Search success is still at the canonical floor.** Reed's KPI remains `0%` because full-text search is still broken and the basket harness cannot pass until the live search-state repair is finished.
   Lesson learned: usage growth should not be interpreted as product quality when the canonical relevance metric is still zero.

4. **Lyra still lacks exact indexed-pages and developer-key KPI truth.** Indexed pages remain blocked on Search Console access and developer key counts remain blocked on persisted `api_keys` row creation.
   Lesson learned: blocked metrics must be treated as owned execution failures, not soft data gaps.

5. **Rex's engineering lane still lacks a fresh same-day latency artifact, and the June deliverables KPI is structurally zero before the June window opens.**
   Lesson learned: KPI definitions need same-day source paths attached, especially when the target month has not started yet and the optics can be misleading.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---:|---:|---:|---|
| **ORACLE** | | | | |
| Real products | 2,762,711 | 100,000,000 | 97,237,289 short | [BUY-22739](/BUY/issues/BUY-22739) -> [BUY-24283](/BUY/issues/BUY-24283) |
| Real merchants | 15,070 last confirmed exact | 150,000 | 134,930 short | Catalog-backed exact refresh now tracked in [BUY-25133](/BUY/issues/BUY-25133) |
| US coverage | 5.87% | 50% | 44.13 pp short | Overall ingestion/growth bottleneck |
| Platforms | 47 exact active platforms | 35 | 12 above target | None on count; growth still blocked |
| **LYRA** | | | | |
| Indexed pages | Blocked | 50,000 | Exact count blocked | [BUY-24263](/BUY/issues/BUY-24263) |
| Developer API keys | Blocked | 1,000 | Exact count blocked | [BUY-22421](/BUY/issues/BUY-22421) |
| Directory listings | 2 | 25 | 23 short | Execution lag; source path on [BUY-22687](/BUY/issues/BUY-22687) |
| Framework integrations | 0 | 5 | 5 short | Execution lag; plan blocked in part by [BUY-13832](/BUY/issues/BUY-13832) |
| Monthly visits | 20,361 | 25,000 | 4,639 short | Traffic and indexing execution lag |
| **REED** | | | | |
| API queries / month | 563 | 500,000 | 499,437 short | Demand-generation and product adoption gap |
| MCP tool calls / month | 3,921 | 200,000 | 196,079 short | Demand-generation and product adoption gap |
| Search success | 0% | 85% | 85 pp short | [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446) |
| Roadmap Phase 1 + 2 | 4 banked P-items | >=9 of 14 | 5 short | Search-state delay reduces roadmap confidence |
| Active AI agents / month | 184 | 100 | 84 above target | None |
| **REX** | | | | |
| API p95 latency | 613 ms last confirmed probe | <100 ms | 513 ms above target | No fresh same-day artifact; lane tracked on [BUY-22685](/BUY/issues/BUY-22685) |
| Engineering deliverables | 0 exact in June window | 40 / month | 40 short once June opens | Counting rule artifact on [BUY-24542](/BUY/issues/BUY-24542) |
| Catalog-growth unblock | No | Yes | Not complete | [BUY-22739](/BUY/issues/BUY-22739) -> [BUY-24283](/BUY/issues/BUY-24283) |
| Core uptime | 99.985% last confirmed | >99.9% | On target | None |

## Vera

Current focus:
- publish a dated CEO report that uses live June 30 targets, refreshed Reed telemetry, the current Oracle shortfall artifact, and explicit blocker ownership instead of silent proxies
- keep the reporting operating system honest by surfacing the catalog source-of-truth conflict directly

24-hour movement and required pace:
- report operating system moved from a previous-day artifact to a same-day final report with live `2026-05-28` telemetry refreshes
- same-day owner/tooling follow-up created for the catalog-stats drift in [BUY-25133](/BUY/issues/BUY-25133)
- required daily pace remains to keep every lane explicitly tied to remaining June 30 gap math and named blockers

Plan and adjustments being made today:
- use the exact Oracle shortfall report for today's product scoreboard
- use live `GET /v1/usage/summary` values for Reed's unstable telemetry
- treat blocked Lyra KPIs as blocked, not as "data unavailable"
- route the final report directly to [@Rich](user://MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6) with a confirmation interaction on the canonical issue document

Five biggest failures of the day:
1. The public catalog stats endpoint still diverges materially from the exact Oracle DB report.
   Lesson learned: fallback stats must never be presented without a visible warning and a repair owner.
2. The Oracle merchant/source-of-truth refresh was not self-serve from this runner.
   Lesson learned: when a source path is permission- or runtime-constrained, the CEO report needs an explicit follow-up owner the same day.
3. Lyra still lacks exact KPI truth for indexed pages and keys.
   Lesson learned: blocked KPI production must be treated as part of the delivery, not externalized away from the report.
4. Rex's latency row still depends on the last confirmed probe package rather than a fresh same-day artifact.
   Lesson learned: operational KPIs need reproducible refresh paths, not just historically accepted values.
5. Reed's product-quality lane remains blocked even while usage counters are live.
   Lesson learned: instrumentation maturity can coexist with product failure; the report has to separate those clearly.

Current blockers:
- [BUY-24446](/BUY/issues/BUY-24446) still blocks Reed's search-quality recovery
- [BUY-25133](/BUY/issues/BUY-25133) now tracks the Oracle/public catalog-stats reconciliation failure for the next report cycle

Active work in progress:
- this report publication and Rich handoff
- daily reconciliation of cross-lane blocker chains

Source of truth:
- [BUY-24985](/BUY/issues/BUY-24985) shortfall artifact
- live `GET /v1/usage/summary`
- live `GET /v1/catalog/stats`

## Rex

Current focus:
- keep uptime above target, reduce latency, clear the catalog-growth unblock chain, and own the runtime/statistics surfaces that other lanes depend on

24-hour movement and required pace:
- core uptime remains `99.985%`, which is on target
- API p95 remains `613 ms` on the last confirmed probe package; to hit June 30 it still needs about `513 ms` reduction, or roughly `15.09 ms/day` over the remaining `34` days
- engineering deliverables remain `0 exact` for the June window because June has not started yet; once June opens the lane needs `40` qualifying completions across the month
- catalog-growth unblock remains `No`, which means Oracle's target path is still gated immediately rather than gradually

Plan and adjustments being made today:
- keep the platform-health KPIs visible using the last confirmed probes
- clear the runtime/source-of-truth debt called out in [BUY-25133](/BUY/issues/BUY-25133)
- continue the unblock chain under [BUY-22685](/BUY/issues/BUY-22685) and [BUY-22739](/BUY/issues/BUY-22739)

Five biggest failures of the day:
1. API p95 is still `613 ms` against a `<100 ms` target.
   Lesson learned: uptime alone does not satisfy the June 30 engineering commitment.
2. The catalog-growth unblock is still incomplete.
   Lesson learned: Oracle's product target remains an engineering dependency, not just an Oracle issue.
3. The public catalog stats endpoint still serves approximate fallback numbers that drift from exact DB-backed reporting.
   Lesson learned: shared executive metrics need runtime surfaces that are visibly canonical or visibly degraded.
4. The key-issuance path is still not a trustworthy KPI source for developer registrations.
   Lesson learned: Lyra's growth goals remain partly blocked by a core engineering path.
5. The June deliverables KPI is still at `0 exact`.
   Lesson learned: if a KPI window has not opened yet, the report has to say so explicitly rather than imply hidden progress.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421) blocks valid persisted key issuance
- [BUY-22720](/BUY/issues/BUY-22720) blocks the catalog-stats exact-counter path

Active work in progress:
- platform-health monitoring
- unblock path through [BUY-22685](/BUY/issues/BUY-22685)
- runtime/catalog reconciliation dependencies affecting [BUY-25133](/BUY/issues/BUY-25133)

Source of truth:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-24542](/BUY/issues/BUY-24542#document-june_engineering_deliverables_count)
- live `GET /v1/catalog/stats`

## Oracle

Current focus:
- restore real catalog growth, keep the product and merchant counts defensible, and fix the scoreboard drift between exact DB-backed reporting and public runtime stats

24-hour movement and required pace:
- active products added across the fully covered `2026-05-27` UTC day: `0`
- current exact counts from the shortfall report snapshot at `2026-05-28 00:15 UTC`: `2,747,644` active products and `2,762,711` real products
- remaining active products to target: `97,252,356`
- required active-product pace from `2026-05-28` forward: `2,860,364/day`
- last confirmed exact catalog-backed merchant count remains `15,070`; that still leaves `134,930` merchants to target and needs a fresh exact refresh next cycle

Plan and adjustments being made today:
- continue treating the exact DB-backed Oracle shortfall report as the authoritative product scoreboard for this report date
- keep the previously established exact active platform count at `47`
- escalate the catalog-stats/public-endpoint drift into [BUY-25133](/BUY/issues/BUY-25133) so the next report cycle has one canonical surface

Five biggest failures of the day:
1. Active-product growth for the closed day was `0`.
   Lesson learned: a single flat day is unacceptable when the required pace is already in the multi-million range.
2. The remaining required pace increased to `2,860,364/day`.
   Lesson learned: delay compounds faster than linear intuition suggests.
3. The public stats endpoint still reports only `1,575,624` approximate active products.
   Lesson learned: executive reporting cannot tolerate hidden fallback drift on the main scoreboard.
4. Exact merchant truth was not refreshed today from the canonical catalog-backed query path.
   Lesson learned: merchant count needs the same daily operational discipline as product count.
5. Ingestion is still not fully reopened.
   Lesson learned: planning math does not matter until the unblock chain lands in production.

Current blockers:
- [BUY-22739](/BUY/issues/BUY-22739) blocks lifting `INGESTION_HOLD`
- [BUY-24283](/BUY/issues/BUY-24283) remains the terminal unblock on the scrape/burn-in path
- [BUY-25133](/BUY/issues/BUY-25133) tracks the source-of-truth drift that now affects reporting confidence directly

Active work in progress:
- Oracle daily shortfall reporting is active
- historical platform-count and reconciliation evidence from [BUY-24539](/BUY/issues/BUY-24539) remains valid for the platform KPI

Source of truth:
- [docs/daily-product-target-shortfall-2026-05-28.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-05-28.md)
- [BUY-24539](/BUY/issues/BUY-24539)
- [BUY-22684](/BUY/issues/BUY-22684)

## Lyra

Current focus:
- grow directory distribution, integrations, indexed-page visibility, and real developer key registrations while making the blocked KPI truth explicit

24-hour movement and required pace:
- directory listings remain `2`; Lyra still needs `23`, or about `0.68/day`
- integrations remain `0`; Lyra still needs `5`, or about `0.15/day`
- monthly visits remain `20,361`; Lyra needs `4,639` more by month-end, or about `136/day`
- indexed pages remain blocked behind Search Console access
- developer API key truth remains blocked behind persisted key issuance

Plan and adjustments being made today:
- keep the distribution metrics visible without pretending blocked KPIs are known
- use [BUY-24263](/BUY/issues/BUY-24263) as the exact owner/action path for indexed pages
- use [BUY-22421](/BUY/issues/BUY-22421) as the exact owner/action path for developer key truth

Five biggest failures of the day:
1. Directory listings are still only `2 / 25`.
   Lesson learned: distribution has to be treated like a daily throughput problem, not a background marketing task.
2. Integrations are still `0 / 5`.
   Lesson learned: zero integrations is a hard miss, not a provisional state.
3. Indexed pages are still blocked.
   Lesson learned: visibility metrics need access-path ownership, not just downstream content work.
4. Developer key count is still blocked.
   Lesson learned: signup path correctness and KPI production are the same problem here.
5. Monthly visits remain `4,639` short.
   Lesson learned: traffic growth is happening too slowly to count as on-track.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421) blocks persisted key issuance
- [BUY-24263](/BUY/issues/BUY-24263) blocks indexed-page truth
- [BUY-22703](/BUY/issues/BUY-22703) and [BUY-22704](/BUY/issues/BUY-22704) remain on the measurement/SEO path

Active work in progress:
- directory inventory and submission path under [BUY-22687](/BUY/issues/BUY-22687)
- SEO/traffic work through [BUY-22703](/BUY/issues/BUY-22703) and [BUY-22704](/BUY/issues/BUY-22704)

Source of truth:
- [BUY-24541](/BUY/issues/BUY-24541)
- [BUY-22687](/BUY/issues/BUY-22687)

## Reed

Current focus:
- repair search relevance, keep live usage counters current, and push API/MCP adoption while the roadmap advances

24-hour movement and required pace:
- live `2026-05-28` usage summary shows `563` API queries MTD; Reed still needs `499,437`, or about `14,689/day`
- live `2026-05-28` usage summary shows `3,921` MCP tool calls MTD; Reed still needs `196,079`, or about `5,767/day`
- trailing-30-day active AI agents remain `184`, which is `84` above target
- canonical search success remains `0%`; Reed needs `85` percentage points, or about `2.50 pp/day`
- roadmap remains at `4` banked P-items and still needs `5` more to hit the minimum shipped set of `>=9`

Plan and adjustments being made today:
- use live `GET /v1/usage/summary` values instead of yesterday's telemetry snapshot
- keep search quality anchored to the canonical basket metric rather than softer proxies
- continue roadmap execution under [BUY-22731](/BUY/issues/BUY-22731#document-plan) while [BUY-24446](/BUY/issues/BUY-24446) remains blocked

Five biggest failures of the day:
1. Search success is still `0%`.
   Lesson learned: the product-quality lane is still failing even though telemetry is now mature.
2. API queries are still only `563 / 500,000`.
   Lesson learned: the product still has very little real demand.
3. MCP tool calls are still only `3,921 / 200,000`.
   Lesson learned: instrumentation success must not be confused with adoption success.
4. Roadmap execution is still only `4` banked P-items.
   Lesson learned: blocked search-state work is slowing the rest of the roadmap.
5. Today's usage summary shows `0` activity so far in the UTC day.
   Lesson learned: MTD progress exists, but daily usage is still lumpy and fragile.

Current blockers:
- [BUY-24284](/BUY/issues/BUY-24284) is the direct search-quality incident
- [BUY-24439](/BUY/issues/BUY-24439) and [BUY-24446](/BUY/issues/BUY-24446) remain on the live search-state recovery path
- [BUY-24261](/BUY/issues/BUY-24261) remains blocked on basket-based search-success completion

Active work in progress:
- usage-summary endpoint is live and producing current month-to-date counters
- roadmap plan remains active in [BUY-22731](/BUY/issues/BUY-22731#document-plan)

Source of truth:
- live `GET /v1/usage/summary`
- [BUY-24540](/BUY/issues/BUY-24540)
- [BUY-22731](/BUY/issues/BUY-22731#document-plan)

## What Has Been Accomplished

- Reed's unstable telemetry was refreshed from the live product API for `2026-05-28`, replacing stale `2026-05-27` values with current MTD counts.
- Oracle's daily shortfall artifact for `2026-05-28` is now folded into the CEO report as the primary product scoreboard.
- The catalog source-of-truth drift between exact Oracle reporting and the public stats endpoint was surfaced directly and routed into a same-day follow-up issue.
- The report remains in the approved section order with the narrow KPI table and explicit failure accounting.

## Key Things Needed To Hit June 30 Goals

- Oracle needs [BUY-22739](/BUY/issues/BUY-22739) and [BUY-24283](/BUY/issues/BUY-24283) cleared so growth resumes immediately.
- Rex needs the catalog-stats/runtime reconciliation in [BUY-25133](/BUY/issues/BUY-25133) resolved before the next report cycle.
- Reed needs the live search-state repair chain [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446) completed so the canonical `0%` search-success KPI can move.
- Lyra needs [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263) resolved so two blocked KPIs become exact numbers instead of execution blockers.

## Board Blockers Summary

- [BUY-24283](/BUY/issues/BUY-24283): Oracle ingestion recovery still terminally blocks catalog growth.
- [BUY-24446](/BUY/issues/BUY-24446): live search-state repair still blocks Reed's headline quality KPI.
- [BUY-22421](/BUY/issues/BUY-22421): persisted key issuance still blocks Lyra's developer-registration KPI.
- [BUY-24263](/BUY/issues/BUY-24263): Search Console access still blocks Lyra's indexed-pages KPI.
- [BUY-25133](/BUY/issues/BUY-25133): same-day repair issue for exact Oracle scoreboard vs public stats drift before the next CEO report.

## Incidents And Execution Path

- Oracle incident path: [BUY-22684](/BUY/issues/BUY-22684) -> [BUY-22739](/BUY/issues/BUY-22739) -> [BUY-24283](/BUY/issues/BUY-24283)
- Reed incident path: [BUY-22731](/BUY/issues/BUY-22731) -> [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446)
- Lyra measurement/key path: [BUY-22687](/BUY/issues/BUY-22687) -> [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263)
- Reporting integrity path: [BUY-25128](/BUY/issues/BUY-25128) -> [BUY-25133](/BUY/issues/BUY-25133)

## Source Inputs

- [docs/daily-product-target-shortfall-2026-05-28.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-05-28.md)
- [docs/daily-ceo-report-2026-05-27.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-2026-05-27.md)
- [BUY-24539](/BUY/issues/BUY-24539)
- [BUY-24540](/BUY/issues/BUY-24540)
- [BUY-24541](/BUY/issues/BUY-24541)
- [BUY-24542](/BUY/issues/BUY-24542#document-june_engineering_deliverables_count)
- live `GET https://api.buywhere.ai/v1/usage/summary`
- live `GET https://api.buywhere.ai/v1/catalog/stats`
