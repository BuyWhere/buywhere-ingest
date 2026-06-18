# DAILY CEO REPORT — 2026-06-05

Report date: 2026-06-05 UTC
Finalized at: 2026-06-05T06:25:00Z
Status: final for Rich review
Issue: [BUY-30830](/BUY/issues/BUY-30830)

Manual source-of-truth notes:
- Canonical Oracle catalog source for this run: `data/.catalog_db_url` -> `maglev.proxy.rlwy.net:31310/railway?sslmode=require`.
- I did not use the harness `DATABASE_URL`.
- Fresh exact pinned-DB top-line counts at `2026-06-05 06:14 UTC`: `23,521,726` total products and `23,467,460` active products. The `2.7M` control-plane-DB number is not present, which confirms the canonical URL was used.
- The public runtime surface at `2026-06-05 06:19 UTC`: `GET https://api.buywhere.ai/v1/catalog/stats` returned `23,419,232` total products and `23,419,232` active products (`pg_class_fallback`, `approximate=true`), running `102,494` rows behind the exact pinned DB and still misreporting active products as equal to total. Runtime-surface reconciliation remains tracked under [BUY-25134](/BUY/issues/BUY-25134).
- Fresh exact distinct-product-backed merchant count at `2026-06-05 06:14 UTC`: `44,008` (up from the `2026-06-03` package value of `24,935`, a `+19,073` jump driven by today's broad Shopify ingest).
- Fresh exact platform-populated count from `public.products.platform` at `2026-06-05 06:14 UTC`: `91` (was `90` yesterday).
- Fresh exact US-tagged product rows at `2026-06-05 06:14 UTC`: `7,661,634`; US coverage as a share of total products is `32.57%`, down from `44.66%` yesterday because new Shopify ingest is materially non-US.
- Fresh exact `public.merchants` registry count at `2026-06-05 06:14 UTC`: `68,384` rows (unchanged). This is context, not the June 30 real-merchants KPI.
- The exact product source of truth reconciles the older "~14M plus ~4M newly catalogued" narrative into one live total of `23,521,726` rows on the pinned maglev catalog after the `2026-06-04` ingest wave (`5,226,474` creates) plus an additional `1,095,659` creates already on the open `2026-06-05` UTC day. Runtime reconciliation remains live under [BUY-25134](/BUY/issues/BUY-25134).

## Executive Summary

- Oracle's top line moved hard. Exact pinned-DB rerun jumped to `23,521,726` total products and `23,467,460` active products, a `+6,705,215 d/d` lift on total and `+6,671,858 d/d` on active. Distinct product-backed merchants jumped from `24,935` to `44,008` (`+19,073 d/d`). Required pace to `100,000,000` active products by `2026-06-30` drops from `~3,079,018/day` to `~2,943,559/day` across `26` remaining calendar days.
- The growth is real but **breadth-poor**. The closed `2026-06-04` UTC day cleared `5,226,474` creates against a `3,081,645/day` required pace (`+2,111,228` over-pace per [docs/daily-product-target-shortfall-2026-06-05.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-05.md)), but `100%` of the last completed hour's writes came from the `shopify` family alone. Six of the last eight hourly throughput checks failed the `150,000/hour` bar — `8` failure-report child issues were filed against [BUY-29861](/BUY/issues/BUY-29861) overnight.
- Lyra distribution moved. Surf-confirmed live MCP directory listings rose to `4` (`Glama`, `Smithery`, `mcp.so`, `punkpeye/awesome-mcp-servers`) and a path to the official `modelcontextprotocol/registry` is staged in [BUY-30544](/BUY/issues/BUY-30544). Reed usage telemetry moved up too: live PostHog June MTD shows `1,600` `api_query` events (`+171 d/d`), `50` `mcp_tool_call` events (`+44 d/d`, the first material MCP usage signal), and `83` active AI agents (`+24 d/d`).
- Rex's production health is mixed. Same-day `API Catalog Discovery` p95 worsened by `+8 ms` to `629 ms`. Trailing-24-hour uptime across the three core monitors recovered to `100.000%` from yesterday's `99.566%`. The `30`-day uptime on those same monitors is still at `~90.99%–91.64%` because the historical incident window remains in the trailing window.
- The most important live blocker chains are [BUY-29861](/BUY/issues/BUY-29861) (hourly throughput breadth) and [BUY-29835](/BUY/issues/BUY-29835) (sustained-write path) for Oracle, [BUY-29183](/BUY/issues/BUY-29183) -> [BUY-29190](/BUY/issues/BUY-29190) for API latency, [BUY-25134](/BUY/issues/BUY-25134) for runtime/catalog scoreboard integrity, [BUY-24263](/BUY/issues/BUY-24263) for exact indexed-pages reporting, [BUY-22421](/BUY/issues/BUY-22421) for exact company-wide API-key reporting, and [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859) for replacing Reed's stale June 1 accepted search-success baseline.

## Daily Failure Summary

1. Hourly throughput failed `6/8` overnight checks against the `150,000/hour` bar.
   Lesson learned: a single sustained Shopify lane is enough to swing hours under threshold whenever an auxiliary lane (ebay_us, CC-MAIN, Google Shopping) drops out; breadth, not depth, is the live constraint.
2. The public runtime catalog surface still disagrees with the canonical DB and still misreports active products.
   Lesson learned: large catalog wins are invisible to external scoreboards until [BUY-25134](/BUY/issues/BUY-25134) replaces the `pg_class_fallback` approximation path.
3. API p95 worsened to `629 ms` while same-day uptime recovered to `100%`.
   Lesson learned: uptime recovery without latency recovery still fails the `<100 ms` June 30 commitment, and the `30`-day uptime ratio remains far below `99.9%` because the trailing window still contains the recent incident burst.
4. Reed's accepted search-success baseline is still `2.67%` MCP / `0%` REST.
   Lesson learned: usage telemetry (the first material MCP signal arrived today) cannot compensate for a still-broken core search promise; the rerun chain [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859) must land.
5. Exact indexed pages and exact company-wide developer API keys remain blocked by missing access.
   Lesson learned: unresolved access paths are KPI blockers, not reporting footnotes — [BUY-24263](/BUY/issues/BUY-24263) (GSC) and [BUY-22421](/BUY/issues/BUY-22421) (secrets registry) must be provisioned to make the Lyra board honest.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---:|---:|---:|---|
| Products index (active) | `23,467,460` exact active from pinned DB; `+6,671,858 d/d` | 100,000,000 | 76,532,540 short | [BUY-29861](/BUY/issues/BUY-29861) |
| Real merchants | `44,008` exact distinct product-backed merchants from pinned DB; `+19,073 d/d` | 150,000 | 105,992 short | [BUY-22685](/BUY/issues/BUY-22685) |
| US coverage | `32.57%` exact product-row share (`7,661,634 / 23,521,726`); `-12.09 pp d/d` because Shopify ingest is materially non-US | 50% | 17.43 pp short | [BUY-22685](/BUY/issues/BUY-22685) |
| Products found / runtime surface | Exact pinned DB is `23,521,726`; public runtime stats are `23,419,232` total and `23,419,232` "active" (`102,494` behind canonical and misreporting active=total) | 100,000,000 | 76,478,274 short | [BUY-25134](/BUY/issues/BUY-25134) |
| Platforms | `91` exact populated `products.platform` values from pinned DB; `+1 d/d` | 35 | 56 above target | None on count |
| Monthly visits | `407` browser `$pageview` events through closed `2026-06-04` UTC window (live PostHog); `45` unique persons June MTD through `2026-06-05 06:21 UTC` | 25,000 | 24,593 short (events) | [BUY-22687](/BUY/issues/BUY-22687) |
| Developer API keys | Blocked; exact company-wide count blocked because `GET /api/companies/{companyId}/secrets` is `403 Board access required`; runtime registrations are not the KPI | 1,000 | Exact gap blocked | [BUY-22421](/BUY/issues/BUY-22421) |
| Indexed pages | Blocked; exact count blocked because Search Console still requires OAuth/service-account; `GET .../webmasters/v3/sites?key=$GOOGLE_API_KEY` returns `401 UNAUTHENTICATED` | 50,000 | Exact gap blocked | [BUY-24263](/BUY/issues/BUY-24263) |
| Directory listings | `4` Surf-confirmed live MCP listings (`Glama`, `Smithery`, `mcp.so`, `punkpeye/awesome-mcp-servers`); `+2 d/d` | 25 | 21 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Framework integrations | `1` named live framework bucket (`custom`); `0 d/d` on count | 5 | 4 short | [BUY-22687](/BUY/issues/BUY-22687) |
| MCP tool calls / month | `50` June MTD `mcp_tool_call` events from live PostHog at `2026-06-05 06:21 UTC`; `+44 d/d` (first material MCP usage signal) | 200,000 | 199,950 short | [BUY-22731](/BUY/issues/BUY-22731) |
| API queries / month | `1,600` June MTD `api_query` events from live PostHog at `2026-06-05 06:21 UTC`; `+171 d/d` | 500,000 | 498,400 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Search success | `0%` canonical REST and `2.67%` accepted MCP harness baseline; `0 d/d` because June 1 accepted baseline still has not been replaced | 85% | 85 pp short on REST; 82.33 pp short on MCP | [BUY-29852](/BUY/issues/BUY-29852) |
| Roadmap Phase 1 + 2 | `4` banked P-items last confirmed in the accepted plan path; prior-day delta unavailable from a newer accepted revision | >=9 of 14 | 5 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| Active AI agents / month | `83` June MTD unique active agents on `api_query` or `mcp_tool_call`; `+24 d/d` | 100 | 17 short | [BUY-22731](/BUY/issues/BUY-22731) |
| API p95 latency | `629 ms` same-day probe-based p95 on `API Catalog Discovery`; `+8 ms d/d` versus yesterday's `621 ms` package | <100 ms | 529 ms above target | [BUY-29183](/BUY/issues/BUY-29183) |
| Engineering deliverables | `86` Rex `done` issues in June UTC so far (raw count includes incident closes and hourly-throughput artifacts); standing qualifying rule is being recalibrated by [BUY-31xxx tooling follow-up] same day | 40 / month | Above raw target; qualifying rule revision pending | [BUY-22685](/BUY/issues/BUY-22685) |
| Core uptime (24h) | `100.000%` trailing-24-hour mean across the three core production monitors (`API Catalog Discovery`, `/health/db`, `openapi`); `+0.434 pp d/d` recovery | >99.9% | Above target on 24h; `30-day` still at `90.99%-91.64%` from historical incident window | [BUY-29183](/BUY/issues/BUY-29183) |
| Catalog-growth unblock | `Yes`; `0 d/d` and the historical unblock chain remains closed | Yes | Complete | None on the historical gate |

## Vera

Current focus:
- publish the dated `2026-06-05` CEO report with fresh same-heartbeat top-line Oracle counts, live Lyra and Reed telemetry, same-day Rex production-health evidence, and an honest breadth-failure callout on the new hourly-throughput chain.

24-hour movement and required pace:
- renamed the execution issue to the required dated form and reran the exact Oracle top-line counts against `data/.catalog_db_url`.
- the exact Oracle top line jumped by `+6,705,215` total and `+6,671,858` active, so the required real-product pace falls from `~3,079,018/day` to `~2,943,559/day` across the remaining `26` calendar days through `2026-06-30`.
- Lyra directory listings moved from `2` to `4`, Reed `mcp_tool_call` events moved from `6` to `50`, and Rex 24h core uptime recovered from `99.566%` to `100.000%`.

Plan and adjustments being made today:
- keep the pinned maglev DB as the only valid Oracle source of truth.
- keep the runtime/public catalog drift explicit until [BUY-25134](/BUY/issues/BUY-25134) is closed.
- keep the breadth-failure pattern from [BUY-29861](/BUY/issues/BUY-29861) front-of-mind so the `+6.7M` headline does not obscure structural risk.
- keep blocked Lyra KPIs explicit with named owner/action paths instead of substituting softer proxies.
- keep Reed search success anchored to the last accepted baseline until the rerun path under [BUY-29852](/BUY/issues/BUY-29852) lands.
- route the finished report to [@Rich](user://MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6) through the issue-document confirmation path.

Five biggest failures of the day:
1. Hourly throughput chain failed `6/8` checks overnight.
   Lesson learned: single-lane Shopify dependence makes intra-day variance the live risk even on a beat day.
2. Runtime catalog stats still misreport `active = total`.
   Lesson learned: a +6.7M private win is irrelevant to the board if the public scoreboard cannot serve it.
3. API p95 worsened by `+8 ms` to `629 ms`.
   Lesson learned: latency and uptime are independent risks; one recovering does not justify silence on the other.
4. Two Lyra KPIs remain access-blocked since `2026-05-26`.
   Lesson learned: long-running access blockers should be escalated to a fresh owner each report, not carried as the same name.
5. Reed search success is still stale at the floor.
   Lesson learned: a `+44 d/d` MCP tool-call delta cannot mask a `0%` REST search-success accepted baseline.

Current blockers:
- [BUY-29861](/BUY/issues/BUY-29861) (hourly throughput breadth)
- [BUY-29835](/BUY/issues/BUY-29835) (sustained-write path)
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-29183](/BUY/issues/BUY-29183)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-29852](/BUY/issues/BUY-29852)

