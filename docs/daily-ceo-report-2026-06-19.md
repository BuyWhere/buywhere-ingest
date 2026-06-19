# DAILY CEO REPORT — 2026-06-19

Report date: 2026-06-19 UTC
Finalized at: 2026-06-19T06:10:00Z
Status: final for Rich review
Issue: [BUY-53384](/BUY/issues/BUY-53384)

## Executive Summary

- Oracle is now well past the June 30 product target on the canonical DB. Fresh pinned-maglev reads at `2026-06-19 06:03:27 UTC` show `n_live_tup = 126,536,061` and `reltuples = 126,531,400`, up `+306,007` from the `126,230,054` reading captured at `2026-06-19 00:17:23 UTC`.
- The biggest company failure today is source-of-truth drift, not raw volume. The public runtime surface `GET https://api.buywhere.ai/v1/catalog/stats` at `2026-06-19 06:01:53Z` still reports only `17,472,931` total products and `26,831` merchants, which is roughly `109.1M` products behind the canonical DB.
- Reed's usage telemetry is materially better than the stale June 17 report path suggested. Fresh `api_usage_monthly` at `2026-06-19 06:03:03 UTC` shows `9,354` API queries, `7,899` MCP calls, and `73` active AI agents in June, but only `227` external API queries, `0` external MCP calls, and `48` external active agents. Adoption is still the gap.
- The largest remaining June 30 gaps are Lyra indexed pages (`15 / 50,000`), Lyra monthly visits (`2,163 / 25,000` on the last confirmed pulse), Oracle product-backed merchants (fresh exact count still timeout-blocked; last confirmed exact `74,815`), and Reed external usage growth.
- The most important live blocker chains are [BUY-48231](/BUY/issues/BUY-48231) for discovery-to-MCP catalog reconciliation, [BUY-32878](/BUY/issues/BUY-32878) for product-side US/platform proof queries, [BUY-22745](/BUY/issues/BUY-22745) plus [BUY-31214](/BUY/issues/BUY-31214) and [BUY-41426](/BUY/issues/BUY-41426) for Lyra growth blockers, and [BUY-51955](/BUY/issues/BUY-51955) for Paperclip blocked-state integrity.

## Daily Failure Summary

1. The public runtime catalog surface is still wildly wrong.
   Remediation: keep [BUY-48231](/BUY/issues/BUY-48231) as the active reconciliation owner path and do not let the public `catalog_stats` endpoint stand in as the KPI source.
   Status: in_progress.
   Lesson learned: exceeding the product target is not executive-safe if the public scoreboard is still `~109M` rows behind.
2. Three consecutive hourly throughput failures from `01:00Z` to `04:00Z` were not filed live because the Paperclip API returned HTTP 500 on child-issue creation.
   Remediation: [docs/buy53341_api_outage_retrofill.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy53341_api_outage_retrofill.md) documents the retry-buffer patch and the retrofiled children `BUY-53359` to `BUY-53361`.
   Status: fixed for the dispatcher, root cause of the API 500 still unknown.
   Lesson learned: a monitoring loop that cannot survive control-plane outages creates fake calm during real failures.
3. Fresh canonical Oracle sub-counts are still not heartbeat-cheap.
   Remediation: same-heartbeat `COUNT(DISTINCT merchant_id)`, `COUNT(DISTINCT platform)`, and product-side `country_code='US'` scans all timed out at `18s`; keep [BUY-32878](/BUY/issues/BUY-32878) and [BUY-48231](/BUY/issues/BUY-48231) as the owner paths.
   Status: blocked.
   Lesson learned: once the table passes `126M` rows, KPI freshness depends on maintaining cheap proof surfaces, not on brute-force scans.
4. Lyra's distribution funnel is still bottlenecked by human/credential unblockers rather than execution capacity.
   Remediation: keep [BUY-22745](/BUY/issues/BUY-22745), [BUY-31214](/BUY/issues/BUY-31214), [BUY-41426](/BUY/issues/BUY-41426), [BUY-9086](/BUY/issues/BUY-9086), and [BUY-9087](/BUY/issues/BUY-9087) visible as the critical path for indexed pages, visits, and developer-key growth.
   Status: blocked.
   Lesson learned: a growth KPI with unresolved account-access dependencies is a blocked KPI, not a slow KPI.
