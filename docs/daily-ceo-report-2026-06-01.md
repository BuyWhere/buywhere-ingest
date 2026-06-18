# DAILY CEO REPORT — 2026-06-01

Report date: 2026-06-01 UTC
Correction timestamp: 2026-06-01T06:15:23Z
Status: final for Rich review
Issue: BUY-28397

Manual rerun note:
- Canonical Oracle catalog source for this rerun: `data/.catalog_db_url` -> `maglev.proxy.rlwy.net:31310/railway?sslmode=require`.
- I did not use the harness `DATABASE_URL`.
- Fresh exact `public.products` counts at `2026-06-01 06:15:23 UTC`: `16,816,466` total products, `16,795,557` active products, `24,932` distinct merchant ids referenced by products, `89` populated platforms, `7,509,743` US-tagged product rows.
- Fresh exact `public.merchants` count at `2026-06-01 06:16 UTC`: `68,384` merchant registry rows. This is not the same KPI as product-backed real merchants.
- `GET https://api.buywhere.ai/v1/catalog/stats` timed out from this runner during this heartbeat, so no same-heartbeat runtime parity statement is included beyond the last confirmed report.

## Executive Summary

- Oracle's exact product totals did not move from the `2026-05-31` manual override: the pinned maglev catalog still returns `16,816,466` total products and `16,795,557` active products. The June 30 product gap therefore remains `83,183,534`, or roughly `2,772,784/day` over the remaining `30` calendar days through `2026-06-30`.
- The biggest measurable change is definitional correction, not growth: the canonical product-backed merchant KPI on `public.products` is `24,932`, while `68,384` is the broader `public.merchants` registry row count. Yesterday's report carried the broader registry number in the merchant KPI slot; today's rerun corrects that.
- Oracle's exact US product-row share is materially better than the stale prior package: `7,509,743 / 16,816,466 = 44.66%`, leaving only `5.34 pp` to the June 30 target. Platform count is now `89`, which is `54` above the `35` target.
- The largest remaining June 30 failures are now Reed search quality at `0%`, Reed usage scale (`348` API queries and `81` MCP tool calls MTD on the accepted canonical package), Lyra's still-blocked exact developer-key and indexed-page KPIs, and Rex's `613 ms` API p95 miss.
- The most important live blocker paths are [BUY-27422](/BUY/issues/BUY-27422) -> [BUY-27418](/BUY/issues/BUY-27418) -> [BUY-24446](/BUY/issues/BUY-24446) -> [BUY-24284](/BUY/issues/BUY-24284) for Reed search recovery, [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263) for Lyra KPI access, and [BUY-22720](/BUY/issues/BUY-22720) -> [BUY-25134](/BUY/issues/BUY-25134) for Oracle runtime-scoreboard integrity.

## Daily Failure Summary

1. **Oracle's exact product count is flat day over day.**
   Lesson learned: denominator correction is useful, but it is not throughput.
2. **The merchant KPI definition was mixed yesterday.**
   Lesson learned: executive reports must distinguish product-backed merchants from registry rows explicitly, or the gap-to-target becomes meaningless.
3. **Reed search success is still `0%`.**
   Lesson learned: no adoption or roadmap narrative matters while the canonical product-quality KPI remains at the floor.
4. **Lyra still lacks exact developer-key and indexed-page counts.**
   Lesson learned: blocked instrumentation and access work are still first-class growth failures.
5. **Rex still has no fresher accepted latency package, and the last confirmed API p95 is `613 ms`.**
   Lesson learned: uptime without latency discipline still fails the June 30 engineering bar.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---:|---:|---:|---|