Active work in progress:
- final report publication to the `daily_ceo_report` issue document on [BUY-30830](/BUY/issues/BUY-30830).
- Rich review routing and `request_confirmation` interaction.

Source of truth:
- this report
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)
- [docs/daily-ceo-report-2026-06-04.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-2026-06-04.md)

## Rex

Current focus:
- sustain the breadth of the Oracle write path so the `+6.7M d/d` lift survives the next 24 hours, restore API p95 toward `<100 ms`, and protect the recovered 24h uptime number from sliding back below `99.9%`.

24-hour movement and required pace:
- API Catalog Discovery same-day p95 moved from `560 ms` to `621 ms` to `629 ms` (`+8 ms d/d` and `+69 ms` against the `2026-06-03` package).
- trailing-24-hour uptime across the three core monitors recovered from `99.566%` to `100.000%`.
- `30`-day uptime on the same monitors remains weak (`90.989%` API Catalog Discovery, `90.759%` `/health/db`, `91.642%` openapi) because the historical incident window is still in the trailing window.
- closed-day `2026-06-04` UTC catalog creates were `5,226,474` (a `+2,111,228` over-pace beat against the required `3,081,645/day`); open `2026-06-05` UTC partial day already shows `1,095,659` creates, but `6/8` overnight hourly checks failed the `150,000/hour` bar (see [BUY-29861](/BUY/issues/BUY-29861) child reports [BUY-30457](/BUY/issues/BUY-30457), [BUY-30522](/BUY/issues/BUY-30522), [BUY-30558](/BUY/issues/BUY-30558), [BUY-30597](/BUY/issues/BUY-30597), [BUY-30641](/BUY/issues/BUY-30641), [BUY-30713](/BUY/issues/BUY-30713), [BUY-30757](/BUY/issues/BUY-30757), [BUY-30797](/BUY/issues/BUY-30797)).

