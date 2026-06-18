# DAILY CEO REPORT — 2026-05-31

Report date: 2026-05-31 UTC
Status: final for Rich review
Issue: BUY-27896

Manual rerun note:
- `2026-05-31T14:51:49Z` manual override supersedes the earlier Oracle catalog figures in this report.
- Canonical Oracle catalog source for this rerun: `data/.catalog_db_url` -> maglev.
- Fresh exact counts used below: `16,816,466` total products, `16,795,557` active products, `68,384` merchants, `87` active platforms.
- Public `GET /v1/catalog/stats` now matches maglev for total and active products (`16,816,466` / `16,795,557`) with `meta.source = public.products`, but still reports only `24,932` merchants, so merchant parity is still unresolved.

## Executive Summary

- The most important measurable move is this correction itself: Oracle's canonical catalog is `16,816,466` total products and `16,795,557` active products on maglev, not `2,767,644` on roundhouse. That lowers the remaining product gap to `83,183,534` and the required average pace to `2,772,784/day` over the remaining `30` days through `2026-06-30`.
- Oracle's product denominator is now reconciled across the manual maglev query and the public endpoint for products and active products. The remaining same-day runtime mismatch is merchants: maglev reports `68,384`, while the public endpoint still reports `24,932`, a `43,452` merchant gap.
- Lyra still does not have a fresh post-fix monthly-visits package. The last defensible bounded metric remains `483` browser-side human `$pageview` events through the closed `2026-05-29` UTC window; the contamination analysis itself is complete in [BUY-27385](/BUY/issues/BUY-27385), but a newer closed-window validation package is not yet published.
- Reed's headline product KPI remains a complete failure: canonical search success is still `0%`, and the completed [BUY-26393](/BUY/issues/BUY-26393) reconciliation now fixes the canonical May usage baseline at `348` API queries MTD, `81` MCP tool calls MTD, and only `5` monthly active AI agents.
- The most important live blocker paths are now [BUY-25134](/BUY/issues/BUY-25134) -> [BUY-22720](/BUY/issues/BUY-22720) for Oracle runtime parity, [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446) for Reed search quality, and Lyra's still-open exact KPI access issues [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263).

## Daily Failure Summary

1. **Oracle's source-of-truth catalog added `0` active products across the closed day.**
   Lesson learned: small prior-day movement was not durable recovery; the growth engine is still effectively stalled.
2. **Oracle reporting still exposes an unresolved merchant denominator mismatch even after the product-count correction.**
   Lesson learned: fixing the product denominator is not enough if downstream report consumers can still read a different merchant total from the public endpoint.
3. **Lyra's monthly visits KPI remains contaminated.**
   Lesson learned: server-side pageview volume is not a business KPI until bot, monitor, and proxy traffic are excluded reliably.
4. **Reed search quality is still pinned at `0%`.**
   Lesson learned: adoption or traffic proxies do not matter while the canonical success metric remains at the floor.
5. **Reed usage scale remains near zero even after the canonical source was fixed.**
   Lesson learned: telemetry reconciliation does not solve the demand problem; it only removes excuses.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---:|---:|---:|---|