| Products found / runtime surface | `16,816,466` exact from pinned maglev `public.products` at `2026-06-01T06:15:23Z`; `0 d/d` versus the `2026-05-31` manual override | 100,000,000 | 83,183,534 short | Growth path still owned under [BUY-22685](/BUY/issues/BUY-22685) |
| Products index | `16,816,466` exact total products and `16,795,557` exact active products from pinned maglev; `0 d/d` on both top-line counts | 100,000,000 | 83,183,534 short on total products | [BUY-22685](/BUY/issues/BUY-22685) |
| Real merchants | `24,932` exact distinct `merchant_id` values referenced by `public.products`; corrected definition replaces the broader `68,384` registry-row count | 150,000 | 125,068 short | Merchant KPI definition corrected; runtime/reporting integrity still tracked under [BUY-25134](/BUY/issues/BUY-25134) |
| US coverage | `44.66%` exact product-row share from pinned maglev (`7,509,743 / 16,816,466`); prior packaged `5.90%` value was stale and materially understated | 50% | 5.34 pp short | Remaining US-footprint gap, not a source-path blocker |
| Platforms | `89` exact populated platform values from `public.products`; `+2` versus the last confirmed `87` package | 35 | 54 above target | No blocker on count |
| Developer API keys | Blocked; exact count still unavailable because persisted key issuance is not live end-to-end | 1,000 | Exact count blocked | [BUY-22421](/BUY/issues/BUY-22421) |
| Indexed pages | Blocked; exact indexed-page count still requires Search Console access or exported coverage data | 50,000 | Exact count blocked | [BUY-24263](/BUY/issues/BUY-24263) |
| Monthly visits | `483` safe browser-side human pageviews through the closed `2026-05-29` UTC window; `0 d/d` because no newer validated package is published | 25,000 | 24,517 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Directory listings | `2`; `0 d/d` | 25 | 23 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Framework integrations | `0`; `0 d/d` | 5 | 5 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Search success | `0%` canonical; `0 pp d/d` | 85% | 85 pp short | [BUY-27422](/BUY/issues/BUY-27422) -> [BUY-27418](/BUY/issues/BUY-27418) -> [BUY-24446](/BUY/issues/BUY-24446) -> [BUY-24284](/BUY/issues/BUY-24284) |
| API queries / month | `348` canonical PostHog MTD from completed [BUY-26393](/BUY/issues/BUY-26393); `0 d/d` because no newer accepted package is linked in this path | 500,000 | 499,652 short | [BUY-22731](/BUY/issues/BUY-22731) |
| MCP tool calls / month | `81` canonical PostHog MTD from completed [BUY-26393](/BUY/issues/BUY-26393); `0 d/d` because no newer accepted package is linked in this path | 200,000 | 199,919 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Active AI agents / month | `5` canonical PostHog MTD from completed [BUY-26393](/BUY/issues/BUY-26393); prior-day delta unavailable from a newer accepted package | 100 | 95 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Roadmap Phase 1 + 2 | `4` banked P-items last confirmed; `0 d/d` in the last confirmed plan/report path | >=9 of 14 | 5 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| API p95 latency | `613 ms` last confirmed probe; blocked for freshness because no newer accepted same-day latency artifact is linked in this path | <100 ms | 513 ms above target | [BUY-22685](/BUY/issues/BUY-22685) |
| Engineering deliverables | `0` exact in the June window so far; `0 d/d` at the start of month | 40 / month | 40 short | [BUY-24542](/BUY/issues/BUY-24542#document-june_engineering_deliverables_count) |
| Catalog-growth unblock | `No`; `0 d/d` | Yes | Not complete | [BUY-22685](/BUY/issues/BUY-22685) |
| Core uptime | `99.985%` last confirmed; `0 d/d` in the current report path | >99.9% | On target | None |

## Vera

Current focus:
- publish the corrected 2026-06-01 CEO report with an exact same-day Oracle rerun, explicit merchant-definition separation, and the required Rich review path

24-hour movement and required pace:
- the exact Oracle rerun succeeded via `data/.catalog_db_url` on maglev rather than the harness DB
- total products remain `16,816,466` and active products remain `16,795,557`, so the required average pace is still about `2,772,784/day`
- the merchant KPI was corrected from the broader `68,384` registry-row count to `24,932` product-backed merchant ids
- US coverage improved from the stale packaged `5.90%` figure to an exact same-day `44.66%`

Plan and adjustments being made today:
- keep the pinned maglev DB path as the canonical Oracle scoreboarding source for this routine
- separate `public.products` merchant ids from `public.merchants` registry rows in all future CEO reports
- keep the Reed and Lyra lanes on their accepted canonical sources until fresher accepted packages exist
- route the finished report to [@Rich](user://MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6) through the issue document confirmation path

Five biggest failures of the day:
1. Oracle product growth is still flat.
   Lesson learned: exact measurement does not compensate for missing throughput.
2. Yesterday's merchant KPI slot used the wrong denominator.
   Lesson learned: executive scoreboards need definition discipline, not just exact SQL.
3. Reed search success is still `0%`.
   Lesson learned: the product remains broken at its core promise.
4. Lyra still lacks exact key/indexed-page counts.
   Lesson learned: blocked measurement work is still delivery work.
5. Rex still has not published a fresher accepted latency package.
   Lesson learned: stale operational metrics degrade executive decision quality.

Current blockers:
- [BUY-27422](/BUY/issues/BUY-27422)
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22720](/BUY/issues/BUY-22720)

Active work in progress:
- final report publication to the `daily_ceo_report` issue document
- Rich review routing and confirmation interaction

Source of truth:
- this report
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)
- exact pinned-DB queries on `public.products` and `public.merchants`
- [BUY-24539](/BUY/issues/BUY-24539)
- [BUY-24540](/BUY/issues/BUY-24540)
- [BUY-24541](/BUY/issues/BUY-24541)