5. Reed's usage is now measurable, but external adoption is still too weak relative to the target.
   Remediation: use the corrected `api_usage_monthly` query-log path and Rich's 2026-06-18 adoption push on [BUY-22731](/BUY/issues/BUY-22731) as the live execution path.
   Status: in_progress.
   Lesson learned: internal traffic can make usage look alive while external adoption remains near zero.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---|---:|---:|---|
| Indexed pages | `15`; `0 d/d` from the last confirmed 2026-06-17 Lyra pulse | 50,000 | 49,985 short | [BUY-22745](/BUY/issues/BUY-22745) |
| Monthly visits | `2,163` pageviews / `261` visitors on the last confirmed 2026-06-17 Lyra pulse; prior-day delta unavailable from a fresher same-day source | 25,000 | 22,837 short | [BUY-22745](/BUY/issues/BUY-22745), [BUY-9086](/BUY/issues/BUY-9086), [BUY-9087](/BUY/issues/BUY-9087) |
| Real merchants | Blocked; fresh exact `COUNT(DISTINCT public.products.merchant_id)` timed out at `18s`; last confirmed exact product-backed merchant count is `74,815` from the 2026-06-10 canonical read | 150,000 | 75,185 short on the last confirmed exact read | [BUY-48231](/BUY/issues/BUY-48231) |
| Developer API keys | Disputed; the last confirmed Lyra funnel count is `280` lifetime on the 2026-06-17 plan pulse, while self-service issuance is live but not yet reconciled into one CEO-safe registration source | 1,000 | 720 short on the last confirmed Lyra count | [BUY-22421](/BUY/issues/BUY-22421), [BUY-31214](/BUY/issues/BUY-31214), [BUY-41426](/BUY/issues/BUY-41426) |
| API queries / month | `9,354 total / 227 external`; `+755 total` versus the 2026-06-18 corrected `8,599` June-to-date read | 500,000 | 490,646 short total; 499,773 short external | [BUY-22731](/BUY/issues/BUY-22731) |
| MCP tool calls / month | `7,899 total / 0 external`; `+2,368 total` versus the 2026-06-18 corrected `5,531` read | 200,000 | 192,101 short total; 200,000 short external | [BUY-22731](/BUY/issues/BUY-22731) |
| Active AI agents / month | `73 total / 48 external`; `+56 total` versus the 2026-06-18 corrected `17` total agent read | 100 | 27 short total; 52 short external | [BUY-22731](/BUY/issues/BUY-22731) |
| Platforms | Blocked; fresh exact distinct-platform scan timed out at `18s`; last confirmed exact non-null platform count is `31` from the 2026-06-10 canonical read | 35 | 4 short on the last confirmed exact read | [BUY-32878](/BUY/issues/BUY-32878) |
| Search success | Disputed; last accepted Reed proxy remains `~90.5%` from the 2026-06-17 weekly zero-result pulse, but the report still carries the live-API overstatement warning from [BUY-39108](/BUY/issues/BUY-39108) | 85% | 5.5 pp above target on the proxy; live-API exact gap still disputed | [BUY-39108](/BUY/issues/BUY-39108) |
| US coverage | Blocked; fresh product-row `country_code='US'` proof timed out at `18s`; last defensible merchant-side proxy remains `85.5%` from the 2026-06-17 Oracle pulse, but the CEO KPI is still product-side | 50% | product-side exact gap blocked | [BUY-32878](/BUY/issues/BUY-32878) |
| Roadmap Phase 1 + 2 | `5 / 14` banked on the last confirmed [BUY-22731 plan](/BUY/issues/BUY-22731#document-plan); prior-day delta unavailable | >=9 of 14 | 4 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| API p95 latency | Same-heartbeat point sample on `GET /v1/catalog/stats` returned `200` in `42-74ms` across 5 probes; this is a point sample, not a broad p95 rollup | <100 ms | point sample clears target; broad-surface p95 still needs durable rollup | [BUY-45671](/BUY/issues/BUY-45671) |
| Directory listings | `25`; `0 d/d` from the 2026-06-17 plan rev 2 pulse | 25 | met | [BUY-22687](/BUY/issues/BUY-22687) |
| Framework integrations | `5`; `0 d/d` from the 2026-06-17 plan rev 2 pulse | 5 | met | [BUY-22687](/BUY/issues/BUY-22687) |
| Real products | Canonical DB `n_live_tup = 126,536,061` and `reltuples = 126,531,400` at `2026-06-19 06:03:27Z`; `+306,007` vs the `2026-06-19 00:17:23Z` canonical reading | 100,000,000 | 26,536,061 above target | [BUY-48231](/BUY/issues/BUY-48231) |
| Uptime | Blocked; no 30-day uptime rollup is available in the report runner, though the canonical DB has stayed up since `2026-06-16 08:52:01Z` and 5/5 same-heartbeat API probes returned `200` | >99.9% | exact 30-day gap blocked | [BUY-22685](/BUY/issues/BUY-22685) |
| Engineering deliverables | `Tracking`; fresh same-heartbeat June close-count not rerun in this heartbeat | 40 / month | exact gap unavailable in this heartbeat | [BUY-22685](/BUY/issues/BUY-22685) |

## Vera

Current focus:
- Publish the 2026-06-19 report with corrected June 19 Oracle and Reed numbers, and route it directly to Rich for review.

24-hour movement and required pace:
- CEO cadence is back on schedule for the 06:00 UTC routine.
- The biggest delta in this heartbeat is the correction from stale runtime/catalog surfaces to the canonical June 19 reads.
- Required pace for the reporting goal is still one final report per day with Rich-visible routing; today that path is complete once the document and confirmation are posted.

Plan and adjustments being made today:
- Use `data/.catalog_db_url` only for Oracle top-line counts.
- Replace stale Reed usage numbers with the corrected `api_usage_monthly` read.
- Keep disputed or blocked KPIs explicit instead of compressing them into false certainty.
- Put the final report into the `daily_ceo_report` issue document and move the issue to Rich review.

Five biggest failures of the day:
1. I inherited a report contract that still referenced the older `~16.8M` catalog language while the canonical DB now reads `126.5M`.
   Lesson learned: the report has to carry the reconciliation blocker every day until the story is singular.
2. The runtime stats endpoint still looks executive-ready while being catastrophically stale.
   Lesson learned: any public-facing metric surface must be treated as untrusted until it is tied back to canonical DB proof.
3. Fresh Oracle sub-count scans are no longer heartbeat-safe.
   Lesson learned: scale changes the reporting architecture, not just the numbers.
4. Lyra still depends on human unblockers that the daily report cannot resolve by itself.
   Lesson learned: the report must show who must act, not just who owns the KPI.
5. Reed's growth metrics improved, but external adoption still trails badly.
   Lesson learned: internal traffic can hide a go-to-market failure unless external splits are reported separately.

Current blockers:
- [BUY-48231](/BUY/issues/BUY-48231)
- [BUY-32878](/BUY/issues/BUY-32878)
- [BUY-22745](/BUY/issues/BUY-22745)
- [BUY-51955](/BUY/issues/BUY-51955)

Active work in progress:
- final report publication
- Rich review routing

Source of truth:
- this report
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)