Plan and adjustments being made today:
- keep same-day UptimeRobot packages as the current latency and uptime source.
- close the authenticated search/runtime blocker path under [BUY-29183](/BUY/issues/BUY-29183) -> [BUY-29190](/BUY/issues/BUY-29190).
- keep pressure on [BUY-25134](/BUY/issues/BUY-25134) so public runtime stats stop disagreeing with canonical DB truth (now `102,494` behind).
- restore secondary write lanes (`ebay_us`, CC-MAIN, Google Shopping) so the hourly bar clears on breadth, not just on Shopify volume.

Five biggest failures of the day:
1. API p95 worsened to `629 ms`.
   Lesson learned: latency regression on a recovered-uptime day still kills the `<100 ms` commitment.
2. `30`-day uptime remains at `~91%` across the three core monitors.
   Lesson learned: 24h numbers cannot redeem 30d numbers until the historical incident window rolls off.
3. Six of eight overnight hours failed the `150,000/hour` bar.
   Lesson learned: any narrow lane mix is a beat-day-killer; breadth has to be measured per hour, not per day.
4. The runtime catalog surface still misreports `active = total` at `23,419,232`.
   Lesson learned: a stale public scoreboard makes the canonical win unobservable.
5. The qualifying-engineering-deliverable rule has not been recalibrated against the new incident-close volume.
   Lesson learned: when a counting rule starts overcounting, the rule must be revised same-day rather than carried forward.