## Rex

Current focus:
- keep uptime above target, reduce API latency, and close the runtime/reporting integrity gaps that still distort executive scoreboarding

24-hour movement and required pace:
- the DB-path blocker is resolved, so the CEO routine can now query the exact Oracle source directly
- API p95 remains `613 ms` on the last accepted package, with no newer accepted same-day artifact linked into this path
- core uptime remains `99.985%`, still above target
- the runtime public stats endpoint did not return within this runner's timeout, so public-surface parity was not re-verified in this heartbeat

Plan and adjustments being made today:
- keep Oracle scoreboarding on the pinned DB path until the public runtime surface is reliably exact and fast
- finish [BUY-22720](/BUY/issues/BUY-22720) and [BUY-25134](/BUY/issues/BUY-25134) so runtime scoreboarding stops drifting by definition or availability
- publish a fresher accepted latency package before the next report cycle
- continue KPI access remediation for Lyra's blocked lanes

Five biggest failures of the day:
1. API p95 is still `613 ms`.
   Lesson learned: being up is not the same as being fast enough.
2. No fresher accepted latency artifact was available.
   Lesson learned: operational metrics need a durable daily packaging path.
3. The public stats runtime timed out from this runner.
   Lesson learned: executive-visible surfaces also need availability expectations.
4. Oracle growth is still flat.
   Lesson learned: resolved infrastructure prerequisites have not yet translated into business throughput.
5. Lyra KPI access blockers remain open.
   Lesson learned: platform owners still own measurement enablement, not just runtime health.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-22720](/BUY/issues/BUY-22720)
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-24263](/BUY/issues/BUY-24263)

Active work in progress:
- infrastructure and runtime KPI integrity under [BUY-22685](/BUY/issues/BUY-22685)
- public-scoreboard integrity and latency packaging

Source of truth:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-22720](/BUY/issues/BUY-22720)
- [BUY-24542](/BUY/issues/BUY-24542#document-june_engineering_deliverables_count)

## Oracle

Current focus:
- keep the exact pinned-DB Oracle scoreboard canonical, restore growth, and stop mixing merchant definitions in executive reporting

24-hour movement and required pace:
- exact pinned maglev rerun at `2026-06-01 06:15:23 UTC`: `16,816,466` total products and `16,795,557` active products
- those top-line product counts are `0 d/d` versus the `2026-05-31` manual override, so there is still no measurable product growth in the current executive path
- the exact product-backed merchant KPI is `24,932`, while the broader `public.merchants` registry table contains `68,384` rows
- exact US product-row share is `44.66%`, leaving only `5.34 pp` to target, and exact populated platform count is `89`

Plan and adjustments being made today:
- keep `public.products` as the canonical source for product-backed merchant and platform KPIs
- keep `public.merchants` visible only as a separate registry-size context number, not as the June 30 merchant KPI
- continue tying runtime-scoreboard integrity to [BUY-25134](/BUY/issues/BUY-25134) and [BUY-22720](/BUY/issues/BUY-22720)
- force the zero-growth story to remain explicit until throughput resumes

Five biggest failures of the day:
1. Oracle added `0` top-line products day over day in the executive path.
   Lesson learned: the growth engine is still not producing visible progress.
2. Oracle is still only `16,816,466 / 100,000,000` products.
   Lesson learned: the product gap remains too large for narrative progress to matter.
3. Product-backed merchants are only `24,932 / 150,000`.
   Lesson learned: the merchant target is farther away than yesterday's mixed definition suggested.
4. Runtime parity could not be re-verified because the public endpoint timed out from this runner.
   Lesson learned: exact DB truth still needs a reliable public serving path.
5. Merchant definitions had drifted across surfaces.
   Lesson learned: product-backed and registry-row counts must never share one KPI slot.

Current blockers:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-22720](/BUY/issues/BUY-22720)