| Products found / runtime surface | `16,816,466` exact at `2026-05-31T14:51:49Z`; public endpoint now matches maglev for products with `meta.source = public.products` | 100,000,000 | 83,183,534 short | Product denominator corrected; growth path still owned under [BUY-22685](/BUY/issues/BUY-22685) |
| Products index | `16,816,466` exact maglev total products; `16,795,557` exact active products from the manual override rerun | 100,000,000 | 83,183,534 short on total products | [BUY-22685](/BUY/issues/BUY-22685) |
| Real merchants | `68,384` exact maglev merchants; public endpoint still reports only `24,932`, so runtime merchant parity is unresolved | 150,000 | 81,616 short | Merchant-serving parity still needs structural report/runtime alignment |
| US coverage | Last confirmed exact product-row share from the prior Oracle package: `5.90%`; this field was not recomputed in the manual catalog override rerun | 50% | 44.10 pp short on the last confirmed package | Overall ingestion and US-footprint gap |
| Platforms | `87` exact active platforms from the manual override rerun | 35 | 52 above target | No blocker on count; overall Oracle growth path still blocked |
| Developer API keys | Blocked; exact count still unavailable because persisted key issuance is not live end-to-end | 1,000 | Exact count blocked | [BUY-22421](/BUY/issues/BUY-22421) |
| Indexed pages | Blocked; exact indexed-page count still requires Search Console access or exported coverage data | 50,000 | Exact count blocked | [BUY-24263](/BUY/issues/BUY-24263) |
| Monthly visits | `483` safe browser-side human pageviews through the closed `2026-05-29` UTC window; temporary canonical path established in completed [BUY-27385](/BUY/issues/BUY-27385), but no newer closed-window validation package is published | 25,000 | 24,517 short on the safe browser-side path | [BUY-22687](/BUY/issues/BUY-22687) |
| Directory listings | `2`; `0 d/d` | 25 | 23 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Framework integrations | `0`; `0 d/d` | 5 | 5 short | [BUY-22687](/BUY/issues/BUY-22687) |
| API queries / month | `348` canonical PostHog MTD from completed [BUY-26393](/BUY/issues/BUY-26393); `+29` versus the last confirmed `319` package | 500,000 | 499,652 short | [BUY-22731](/BUY/issues/BUY-22731) |
| MCP tool calls / month | `81` canonical PostHog MTD from completed [BUY-26393](/BUY/issues/BUY-26393); `+59` versus the last confirmed `22` package | 200,000 | 199,919 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Search success | `0%` canonical; `0 pp d/d` | 85% | 85 pp short | [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446) |
| Roadmap Phase 1 + 2 | `4` banked P-items last confirmed; `0 d/d` in the last confirmed plan/report path | >=9 of 14 | 5 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| Active AI agents / month | `5` canonical PostHog MTD from completed [BUY-26393](/BUY/issues/BUY-26393); prior-day delta unavailable from a newer same-day package | 100 | 95 short | [BUY-22731](/BUY/issues/BUY-22731) |
| API p95 latency | `613 ms` last confirmed probe; no fresh same-day latency artifact was published in this path | <100 ms | 513 ms above target | [BUY-22685](/BUY/issues/BUY-22685) |
| Engineering deliverables | `0` exact in the June window; June has not opened yet, so the target month is still ahead | 40 / month | 40 short once June opens | [BUY-24542](/BUY/issues/BUY-24542#document-june_engineering_deliverables_count) |
| Catalog-growth unblock | `No`; `0 d/d` | Yes | Not complete | [BUY-22739](/BUY/issues/BUY-22739) -> [BUY-24283](/BUY/issues/BUY-24283) |
| Core uptime | `99.985%` last confirmed; `0 d/d` in the current report path | >99.9% | On target | None |

## Vera

Current focus:
- publish a dated CEO report that surfaces today's harder Oracle truth, keeps disputed metrics explicitly labeled, and routes the final report directly to Rich for confirmation

24-hour movement and required pace:
- Oracle's corrected source-of-truth catalog is `16,816,466` total products and `16,795,557` active products, with required total-product pace now `2,772,784/day`
- the exact Oracle product count now matches the public endpoint for products, while merchants remain split between `68,384` on maglev and `24,932` on the public endpoint
- Lyra's last defensible monthly-visits figure remains `483` safe browser pageviews through the closed `2026-05-29` UTC window
- Reed's canonical search-success KPI remains `0%`, and the completed reconciliation path now fixes canonical May usage at `348` API queries, `81` MCP tool calls, and `5` active AI agents

Plan and adjustments being made today:
- treat `data/.catalog_db_url` -> maglev as the canonical Oracle scoreboard for manual reporting until the routine-level reader fix lands
- keep the Lyra visits KPI on the browser-only bounded query defined by completed [BUY-27385](/BUY/issues/BUY-27385) until a newer closed-window validation package is published
- use the completed [BUY-26393](/BUY/issues/BUY-26393) PostHog reconciliation as the canonical Reed usage source going forward
- route the finished report to [@Rich](user://MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6) through the issue document confirmation path

Five biggest failures of the day:
1. I am still publishing a report into a system with unresolved Oracle denominator drift.
   Lesson learned: the report must call out system ambiguity directly instead of smoothing it over.
2. Oracle's closed-day growth reverted to zero.
   Lesson learned: one small recovery day does not prove the engine is healthy.
3. Lyra still lacks a fresh post-fix visits package.
   Lesson learned: a one-time contamination analysis is not the same thing as a daily reporting feed.
4. Reed's canonical monthly active AI-agent count is only `5`.
   Lesson learned: fixing the source exposed how much weaker adoption really is.
5. Reed search success is still `0%`.
   Lesson learned: business narrative cannot outrun product-quality truth.

Current blockers:
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-22720](/BUY/issues/BUY-22720)
- [BUY-24446](/BUY/issues/BUY-24446)
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)

Active work in progress:
- final report publication to the `daily_ceo_report` issue document
- Rich review routing and confirmation interaction

Source of truth:
- this report
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)
- [BUY-24539](/BUY/issues/BUY-24539)
- [BUY-24540](/BUY/issues/BUY-24540)
- [BUY-24541](/BUY/issues/BUY-24541)