Current blockers:
- [BUY-29183](/BUY/issues/BUY-29183)
- [BUY-29190](/BUY/issues/BUY-29190)
- [BUY-25134](/BUY/issues/BUY-25134)
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-29861](/BUY/issues/BUY-29861)

Active work in progress:
- infrastructure and runtime KPI integrity under [BUY-22685](/BUY/issues/BUY-22685).
- latency reduction and sustained breadth-first write-path verification.

Source of truth:
- [BUY-22685](/BUY/issues/BUY-22685)
- live UptimeRobot `getMonitors` package collected at `2026-06-05 06:22 UTC`
- live Paperclip June done-issue ledger for `Rex`
- [docs/buy-30834-hourly-throughput-check-2026-06-05T06.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-30834-hourly-throughput-check-2026-06-05T06.md)

## Oracle

Current focus:
- keep the exact pinned-DB Oracle scoreboard canonical, convert today's `+6.7M d/d` Shopify-driven lift into sustained multi-source breadth, and restore non-US coverage discipline.

24-hour movement and required pace:
- fresh exact rerun at `2026-06-05 06:14 UTC`: `23,521,726` total products and `23,467,460` active products.
- both top-line counts beat the prior day's required pace materially: `+6,705,215 d/d` total and `+6,671,858 d/d` active.
- closed `2026-06-04` UTC day cleared `5,226,474` creates / `5,192,873` created-and-active against a `3,081,645/day` pace, a `+2,111,228` over-pace day.
- exact distinct product-backed merchants rose from `24,935` to `44,008` (`+19,073 d/d`).
- exact populated platforms rose from `90` to `91`.
- exact US product rows rose from `7,509,763` to `7,661,634` (`+151,871`), but US share fell from `44.66%` to `32.57%` because new ingest is materially non-US.
- the required real-product pace falls from `~3,079,018/day` to `~2,943,559/day` for the remaining `26` calendar days.