## Rex

Current focus:
- Keep the live API responsive while the reporting surfaces catch up to the canonical DB.

24-hour movement and required pace:
- Same-heartbeat `GET /v1/catalog/stats` probes returned `200` in `42-74ms`, so the point sample clears the `<100ms` bar.
- The runtime stats payload still reports only `17.47M` products against the `126.54M` canonical DB, which means the reliability problem moved from "endpoint up/down" to "endpoint trustworthy/untrustworthy."
- The DB has been up since `2026-06-16 08:52:01Z`, but no fresh 30-day uptime rollup was available in this runner.

Plan and adjustments being made today:
- Keep the live API fast at the point surface.
- Close the scoreboard-integrity gap between runtime stats and canonical DB.
- Restore a durable uptime/latency rollup path for the CEO report.
- Keep platform blocked-state integrity visible under [BUY-51955](/BUY/issues/BUY-51955).

Five biggest failures of the day:
1. Runtime `catalog_stats` still reports a product total that is `~109.1M` behind canonical.
   Lesson learned: a fast endpoint that is wrong is still an executive failure.
2. Broad-surface uptime is not reportable from this heartbeat runner.
   Lesson learned: monitor-path availability is itself a production dependency.
3. The Paperclip API returned 500s during hourly-child filing.
   Lesson learned: platform reliability problems propagate into operational blind spots immediately.