Active work in progress:
- exact pinned-DB scoreboarding
- runtime-surface integrity and throughput recovery

Source of truth:
- direct pinned-DB queries on `public.products`
- direct pinned-DB query on `public.merchants`
- [BUY-22684](/BUY/issues/BUY-22684#document-plan)
- [BUY-25134](/BUY/issues/BUY-25134)

## Lyra

Current focus:
- grow distribution and integrations while keeping the human-web KPI honest and exact-key/indexed-page blockers visible

24-hour movement and required pace:
- the last defensible visits count remains `483` safe browser-side human pageviews through the closed `2026-05-29` UTC window
- directory listings remain `2`, leaving `23` still needed
- integrations remain `0`, leaving all `5` still needed
- developer API keys and indexed pages remain blocked exact metrics rather than stale proxies

Plan and adjustments being made today:
- keep monthly visits on the bounded browser-only query defined by completed [BUY-27385](/BUY/issues/BUY-27385)
- keep developer API keys blocked on [BUY-22421](/BUY/issues/BUY-22421) until persisted issuance is live
- keep indexed pages blocked on [BUY-24263](/BUY/issues/BUY-24263) until Search Console access or exported coverage data exists
- continue directory and integration execution under [BUY-22687](/BUY/issues/BUY-22687)

Five biggest failures of the day:
1. Lyra still cannot claim a fresher validated monthly-visits package.
   Lesson learned: one contamination audit is not a daily reporting feed.
2. Directory listings are still `2 / 25`.
   Lesson learned: distribution throughput remains too low.
3. Integrations are still `0 / 5`.
   Lesson learned: integration execution remains stalled.
4. Developer API key count is still blocked.
   Lesson learned: product growth claims need a real issuance ledger.
5. Indexed-page count is still blocked.
   Lesson learned: external-access dependencies need explicit operating ownership.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22687](/BUY/issues/BUY-22687)

Active work in progress:
- directory and integration lane under [BUY-22687](/BUY/issues/BUY-22687)
- browser-only monthly-visits KPI path from [BUY-27385](/BUY/issues/BUY-27385)

Source of truth:
- [BUY-22687](/BUY/issues/BUY-22687)
- [BUY-24541](/BUY/issues/BUY-24541)
- [docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md)

## Reed

Current focus:
- repair search quality, unblock the runtime chain, and keep usage/adoption reporting anchored to the accepted canonical PostHog reconciliation

24-hour movement and required pace:
- canonical search success remains `0%`
- canonical usage still carries `348` API queries, `81` MCP tool calls, and `5` active AI agents from completed [BUY-26393](/BUY/issues/BUY-26393)
- `BUY-22731` remains blocked by [BUY-24284](/BUY/issues/BUY-24284), which is still blocked by [BUY-24446](/BUY/issues/BUY-24446)
- the deepest active blocker in the current runtime chain remains [BUY-27422](/BUY/issues/BUY-27422)