## Rex

Current focus:
- keep uptime above target, reduce API latency, and own the unblock plus runtime integrity path that gates Oracle and Lyra reporting

24-hour movement and required pace:
- core uptime remains `99.985%`, which is still above target
- API p95 remains `613 ms` on the last confirmed probe, with no fresh same-day artifact published into this path
- the completed Oracle recovery tasks still have not translated into measurable catalog growth, and the closed source-of-truth day showed `0` active-product growth
- the public endpoint now matches maglev exactly for products and active products, but its merchant total still diverges from the canonical maglev merchant total

Plan and adjustments being made today:
- translate the completed Oracle recovery work into measurable throughput under [BUY-22685](/BUY/issues/BUY-22685)
- carry the public endpoint as valid for products and active products, but stop treating its merchant total as canonical until the serving/report path is aligned
- publish a fresh closed-window Lyra validation package after the completed contamination analysis in [BUY-27385](/BUY/issues/BUY-27385)
- publish a fresh same-day latency artifact before the next report cycle

Five biggest failures of the day:
1. API p95 is still `613 ms` against a `<100 ms` target.
   Lesson learned: being up is not the same as being fast enough.
2. Completed Oracle recovery tasks still have not produced measurable growth.
   Lesson learned: closing task tickets is not the same thing as restoring throughput.
3. The public endpoint merchant total still does not reconcile to the canonical maglev merchant total.
   Lesson learned: exact product parity can still coexist with a broken merchant denominator.
4. No fresh closed-window Lyra visits package was published after the contamination work.
   Lesson learned: analytics remediation needs a durable daily refresh, not just one fix pass.
5. No fresh same-day latency artifact was available in this report path.
   Lesson learned: operational metrics need reproducible daily packaging.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-22720](/BUY/issues/BUY-22720)
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-24263](/BUY/issues/BUY-24263)

Active work in progress:
- infrastructure and runtime KPI integrity continue under [BUY-22685](/BUY/issues/BUY-22685)
- Oracle unblock and runtime-surface parity remain open

Source of truth:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-24542](/BUY/issues/BUY-24542#document-june_engineering_deliverables_count)
- [BUY-25133](/BUY/issues/BUY-25133)

## Oracle

Current focus:
- restore durable catalog growth, keep the exact DB-backed scoreboard current, and reconcile discovery -> index -> runtime into one executive-safe source of truth

24-hour movement and required pace:
- exact live DB reporting in the manual override rerun is `16,795,557` active products and `16,816,466` total products
- the fully covered `2026-05-30` UTC day added `0` active products on the source-of-truth shortfall path even after completed recovery tasks [BUY-22739](/BUY/issues/BUY-22739) and [BUY-24283](/BUY/issues/BUY-24283)
- exact merchant scale is `68,384` on maglev, while the public endpoint still reports `24,932`; the last confirmed US product-row share from the prior Oracle package remains `5.90%`
- the business still needs `83,183,534` more products and roughly `2.77M/day` over the remaining `30` days

Plan and adjustments being made today:
- keep `data/.catalog_db_url` -> maglev as the canonical exact scoreboard for manual CEO reporting
- keep the public endpoint visible as an exact mirror for products and active products, but explicitly non-canonical for merchants until that split is resolved
- force a throughput explanation under [BUY-22685](/BUY/issues/BUY-22685) now that [BUY-22739](/BUY/issues/BUY-22739) and [BUY-24283](/BUY/issues/BUY-24283) are already done
- keep today's shortfall artifact linked in the report so the closed-day zero-growth miss is visible

Five biggest failures of the day:
1. Oracle added `0` active products across the closed day even after the prior recovery tasks were marked done.
   Lesson learned: the growth engine is still failing at the only pace that matters.
2. Oracle remains only `16,816,466 / 100,000,000` products against the June 30 goal.
   Lesson learned: the gap is too large for incrementalism to read as progress.
3. Merchant scale remains only `68,384 / 150,000`, and the public endpoint still understates it at `24,932`.
   Lesson learned: merchant growth is also materially behind path.
4. US coverage remains `5.90%`.
   Lesson learned: catalog breadth is still far too narrow.
5. Oracle still lacks one reconciled merchant denominator across maglev and the public endpoint.
   Lesson learned: even after a product-count fix, partial runtime drift still hides operational truth unless called out directly.

Current blockers:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-22720](/BUY/issues/BUY-22720)

Active work in progress:
- daily Oracle shortfall reporting remains active
- runtime-surface reconciliation remains active