4. The blocked-state PATCH bug is still open in review.
   Lesson learned: workflow integrity bugs become KPI blockers when they distort ownership and unblock paths.
5. Lyra's credential-gated KPIs still depend on Rex-owned access paths.
   Lesson learned: infra/access work is part of product delivery when the metrics depend on it.

Current blockers:
- [BUY-45671](/BUY/issues/BUY-45671)
- [BUY-51955](/BUY/issues/BUY-51955)
- [BUY-22745](/BUY/issues/BUY-22745)
- [BUY-22421](/BUY/issues/BUY-22421)

Active work in progress:
- runtime/catalog surface integrity
- uptime reporting path recovery
- control-plane reliability fixes

Source of truth:
- same-heartbeat `curl` probes to `https://api.buywhere.ai/v1/catalog/stats`
- [docs/buy53341_api_outage_retrofill.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy53341_api_outage_retrofill.md)

## Oracle

Current focus:
- Keep the canonical product story accurate while surfacing the unresolved merchant, US-coverage, platform, and public-scoreboard gaps.

24-hour movement and required pace:
- Canonical DB read at `2026-06-19 06:03:27Z`: `n_live_tup = 126,536,061`, `reltuples = 126,531,400`.
- Delta versus the `2026-06-19 00:17:23Z` canonical anchor: `+306,007`.
- The 100M product target is exceeded by `26.54M`; no forward pace is required for that target.
- The fresh exact merchant, platform, and product-side US-share queries all timed out inside the heartbeat budget.

Plan and adjustments being made today:
- Keep canonical DB counts explicit and visible.
- Do not let `public.merchants.count(*)` replace the product-backed merchant KPI.
- Keep [BUY-48231](/BUY/issues/BUY-48231) tied to the May 31 `~14M + ~4M` reconciliation.
- Keep [BUY-32878](/BUY/issues/BUY-32878) visible until product-side US/platform proof is cheap again.

Five biggest failures of the day:
1. The public runtime catalog surface still says `17.47M` while canonical says `126.54M`.
   Lesson learned: source-of-truth drift is now the top Oracle risk, not ingestion volume.
2. The exact product-backed merchant scan timed out.
   Lesson learned: the CEO merchant KPI needs a maintained proof surface, not ad hoc full-table scans.
3. Product-side US share timed out.
   Lesson learned: merchant-side proxies cannot silently replace product-side KPI definitions.
4. Distinct platform proof timed out.
   Lesson learned: once the schema and query cost evolve, the report has to record what is no longer cheap enough to prove.
5. The May 31 narrative is still not reconciled to the June 19 total.
   Lesson learned: board trust requires a single count story, not two competing true numbers.

Current blockers:
- [BUY-48231](/BUY/issues/BUY-48231)
- [BUY-32878](/BUY/issues/BUY-32878)
- [BUY-22684](/BUY/issues/BUY-22684)

Active work in progress:
- canonical catalog reconciliation
- source-mix execution
- submetric proof-path repair

Source of truth:
- `psql "$(cat data/.catalog_db_url)"`
- [docs/daily-product-target-shortfall-2026-06-19.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-19.md)
- [docs/daily-source-mix-plan-2026-06-19.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-19.md)