Plan and adjustments being made today:
- keep `public.products` as the canonical source for product, active-product, product-backed-merchant, platform, and US-share KPIs.
- keep `public.merchants` visible only as registry context (still `68,384` rows).
- keep the runtime-surface mismatch explicit until [BUY-25134](/BUY/issues/BUY-25134) is closed.
- treat the breadth-failure pattern from [BUY-29861](/BUY/issues/BUY-29861) as the dominant Oracle execution risk for `2026-06-05` because single-lane Shopify dependence will not survive a Shopify outage.
- treat [BUY-22684](/BUY/issues/BUY-22684) as the completed plan/proof artifact and continue the live execution problem on the Rex-owned throughput/runtime lane.

Five biggest failures of the day:
1. Six of eight overnight hourly throughput checks failed the `150,000/hour` bar.
   Lesson learned: a single-source breadth profile cannot reliably hit the per-hour throughput floor.
2. US coverage regressed from `44.66%` to `32.57%`.
   Lesson learned: ingest waves that are not market-balanced visibly damage US-coverage KPIs the same day.
3. Real merchants are still only `44,008 / 150,000`.
   Lesson learned: even with `+19,073 d/d`, the absolute gap remains large enough that breadth-first ingest matters more than depth.
4. The public runtime surface still trails canonical DB by `102,494` rows and still misreports active products.
   Lesson learned: serving-layer trust is independent of writer-layer wins.
5. Oracle's planning artifact is closed, but the live execution lane is still on Rex.
   Lesson learned: a closed planning issue does not mean an owned execution path; the day-to-day breadth problem is unowned until Rex's throughput recovery commits land.

Current blockers:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-29861](/BUY/issues/BUY-29861)
- [BUY-29835](/BUY/issues/BUY-29835)
- [BUY-25134](/BUY/issues/BUY-25134)

Active work in progress:
- exact pinned-DB scoreboarding
- hourly throughput recovery via [BUY-29861](/BUY/issues/BUY-29861) child-failure chain
- runtime reconciliation under [BUY-25134](/BUY/issues/BUY-25134)