Source of truth:
- [docs/daily-product-target-shortfall-2026-05-31.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-05-31.md)
- [docs/buy-27394-runtime-surface-row-family-ledger-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27394-runtime-surface-row-family-ledger-2026-05-30.md)
- [BUY-24539](/BUY/issues/BUY-24539)
- direct Postgres queries on `public.products`
- live `GET https://api.buywhere.ai/v1/catalog/stats`

## Lyra

Current focus:
- grow distribution and integrations while replacing the contaminated raw pageview stream with a trustworthy human-web visits KPI

24-hour movement and required pace:
- the last defensible bounded visits count remains `483` browser-side human pageviews through the closed `2026-05-29` UTC window
- the broader stream still contains the previously measured `34,713` contaminated `pageview_server` rows from the last closed validation window
- directory listings remain `2`, which leaves `23` still needed
- integrations remain `0`, which leaves all `5` still needed

Plan and adjustments being made today:
- keep Lyra monthly visits on the bounded browser-only query defined by completed [BUY-27385](/BUY/issues/BUY-27385)
- keep indexed pages blocked on [BUY-24263](/BUY/issues/BUY-24263) until Search Console access or an exported coverage report is available
- keep developer API keys blocked on [BUY-22421](/BUY/issues/BUY-22421) until persisted issuance is live
- continue directory and integration execution under [BUY-22687](/BUY/issues/BUY-22687)

Five biggest failures of the day:
1. Lyra still cannot claim a fresh post-fix monthly-visits win.
   Lesson learned: one completed analysis does not replace a durable daily reporting feed.
2. Directory listings are still only `2 / 25`.
   Lesson learned: distribution throughput remains weak.
3. Integrations are still `0 / 5`.
   Lesson learned: zero integrations is still a real product-distribution miss.
4. Indexed-page reporting is still blocked on outside access.
   Lesson learned: critical marketing KPIs need durable credentialed access, not ad hoc exports.
5. Developer API keys still do not have a reliable persisted count path.
   Lesson learned: growth instrumentation must exist before scale claims are credible.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22703](/BUY/issues/BUY-22703)
- [BUY-22704](/BUY/issues/BUY-22704)

Active work in progress:
- directory inventory and submission path under [BUY-22687](/BUY/issues/BUY-22687)
- waiting on a newer closed-window validation package after the completed [BUY-27385](/BUY/issues/BUY-27385) contamination analysis

Source of truth:
- [BUY-24541](/BUY/issues/BUY-24541)
- [docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md)
- [BUY-22687](/BUY/issues/BUY-22687)

## Reed

Current focus:
- repair search quality, restore one canonical same-day usage source, and keep roadmap/adoption reporting honest while the core product KPI is still failing

24-hour movement and required pace:
- canonical search success remains `0%`
- canonical PostHog reporting now shows only `348` API queries MTD and `81` MCP tool calls MTD after completed [BUY-26393](/BUY/issues/BUY-26393)
- canonical monthly active AI agents are only `5`, not the previously carried `184` runtime proxy
- the core execution truth remains that search quality, not top-of-funnel traffic, is the gating product failure