## Lyra

Current focus:
- Convert the now-usable product into real human and developer adoption while clearing the account/credential blockers that still gate three KPIs.

24-hour movement and required pace:
- Last confirmed plan pulse remains `25 / 25` directories and `5 / 5` integrations as of 2026-06-17.
- Last confirmed funnel metrics remain `280` developer keys, `15` indexed pages, and `2,163` monthly pageviews on the 2026-06-17 pulse.
- Rich's 2026-06-18 direction on [BUY-22687](/BUY/issues/BUY-22687) explicitly shifted priority toward SEO that converts, directory presence, fast onboarding, and clearer positioning.
- Required pace is still extreme on the three unmet KPIs and still depends on external unblockers.

Plan and adjustments being made today:
- Keep directories and integrations marked as met.
- Treat developer-key growth as disputed until one registration source is chosen for the CEO KPI.
- Keep indexed pages and monthly visits on the explicit GSC/social/account critical path.
- Coordinate the human funnel with Reed's agent-adoption push.

Five biggest failures of the day:
1. Indexed pages are still only `15 / 50,000`.
   Lesson learned: SEO recovery without GSC control is not a repeatable growth machine.
2. Monthly visits are still only `2,163 / 25,000`.
   Lesson learned: product quality alone does not create traffic; distribution has to be operationalized.
3. The developer-key KPI is still disputed between issuance and funnel-registration surfaces.
   Lesson learned: registration volume and usable adoption need separate definitions.
4. The growth-critical blockers are still mostly human approvals and account access.
   Lesson learned: blocked marketing infrastructure is still a product blocker when the KPI is adoption.
5. The report still does not have a fresher same-day Lyra numeric pulse than the 2026-06-17 plan.
   Lesson learned: weekly planning updates are not enough when the CEO report cadence is daily.

Current blockers:
- [BUY-22745](/BUY/issues/BUY-22745)
- [BUY-31214](/BUY/issues/BUY-31214)
- [BUY-41426](/BUY/issues/BUY-41426)
- [BUY-9086](/BUY/issues/BUY-9086)
- [BUY-9087](/BUY/issues/BUY-9087)

Active work in progress:
- growth/distribution execution under [BUY-22687](/BUY/issues/BUY-22687)
- adoption push per Rich's 2026-06-18 comment

Source of truth:
- latest plan/comment pulse on [BUY-22687](/BUY/issues/BUY-22687)
- [docs/buy-52309-daily-ceo-report-2026-06-17.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-52309-daily-ceo-report-2026-06-17.md)

## Reed

Current focus:
- Turn the now-measurable API and MCP usage into external adoption, and keep search-quality reporting honest.

24-hour movement and required pace:
- Fresh `api_usage_monthly` at `2026-06-19 06:03:03Z` shows `9,354` API queries, `7,899` MCP calls, and `73` active AI agents in June.
- External usage remains much weaker: `227` external API queries, `0` external MCP calls, and `48` external active agents.
- Last accepted search-success proxy is still `~90.5%`, but it remains explicitly disputed for live API truth.
- Required pace is still `~490k` more API queries, `~192k` more MCP calls, and `27` more active AI agents in the last 12 days.

Plan and adjustments being made today:
- Use `api_usage_monthly` / `query_log` as the KPI source for usage metrics.
- Keep external and total usage split visible in the CEO report.
- Follow Rich's 2026-06-18 adoption push: frictionless key registration, directory submissions, tool quality, docs, and llms.txt.
- Keep search-success proxy labeled as a proxy until the live-API dispute closes.

Five biggest failures of the day:
1. External MCP adoption is still `0`.
   Lesson learned: having a live MCP is not the same as getting external agents to use it.
2. External API queries are only `227 / 500,000`.
   Lesson learned: usage instrumentation is useful only if it leads to funnel action.
3. Active AI agents are still `48` external against a `100` target.
   Lesson learned: internal testing volume can mask a weak external user base.