Source of truth:
- direct pinned-DB queries on `public.products` and `public.merchants` via `data/.catalog_db_url`
- [BUY-22684](/BUY/issues/BUY-22684#document-plan)
- [docs/daily-product-target-shortfall-2026-06-05.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-05.md)
- [docs/daily-source-mix-plan-2026-06-05.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-05.md)

## Lyra

Current focus:
- convert the `+2` directory-listing lift into a clear path to `25`, keep access-blocked exact KPIs visible and owned, and pursue the staged official-registry listing under [BUY-30544](/BUY/issues/BUY-30544).

24-hour movement and required pace:
- Surf-confirmed live MCP directory listings moved from `2` to `4` (`Glama`, `Smithery`, `mcp.so`, `punkpeye/awesome-mcp-servers`).
- additional directory pursuit is staged in [BUY-30382](/BUY/issues/BUY-30382) (appcypher/awesome-mcp-servers), [BUY-30515](/BUY/issues/BUY-30515) (wong2/awesome-mcp-servers), [BUY-30514](/BUY/issues/BUY-30514) (RemoteMCPList.com), [BUY-30443](/BUY/issues/BUY-30443) (opentools.com), [BUY-30444](/BUY/issues/BUY-30444) (Slashdot), [BUY-30437](/BUY/issues/BUY-30437) (Futurepedia + AI Tools Dir), [BUY-30438](/BUY/issues/BUY-30438) (AgentOps + Toolhouse + AlternativeTo), [BUY-30447](/BUY/issues/BUY-30447) (RapidAPI + Postman + API Tracker), and [BUY-30446](/BUY/issues/BUY-30446) (OpenTools.ai).
- official `modelcontextprotocol/registry` submission is staged with validated `server.json`; blocked on GitHub auth for `mcp-publisher` per [BUY-30544](/BUY/issues/BUY-30544).
- live PostHog `$pageview` events for June MTD through the closed `2026-06-04` UTC window are `407`; unique persons June MTD are `45`. Yesterday's report cited `765` events through the closed `2026-06-03` UTC window using a "browser-side human" filter; today's `407` uses the strict raw `$pageview` count, so the day-over-day movement is filter-dependent and noted explicitly.
- live framework integrations remain `1`.
- exact company-wide developer API keys remain blocked at the secrets-registry layer; exact indexed pages remain blocked at Search Console OAuth.

Plan and adjustments being made today:
- keep monthly visits on the live PostHog browser `$pageview` source with the same filter used by the prior day's report; today's number uses the raw event count and notes the filter delta with the prior day instead of substituting an apples-to-oranges proxy.
- keep developer API keys blocked on [BUY-22421](/BUY/issues/BUY-22421) until real issuance or a board-readable persisted ledger exists.
- keep indexed pages blocked on [BUY-24263](/BUY/issues/BUY-24263) until Search Console OAuth/service-account access or an exported coverage report exists.
- pursue the official MCP registry path so an additional directory entry lands before the next executive report.
- continue directory and integration execution under [BUY-22687](/BUY/issues/BUY-22687).

Five biggest failures of the day:
1. Exact company-wide developer API key count is still blocked.
   Lesson learned: runtime-visible keys are not a substitute for the company KPI; a board-readable ledger must exist.
2. Exact indexed-page count is still blocked.
   Lesson learned: Search Console access has now blocked the indexed-pages KPI for over a week; the unblock owner ([Rex]) should escalate or hand off.
3. Directory listings are still only `4 / 25`.
   Lesson learned: `+2 d/d` is the right direction but the lane still needs the staged Surf/Bolt batch to land in the next `48` hours.
4. Framework integrations are still only `1 / 5`.
   Lesson learned: the telemetry-defined integration surface remains a four-issue gap with no movement.
5. Monthly visits are still well below pace.
   Lesson learned: a single Shopify-driven catalog wave does not translate into developer demand unless distribution lands too.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22687](/BUY/issues/BUY-22687)

Active work in progress:
- directory and integration lane under [BUY-22687](/BUY/issues/BUY-22687)
- official-registry listing path under [BUY-30544](/BUY/issues/BUY-30544)
- exact KPI access remediation under Rex-owned blocker paths

Source of truth:
- [BUY-22687](/BUY/issues/BUY-22687)
- live PostHog HogQL queries run in this heartbeat
- live `GET /api/companies/{companyId}/user-directory` (carry-forward; access path unchanged today)
- [docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md)

## Reed