Plan and adjustments being made today:
- keep the search-quality blocker chain explicit: [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446)
- use the completed [BUY-26393](/BUY/issues/BUY-26393) HogQL path as the canonical source for API queries, MCP tool calls, and monthly active AI agents
- keep roadmap milestone status anchored to [BUY-22731](/BUY/issues/BUY-22731#document-plan)
- avoid replacing the canonical search-success KPI with softer proxies

Five biggest failures of the day:
1. Search success is still `0%`.
   Lesson learned: the product is still failing at its primary job.
2. API queries remain negligible against target.
   Lesson learned: usage scale is still nowhere near the required business line.
3. MCP tool-call adoption remains negligible against target.
   Lesson learned: agent tooling usage has not translated into meaningful monthly volume.
4. Canonical monthly active AI agents are only `5 / 100`.
   Lesson learned: once the telemetry source was corrected, the adoption gap became materially worse than the old proxy suggested.
5. Roadmap execution still cannot offset the search-state failure.
   Lesson learned: roadmap progress does not matter if the core user journey is broken.

Current blockers:
- [BUY-24284](/BUY/issues/BUY-24284)
- [BUY-24439](/BUY/issues/BUY-24439)
- [BUY-24446](/BUY/issues/BUY-24446)

Active work in progress:
- roadmap plan remains active in [BUY-22731](/BUY/issues/BUY-22731#document-plan)
- usage-source reconciliation is complete in [BUY-26393](/BUY/issues/BUY-26393); the remaining issue is business adoption, not telemetry definition

Source of truth:
- [BUY-24540](/BUY/issues/BUY-24540)
- direct PostHog query on `api_query` and `mcp_tool_call`
- [BUY-22731](/BUY/issues/BUY-22731#document-plan)

## What Has Been Accomplished

- Renamed the execution issue to `DAILY CEO REPORT — 2026-05-31`.
- Published a dated report that reflects the closed `2026-05-30` UTC Oracle zero-growth miss rather than carrying forward the earlier partial-recovery narrative.
- Manually reran the Oracle catalog portion against maglev and corrected the canonical scoreboard to `16,816,466` total products, `16,795,557` active products, `68,384` merchants, and `87` active platforms.
- Verified that the public endpoint now matches maglev for products and active products, while still diverging on merchants (`24,932` public vs `68,384` canonical).
- Kept Lyra's visits KPI on the bounded browser-only query established by completed [BUY-27385](/BUY/issues/BUY-27385).
- Corrected Reed's canonical usage lane using completed [BUY-26393](/BUY/issues/BUY-26393): `348` API queries, `81` MCP tool calls, and `5` monthly active AI agents.

## Key Things Needed To Hit June 30 Goals

- Oracle needs a throughput explanation and measurable recovery under [BUY-22685](/BUY/issues/BUY-22685) because the active catalog still closed at `0` growth even after completed recovery tasks [BUY-22739](/BUY/issues/BUY-22739) and [BUY-24283](/BUY/issues/BUY-24283).
- Oracle now has a corrected product denominator, but still needs the merchant-serving path aligned so the public endpoint stops understating merchants by `43,452`.
- Reed needs [BUY-24446](/BUY/issues/BUY-24446) completed so search success can move off `0%`.
- Reed needs [BUY-22731](/BUY/issues/BUY-22731) to move actual usage because the canonical lane is now fixed and still only at `348 / 81 / 5`.
- Lyra needs a fresh closed-window post-fix visits package after completed [BUY-27385](/BUY/issues/BUY-27385) so monthly visits become a durable daily KPI again.
- Lyra still needs [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263) resolved so blocked KPI surfaces become exact numbers.

## Board Blockers Summary

- Merchant-serving parity remains unresolved: the public endpoint reports `24,932` merchants while canonical maglev reports `68,384`.
- [BUY-24446](/BUY/issues/BUY-24446): live search-state repair still blocks Reed's headline quality KPI.
- [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263): blocked Lyra KPI surfaces remain unresolved.

## Incidents And Execution Path

- Oracle growth path: [BUY-22684](/BUY/issues/BUY-22684) -> [BUY-22739](/BUY/issues/BUY-22739) -> [BUY-24283](/BUY/issues/BUY-24283); both follow-up recovery tasks are complete, but the growth metric is still flat
- Oracle reporting-integrity path: [BUY-24539](/BUY/issues/BUY-24539) -> [BUY-25133](/BUY/issues/BUY-25133) -> [BUY-28071](/BUY/issues/BUY-28071); product counts are corrected, but merchant parity is still unresolved on the public endpoint
- Reed incident path: [BUY-22731](/BUY/issues/BUY-22731) -> [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-24439](/BUY/issues/BUY-24439) -> [BUY-24446](/BUY/issues/BUY-24446)
- Reed reporting-integrity path: [BUY-24540](/BUY/issues/BUY-24540) -> [BUY-26393](/BUY/issues/BUY-26393); path is complete and now establishes the canonical KPI source
- Lyra measurement path: [BUY-22687](/BUY/issues/BUY-22687) -> [BUY-27385](/BUY/issues/BUY-27385); contamination analysis is complete, but a newer closed-window validation package is still needed

## Source Inputs

- [docs/daily-product-target-shortfall-2026-05-31.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-05-31.md)
- [docs/buy-27394-runtime-surface-row-family-ledger-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27394-runtime-surface-row-family-ledger-2026-05-30.md)
- [docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md)
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)
- [BUY-24539](/BUY/issues/BUY-24539)
- [BUY-24540](/BUY/issues/BUY-24540)
- [BUY-24541](/BUY/issues/BUY-24541)
- [BUY-24542](/BUY/issues/BUY-24542#document-june_engineering_deliverables_count)
- [BUY-25133](/BUY/issues/BUY-25133)
- [BUY-28071](/BUY/issues/BUY-28071)
- [BUY-26393](/BUY/issues/BUY-26393)
- [BUY-27385](/BUY/issues/BUY-27385)
- direct Postgres queries on `public.products` and `public.merchants` via `data/.catalog_db_url`
- direct PostHog queries on project `415112`
- live `GET https://api.buywhere.ai/v1/catalog/stats`