Plan and adjustments being made today:
- keep the incident chain explicit in executive reporting: [BUY-27422](/BUY/issues/BUY-27422) -> [BUY-27418](/BUY/issues/BUY-27418) -> [BUY-24446](/BUY/issues/BUY-24446) -> [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-22731](/BUY/issues/BUY-22731)
- keep usage/adoption metrics on the accepted [BUY-26393](/BUY/issues/BUY-26393) package until a newer accepted source is published
- keep roadmap milestone status anchored to [BUY-22731](/BUY/issues/BUY-22731#document-plan)
- avoid substituting softer proxies for the canonical search-success KPI

Five biggest failures of the day:
1. Search success is still `0%`.
   Lesson learned: the product is still failing at its core job.
2. API queries remain `348 / 500,000`.
   Lesson learned: adoption remains negligible.
3. MCP tool calls remain `81 / 200,000`.
   Lesson learned: telemetry existence is not usage success.
4. Monthly active AI agents remain only `5 / 100`.
   Lesson learned: the prior proxy optimism is gone; demand is still weak.
5. The runtime recovery chain is still blocked at [BUY-27422](/BUY/issues/BUY-27422).
   Lesson learned: unresolved platform work is still the gating product blocker.

Current blockers:
- [BUY-27422](/BUY/issues/BUY-27422)
- [BUY-27418](/BUY/issues/BUY-27418)
- [BUY-24446](/BUY/issues/BUY-24446)
- [BUY-24284](/BUY/issues/BUY-24284)
- [BUY-22731](/BUY/issues/BUY-22731)

Active work in progress:
- search incident and runtime reconciliation chain
- canonical usage/adoption reporting via [BUY-26393](/BUY/issues/BUY-26393)

Source of truth:
- [BUY-22731](/BUY/issues/BUY-22731#document-plan)
- [BUY-26393](/BUY/issues/BUY-26393)
- [BUY-24284](/BUY/issues/BUY-24284)
- [BUY-24446](/BUY/issues/BUY-24446)
- [BUY-27418](/BUY/issues/BUY-27418)

## What Has Been Accomplished

- Restored the mandated Oracle DB path into the managed CEO-report checkout through completed [BUY-28404](/BUY/issues/BUY-28404).
- Re-ran the exact Oracle scoreboard against the pinned maglev catalog DB without touching the harness `DATABASE_URL`.
- Corrected the merchant KPI definition by separating product-backed merchant ids (`24,932`) from broader `public.merchants` registry rows (`68,384`).
- Recomputed exact US coverage (`44.66%`) and platform count (`89`) from the same-day canonical source.

## Key Things Needed To Hit June 30 Goals

- Resume visible Oracle product growth; exact counts are now clean, but throughput is still flat.
- Close [BUY-22720](/BUY/issues/BUY-22720) and [BUY-25134](/BUY/issues/BUY-25134) so runtime Oracle scoreboarding is exact, available, and definitionally aligned.
- Resolve [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263) so Lyra can carry exact KPI values instead of blocked placeholders.
- Unblock [BUY-27422](/BUY/issues/BUY-27422) and its downstream Reed chain so search success can move off `0%`.
- Publish a fresher accepted Rex latency artifact and daily June deliverables count.

## Board Blockers Summary

- Reed product blocker: [BUY-27422](/BUY/issues/BUY-27422) is the deepest active blocker in the search-recovery chain.
- Lyra KPI blockers: [BUY-22421](/BUY/issues/BUY-22421) for developer API keys and [BUY-24263](/BUY/issues/BUY-24263) for indexed pages remain open.
- Oracle runtime-scoreboard blocker: [BUY-22720](/BUY/issues/BUY-22720) still feeds [BUY-25134](/BUY/issues/BUY-25134), so exact DB truth is not yet mirrored by a trusted public-serving path.
- Rex engineering blocker: no fresher accepted latency artifact exists beyond the `613 ms` package currently carried here.

## Incidents And Execution Path

- Oracle reporting path: [BUY-28397](/BUY/issues/BUY-28397) -> exact pinned-DB rerun via `data/.catalog_db_url`
- Oracle runtime-scoreboard path: [BUY-22720](/BUY/issues/BUY-22720) -> [BUY-25134](/BUY/issues/BUY-25134)
- Lyra measurement path: [BUY-22421](/BUY/issues/BUY-22421) -> [BUY-22687](/BUY/issues/BUY-22687) and [BUY-24263](/BUY/issues/BUY-24263) -> [BUY-22687](/BUY/issues/BUY-22687)
- Reed incident path: [BUY-27422](/BUY/issues/BUY-27422) -> [BUY-27418](/BUY/issues/BUY-27418) -> [BUY-24446](/BUY/issues/BUY-24446) -> [BUY-24284](/BUY/issues/BUY-24284) -> [BUY-22731](/BUY/issues/BUY-22731)
- Rex execution path: [BUY-22421](/BUY/issues/BUY-22421) and [BUY-22720](/BUY/issues/BUY-22720) -> [BUY-22685](/BUY/issues/BUY-22685)

## Source Inputs

- exact `public.products` query at `2026-06-01 06:15:23 UTC` via pinned `data/.catalog_db_url`
- exact `public.merchants` query at `2026-06-01 06:16 UTC` via pinned `data/.catalog_db_url`
- [docs/daily-ceo-report-2026-05-31.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-2026-05-31.md)
- [docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md)
- [BUY-26393](/BUY/issues/BUY-26393)
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-22684](/BUY/issues/BUY-22684)
- [BUY-22687](/BUY/issues/BUY-22687)
- [BUY-22731](/BUY/issues/BUY-22731)
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-22720](/BUY/issues/BUY-22720)
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-24284](/BUY/issues/BUY-24284)
- [BUY-24446](/BUY/issues/BUY-24446)
- [BUY-27418](/BUY/issues/BUY-27418)
- completed [BUY-28404](/BUY/issues/BUY-28404)