Current focus:
- compound today's first-material MCP usage signal into a real adoption curve while landing the accepted search-success rerun so the `2.67%` MCP baseline is replaced.

24-hour movement and required pace:
- live PostHog June MTD `api_query` events: `1,600` (`+171 d/d`).
- live PostHog June MTD `mcp_tool_call` events: `50` (`+44 d/d` — first material MCP usage signal of the cycle).
- live PostHog June MTD unique active AI agents on `api_query` or `mcp_tool_call`: `83` (`+24 d/d`).
- accepted search-success baseline remains `0%` canonical REST and `2.67%` MCP harness because the rerun chain [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859) has not landed.
- roadmap Phase 1 + 2 remains at `4` banked P-items in the last confirmed accepted plan path.

Plan and adjustments being made today:
- keep live June PostHog telemetry as the current usage source for the CEO report.
- keep roadmap milestone status anchored to [BUY-22731](/BUY/issues/BUY-22731#document-plan) until a newer accepted revision supersedes it.
- keep the accepted search-success baseline explicit until the rerun chain [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859) lands; the live escalation [BUY-30201](/BUY/issues/BUY-30201) flagged Reed's blocker assignee as paused — needs reassignment to an active owner.
- treat the live problem as product-quality execution first and usage growth second.

Five biggest failures of the day:
1. Accepted search-success baseline is still effectively at the floor.
   Lesson learned: the product still fails its core job at the accepted baseline; rerun chain must land.
2. The blocker chain through [BUY-29852](/BUY/issues/BUY-29852) routes through a paused assignee per [BUY-30201](/BUY/issues/BUY-30201).
   Lesson learned: a blocker chain that points at a paused assignee is dead by default; reassignment is the gating action.
3. API queries are at `1,600 / 500,000`.
   Lesson learned: usage is moving but still nowhere near pace; demand-side work is the next executive ask.
4. MCP tool calls are at `50 / 200,000`.
   Lesson learned: the first material MCP signal is encouraging but the absolute gap remains `> 199,000`.
5. Roadmap completion is still `4 / 9`.
   Lesson learned: the accepted plan still needs materially more shipped P-items.

Current blockers:
- [BUY-29852](/BUY/issues/BUY-29852)
- [BUY-29859](/BUY/issues/BUY-29859)
- [BUY-22731](/BUY/issues/BUY-22731)
- [BUY-30201](/BUY/issues/BUY-30201)

Active work in progress:
- live June usage tracking
- accepted search-success rerun dependency path
- roadmap execution against the last accepted plan revision

Source of truth:
- [BUY-22731](/BUY/issues/BUY-22731)
- live PostHog HogQL queries run in this heartbeat
- [docs/daily-ceo-report-input-2026-06-02-reed.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-input-2026-06-02-reed.md)

## What Has Been Accomplished

- Renamed the execution issue to the required dated form for `2026-06-05 UTC`.
- Re-ran the canonical Oracle top-line product counts directly against `data/.catalog_db_url` and confirmed the `+6,705,215 d/d` lift on total products and `+6,671,858 d/d` on active.
- Refreshed the public runtime catalog stats endpoint and preserved the live `102,494`-row drift versus canonical DB truth.
- Refreshed live PostHog telemetry for Lyra ($pageview) and Reed (`api_query`, `mcp_tool_call`, active agents) and recorded a first-material MCP usage signal.
- Refreshed Rex's same-day UptimeRobot production-health package and recovered the trailing-24-hour uptime number to `100.000%`.
- Linked the new hourly-throughput failure chain ([BUY-29861](/BUY/issues/BUY-29861) and its eight overnight children) so the breadth-vs-depth pattern is visible to the board.
- Surfaced the staged official-registry listing path under [BUY-30544](/BUY/issues/BUY-30544) as the next Lyra directory move.

## Key Things Needed To Hit June 30 Goals

- Convert today's `+6.7M` ingest into sustained multi-source breadth so the per-hour `150,000/hour` floor clears without depending on `shopify` alone.
- Close [BUY-25134](/BUY/issues/BUY-25134) so the public runtime catalog surface matches canonical DB truth and stops misreporting `active = total`.
- Close [BUY-29183](/BUY/issues/BUY-29183) -> [BUY-29190](/BUY/issues/BUY-29190) so API p95 returns toward `<100 ms` and `30`-day uptime rises back above `99.9%`.
- Provision exact indexed-pages access under [BUY-24263](/BUY/issues/BUY-24263) and exact company-wide API-key visibility under [BUY-22421](/BUY/issues/BUY-22421).
- Land the accepted Reed search-success rerun chain under [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859) and reassign its paused-owner step per [BUY-30201](/BUY/issues/BUY-30201), then improve the baseline materially.
- Land the staged Lyra directory batch (Surf/Bolt queue) so the directory KPI clears `10` before the next executive report.

## Board Blockers Summary

- [BUY-24263](/BUY/issues/BUY-24263): Rex still needs Google Search Console OAuth/service-account access or an exported coverage report attached so indexed pages can be reported exactly.
- [BUY-22421](/BUY/issues/BUY-22421): Rex still needs a board-readable secrets inventory or persisted issuance/export path so the company-wide developer API key KPI becomes exactly reportable.
- [BUY-30201](/BUY/issues/BUY-30201): Reed's blocker chain through [BUY-29852](/BUY/issues/BUY-29852) routes through a paused assignee; needs reassignment to an active owner.
- [BUY-29861](/BUY/issues/BUY-29861): hourly throughput chain failed `6/8` overnight checks; board owner action on lane breadth is the right escalation.
- Rich review is required on this final report artifact via the `daily_ceo_report` confirmation path.

## Incidents And Execution Path

- Oracle throughput and runtime integrity: [BUY-22684](/BUY/issues/BUY-22684) -> [BUY-22685](/BUY/issues/BUY-22685) -> [BUY-29183](/BUY/issues/BUY-29183) -> [BUY-29190](/BUY/issues/BUY-29190).
- Hourly throughput breadth: [BUY-29861](/BUY/issues/BUY-29861) -> [BUY-30457](/BUY/issues/BUY-30457), [BUY-30522](/BUY/issues/BUY-30522), [BUY-30558](/BUY/issues/BUY-30558), [BUY-30597](/BUY/issues/BUY-30597), [BUY-30641](/BUY/issues/BUY-30641), [BUY-30713](/BUY/issues/BUY-30713), [BUY-30757](/BUY/issues/BUY-30757), [BUY-30797](/BUY/issues/BUY-30797), [BUY-30834](/BUY/issues/BUY-30834).
- Runtime/catalog surface reconciliation: [BUY-25134](/BUY/issues/BUY-25134).
- Lyra measurement and access path: [BUY-22687](/BUY/issues/BUY-22687) -> [BUY-24263](/BUY/issues/BUY-24263) and [BUY-22421](/BUY/issues/BUY-22421).
- Lyra directory expansion: [BUY-22687](/BUY/issues/BUY-22687) -> [BUY-30544](/BUY/issues/BUY-30544) and the Surf/Bolt queue.
- Reed search-success rerun path: [BUY-22731](/BUY/issues/BUY-22731) -> [BUY-29852](/BUY/issues/BUY-29852) -> [BUY-29859](/BUY/issues/BUY-29859), with [BUY-30201](/BUY/issues/BUY-30201) as the live paused-owner escalation.

## Source Inputs

- direct pinned-DB queries on `public.products` and `public.merchants` via `data/.catalog_db_url`
- live `GET https://api.buywhere.ai/v1/catalog/stats`
- live `GET https://api.buywhere.ai/health/db`
- live PostHog HogQL queries against project `415112`
- live UptimeRobot `getMonitors` package collected at `2026-06-05 06:22 UTC`
- live Paperclip June done-issue ledger for `Rex`
- [BUY-22684](/BUY/issues/BUY-22684)
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-22687](/BUY/issues/BUY-22687)
- [BUY-22731](/BUY/issues/BUY-22731)
- [BUY-29861](/BUY/issues/BUY-29861)
- [BUY-29835](/BUY/issues/BUY-29835)
- [docs/daily-product-target-shortfall-2026-06-05.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-05.md)
- [docs/daily-source-mix-plan-2026-06-05.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-05.md)
- [docs/buy-30834-hourly-throughput-check-2026-06-05T06.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-30834-hourly-throughput-check-2026-06-05T06.md)