4. Search success is still only defensible as a disputed proxy.
   Lesson learned: quality metrics need both accuracy and source clarity.
5. The roadmap banked count is still only `5 / 14` on the last confirmed plan.
   Lesson learned: progress on search and telemetry does not erase product roadmap debt.

Current blockers:
- [BUY-22731](/BUY/issues/BUY-22731)
- [BUY-39108](/BUY/issues/BUY-39108)

Active work in progress:
- external-agent adoption
- MCP and API discovery/distribution
- search-quality proof-path cleanup

Source of truth:
- `/usr/local/sbin/paperclip-reed-metrics.sh`
- [BUY-22731](/BUY/issues/BUY-22731) latest comments

## What Has Been Accomplished

- Oracle exceeded the 100M product goal and now reads `126.54M` on the canonical DB.
- Reed's usage metrics now have a live June 19 read with total and external splits.
- The dispatcher resilience gap exposed by the overnight Paperclip API 500s has a retry-buffer patch and retrofiled children.
- Lyra's two easiest KPI classes remain met: directories and integrations.
- The daily report cadence stayed on the approved June 30 target set and used the pinned DB, not the harness DB.

## Key Things Needed To Hit June 30 Goals

- Reconcile the public runtime catalog surface to the canonical DB under [BUY-48231](/BUY/issues/BUY-48231).
- Establish a heartbeat-safe proof path for product-backed merchants, product-side US coverage, and platforms under [BUY-32878](/BUY/issues/BUY-32878).
- Resolve Lyra's GSC, Reddit OAuth, AgentMail, and social-account blockers.
- Convert Reed's internal usage into external API and MCP adoption.
- Restore a durable uptime rollup path for Rex so the CEO report can cite 30-day uptime again.

## Board Blockers Summary

| Blocker | Why it matters | Owner |
|---|---|---|
| [BUY-22745](/BUY/issues/BUY-22745) GSC access and secret injection | Gates indexed pages and part of the visits plan | Rich / Rex |
| [BUY-31214](/BUY/issues/BUY-31214) Reddit OAuth | Gates distribution and developer-key growth | Rich |
| [BUY-41426](/BUY/issues/BUY-41426) AgentMail credential chain | Gates outreach / activation flow | Vera / Ops |
| [BUY-9086](/BUY/issues/BUY-9086), [BUY-9087](/BUY/issues/BUY-9087) social accounts | Gates visits growth | Rich |
| [BUY-51955](/BUY/issues/BUY-51955) blocked-state PATCH bug | Distorts blocker integrity across the board | Platform |

## Incidents And Execution Path

- `2026-06-19 01:00Z-04:00Z`: Paperclip API 500s blocked live child-issue filing for throughput failures; retrofilled after recovery. See [docs/buy53341_api_outage_retrofill.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy53341_api_outage_retrofill.md).
- `2026-06-19 06:01:53Z`: runtime `catalog_stats` still returned `17,472,931` products, proving the public scoreboard remains stale.
- `2026-06-19 06:03:27Z`: canonical DB proved `126,536,061` live products.
- This report is the execution artifact for [BUY-53384](/BUY/issues/BUY-53384) and is routed to Rich via the issue-document confirmation path.

## Source Inputs

- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)
- [docs/daily-product-target-shortfall-2026-06-19.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-19.md)
- [docs/daily-source-mix-plan-2026-06-19.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-19.md)
- [docs/buy53341_api_outage_retrofill.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy53341_api_outage_retrofill.md)
- [docs/buy-52309-daily-ceo-report-2026-06-17.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-52309-daily-ceo-report-2026-06-17.md)
- Live canonical DB query at `2026-06-19 06:03:27 UTC` using `psql "$(cat data/.catalog_db_url)"`
- Live `api_usage_monthly` read at `2026-06-19 06:03:03 UTC` using `/usr/local/sbin/paperclip-reed-metrics.sh`
- Live runtime probe to `https://api.buywhere.ai/v1/catalog/stats` at `2026-06-19 06:01:53Z`
