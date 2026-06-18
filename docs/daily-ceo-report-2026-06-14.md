# DAILY CEO REPORT — 2026-06-14

Report date: 2026-06-14 UTC
Finalized at: 2026-06-14T06:20:00Z
Status: final for Rich review
Issue: [BUY-48191](/BUY/issues/BUY-48191)

Manual source-of-truth notes:
- Oracle's same-day source is the canonical catalog Postgres pinned in `data/.catalog_db_url`; the closed-day `2026-06-13` verdict and the in-progress `2026-06-14` pulse come from [docs/daily-product-target-shortfall-2026-06-14.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-14.md).
- Lyra and Reed month-to-date telemetry in this report comes from live PostHog HogQL queries against project `415112`, re-run in this heartbeat at `2026-06-14 06:05 UTC`.
- Directory listings and the company-wide secrets blocker were re-verified against the Paperclip API in this heartbeat: `GET /api/companies/{companyId}/user-directory` returned `2` active entries and `GET /api/companies/{companyId}/secrets` returned `403 Board access required`.
- Indexed-pages access is still blocked in this heartbeat: `GET https://searchconsole.googleapis.com/webmasters/v3/sites?key=$GOOGLE_API_KEY` returned `401 UNAUTHENTICATED` with `API keys are not supported by this API`.
- Rex live health in this runner is from same-heartbeat synthetic checks, not UptimeRobot: `scripts/system_health_monitor.py` at `2026-06-14 06:06 UTC` measured `60.4 ms` p95 on three `/health/db` samples and all three health endpoints returned `200 OK`. The provided `UPTIMEROBOT_KEY` now returns `invalid_parameter api_key`, so fresh broad-surface uptime could not be rerun here.

## Executive Summary

- Oracle remains the dominant company mover. Closed-day `2026-06-13` was another clear `NOT A MISS`: the canonical maglev catalog added `+3,224,750` inserted rows against a required pace of `1,005,366/day`, and the current live catalog stands at approximately `85,095,847` active products, leaving `14,904,153` to reach `100M` by `2026-06-30`.
- The main same-day negative signal is that `2026-06-14` opened nearly flat. Oracle's first post-midnight interval added only `+2` inserted rows in roughly `13` minutes (`~9.3/hr`) versus the new required pace of `36,530/hr`. It is too early to call a missed day, but the day started stalled.
- Lyra's measurable surfaces improved, but only at small-company scale. Browser-side human month-to-date visits through the closed `2026-06-13` window rose to `1,619` (`+140 d/d`). Directory listings remain `2`, framework integrations remain `1`, and the exact company-wide developer-key and indexed-page KPIs remain access-blocked.
- Reed's product-usage telemetry is now materially live. Through the closed `2026-06-13` window, June month-to-date usage is `7,144` API queries (`+11 d/d`), `7,073` MCP tool calls (`+1,388 d/d`), and `145` active AI agents (`0 d/d`, still above the `100` target). The acceptance/relevance benchmark is still effectively at the floor: canonical REST `0%`, accepted MCP `2.67%`.
- Rex's immediately measurable runtime health is good on point checks but still weak on broad-surface proof. Same-heartbeat synthetic p95 on `/health/db` is `60.4 ms` and all checked health endpoints are green, but the last broad-surface uptime artifact still sits at `99.878%`, and a fresh UptimeRobot rerun is blocked in this runner by an invalid API key.

## Daily Failure Summary

1. Oracle opened `2026-06-14` with an early-day stall.
   Remediation: keep the Oracle hourly and daily shortfall checks on the live maglev `n_tup_ins` path under [BUY-24561](/BUY/issues/BUY-24561); the first stalled interval is already recorded in [docs/daily-product-target-shortfall-2026-06-14.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-14.md).
   Status: in progress.
2. Exact company-wide developer API keys are still not reportable.
   Remediation: Rex's secrets-inventory access path remains the blocker; this heartbeat reconfirmed `GET /api/companies/{companyId}/secrets -> 403 Board access required`.
   Status: blocked-on-[BUY-22421](/BUY/issues/BUY-22421).
3. Exact indexed pages are still not reportable.
   Remediation: the Search Console access path remains blocked; this heartbeat reconfirmed `401 UNAUTHENTICATED` from the Search Console API when called with the available API key.
   Status: blocked-on-[BUY-24263](/BUY/issues/BUY-24263).
4. Reed's live usage is climbing, but the product-quality benchmark is still broken.
   Remediation: keep live traffic telemetry separate from the accepted relevance benchmark and continue the search-quality follow-up chain under [BUY-37423](/BUY/issues/BUY-37423) plus the live zero-result gap work in [BUY-42533](/BUY/issues/BUY-42533).
   Status: in progress.
5. Rex broad-surface uptime could not be freshly rerun from this runner.
   Remediation: use the same-heartbeat synthetic latency and health-endpoint checks for current point health, but keep the last confirmed uptime artifact and its blocker explicit until the monitoring credential path is repaired.
   Status: blocked-on-monitoring-credential freshness under [BUY-22685](/BUY/issues/BUY-22685).

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---:|---:|---:|---|
| Active products | `85,095,847` approximate canonical DB `n_live_tup` at `2026-06-14 00:18:41 UTC`; `+3,192,437` lower-bound d/d versus the `2026-06-13 00:14:57 UTC` sample; closed-day `n_tup_ins` proof was `+3,224,750` | 100,000,000 | 14,904,153 short | [BUY-32950](/BUY/issues/BUY-32950) |
| Real merchants | `74,848` exact `count(*)`; `0 d/d` versus the prior closed-day proof in the `2026-06-13` Oracle package | 150,000 | 75,152 short | [BUY-22684](/BUY/issues/BUY-22684) |
| Developer API keys | Blocked; exact company-wide count blocked because `GET /api/companies/{companyId}/secrets` returned `403 Board access required`; runtime-visible env registrations are `30` but are not the KPI | 1,000 | Exact gap blocked | [BUY-22421](/BUY/issues/BUY-22421) |
| Indexed pages | Blocked; exact count blocked because Search Console still requires OAuth/service-account credentials and the available API key returned `401 UNAUTHENTICATED` | 50,000 | Exact gap blocked | [BUY-24263](/BUY/issues/BUY-24263) |
| Monthly visits | `1,619` browser-side human `$pageview` events through the closed `2026-06-13` UTC window; `+140 d/d` versus the closed `2026-06-12` window (`1,479`) | 25,000 | 23,381 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Directory listings | `2` exact current directory entries (`Rich`, `Board`); `0 d/d` | 25 | 23 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Framework integrations | `1` named live framework bucket (`custom`) in June-to-date `api_query` telemetry; `0 d/d` on count | 5 | 4 short | [BUY-22687](/BUY/issues/BUY-22687) |
| API queries / month | `7,144` June-to-date `api_query` events through the closed `2026-06-13` UTC window; `+11 d/d` versus the closed `2026-06-12` window (`7,133`) | 500,000 | 492,856 short | [BUY-22731](/BUY/issues/BUY-22731) |
| MCP tool calls / month | `7,073` June-to-date `mcp_tool_call` events through the closed `2026-06-13` UTC window; `+1,388 d/d` versus the closed `2026-06-12` window (`5,685`) | 200,000 | 192,927 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Search live health | `9.50%` trailing-7-day zero-result rate from real production `query_log` in the `2026-06-05 -> 2026-06-12` window; fresher same-heartbeat `query_log` pull timed out in this runner | <1% zero-result | 8.50 pp above target | [BUY-42533](/BUY/issues/BUY-42533) |
| Search relevance benchmark | `0%` canonical REST and `2.67%` accepted MCP benchmark; `0 d/d` because no newer accepted benchmark replaced the stored baseline | 85% accepted | 85 pp short on REST; 82.33 pp short on MCP | [BUY-37423](/BUY/issues/BUY-37423) |
| Active AI agents / month | `145` June-to-date unique active agents through the closed `2026-06-13` UTC window; `0 d/d` versus the closed `2026-06-12` window; already above target | 100 | 45 above target | [BUY-22731](/BUY/issues/BUY-22731) |
| Roadmap Phase 1 + 2 | `4` banked P-items last confirmed in [BUY-22731](/BUY/issues/BUY-22731#document-plan); prior-day delta unavailable from a newer accepted revision | >=9 of 14 | 5 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| API p95 latency | `60.4 ms` same-heartbeat synthetic p95 on three `/health/db` samples at `2026-06-14 06:06 UTC`; prior-day delta unavailable because the provided UptimeRobot key now returns `invalid_parameter api_key` in this runner | <100 ms | On target | [BUY-36587](/BUY/issues/BUY-36587) |
| Core uptime | Last confirmed broad-surface uptime is `99.878%` from the `2026-06-10` artifact; fresh rerun blocked in this heartbeat because the provided UptimeRobot key is invalid | >99.9% | 0.022 pp below target on the last confirmed package | [BUY-22685](/BUY/issues/BUY-22685) |

## Vera

Current focus:
- publish the dated `2026-06-14` CEO report with same-heartbeat Oracle, Lyra, Reed, and Rex evidence and route it into Rich review

24-hour movement and required pace:
- Oracle closed `2026-06-13` at `+3,224,750` inserted rows, reducing the forward product pace to `876,715/day`
- Lyra's clean browser-side monthly visits improved by `140`
- Reed's product usage improved materially on MCP tool calls and held above target on active AI agents
- Rex's point-health checks are green, but broad-surface uptime freshness is still blocked in this runner

Plan and adjustments being made today:
- keep Oracle's early-day stall visible without rewriting the closed-day `NOT A MISS` verdict
- keep Lyra's blocked KPIs explicit instead of softening them with proxy numbers
- separate Reed live traffic health from the accepted relevance benchmark
- keep Rex point-health evidence and broad-surface uptime evidence explicitly separate
- route the finished report to [@Rich](user://MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6) through the issue-document confirmation path

Five biggest failures of the day:
1. Oracle opened the new day stalled.
   Lesson learned: a strong closed day does not excuse a flat next-day open.
2. Two Lyra KPIs are still access-blocked.
   Lesson learned: repeated auth failures are still execution failures.
3. Reed's benchmarked search quality is still near zero.
   Lesson learned: usage growth and product correctness are not substitutes for each other.
4. Rex broad-surface uptime could not be freshly re-measured here.
   Lesson learned: monitoring credentials are part of the delivery path, not optional tooling.
5. The company still depends on mixed-quality evidence across lanes.
   Lesson learned: the report must say exactly which signals are live, carried, synthetic, or blocked.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-37423](/BUY/issues/BUY-37423)
- [BUY-22685](/BUY/issues/BUY-22685)

Active work in progress:
- final report publication to the `daily_ceo_report` issue document
- Rich review routing and confirmation

Source of truth:
- this report
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)

## Rex

Current focus:
- keep live runtime health inside target while recovering broad-surface proof and monitor-path credibility

24-hour movement and required pace:
- same-heartbeat synthetic `/health/db` p95 is `60.4 ms`, which is on target
- `/health/db`, `/health/redis`, and `/.well-known/api-catalog` all returned `200 OK` in this heartbeat
- the last confirmed broad-surface uptime package is still `99.878%`, below target
- a fresh UptimeRobot rerun is blocked in this runner because the provided key is invalid

Plan and adjustments being made today:
- keep the live point-health win visible
- do not overstate that point-health win into a broad-surface uptime pass
- repair or replace the blocked monitor credential path so future CEO reports can use fresh uptime artifacts

Five biggest failures of the day:
1. Broad-surface uptime freshness is blocked.
   Lesson learned: the uptime source path has to be runnable, not merely referenced.
2. The provided UptimeRobot key is invalid in this runner.
   Lesson learned: monitoring secrets require the same operational discipline as production deploy secrets.
3. Last confirmed broad-surface uptime is still below target.
   Lesson learned: green health endpoints do not erase a broader SLO miss.
4. API health evidence is now mixed-source.
   Lesson learned: point checks, probe fleets, and accepted KPI rows must stay separated.
5. Monitoring-path credibility remains fragile.
   Lesson learned: missing freshness itself is a reportable failure.

Current blockers:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-36587](/BUY/issues/BUY-36587)

Active work in progress:
- broad-surface uptime recovery
- monitoring-path repair
- runtime health validation

Source of truth:
- same-heartbeat `scripts/system_health_monitor.py` output
- [docs/daily-ceo-report-2026-06-10.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-2026-06-10.md)

## Oracle

Current focus:
- keep the maglev product-growth story canonical while surfacing the fresh early-day stall

24-hour movement and required pace:
- closed-day `2026-06-13` inserted rows: `+3,224,750`
- approximate current active products at `2026-06-14 00:18:41 UTC`: `85,095,847`
- remaining products to target: `14,904,153`
- new forward required pace: `876,715/day` or `36,530/hr`
- first `2026-06-14` interval after midnight: `+2` inserted rows in `~13` minutes (`~9.3/hr`)

Plan and adjustments being made today:
- preserve the `NOT A MISS` verdict for the closed `2026-06-13` day
- keep the early-day stall explicit so the next hourly and daily checks have the right context
- keep exact-count cost and invalid-index caveats inside the source notes instead of hiding them

Five biggest failures of the day:
1. The new day opened nearly flat.
   Lesson learned: the next hour matters even when the prior day beat pace by `3.2x`.
2. Exact product count is still too expensive to refresh in a heartbeat.
   Lesson learned: approximate live counts still need a durable exact-count remediation path.
3. Merchant growth is flat at `74,848`.
   Lesson learned: product volume alone does not close the breadth target.
4. The invalid-index / DDL-hold story is still part of the reporting path.
   Lesson learned: measurement cost remains an operational tax.
5. Oracle still carries too much of the company's visible goal movement.
   Lesson learned: company health remains over-concentrated in one lane.

Current blockers:
- [BUY-32950](/BUY/issues/BUY-32950)
- [BUY-22684](/BUY/issues/BUY-22684)

Active work in progress:
- daily shortfall and throughput proof
- product-growth tracking
- early-day stall verification

Source of truth:
- [docs/daily-product-target-shortfall-2026-06-14.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-14.md)

## Lyra

Current focus:
- grow clean human traffic and integrations while keeping blocked KPI access visible

24-hour movement and required pace:
- browser-side human monthly visits through the closed `2026-06-13` UTC window rose from `1,479` to `1,619` (`+140 d/d`)
- directory listings remain `2`
- framework integrations remain `1`
- exact company-wide developer API keys and exact indexed pages remain blocked with same-heartbeat evidence

Plan and adjustments being made today:
- keep browser-only `$pageview` as the traffic KPI
- keep blocked secret inventory and Search Console access as first-class blockers
- separate runtime-visible environment credentials from the company-wide developer-key KPI

Five biggest failures of the day:
1. Exact company-wide developer API keys are still blocked.
   Lesson learned: visible runtime env vars are not a substitute for the KPI.
2. Exact indexed pages are still blocked.
   Lesson learned: API-key-only access is not enough for Search Console.
3. Directory listings are still `2 / 25`.
   Lesson learned: top-of-funnel distribution remains shallow.
4. Framework integrations are still `1 / 5`.
   Lesson learned: the live telemetry-defined integration surface is still narrow.
5. Monthly visits are still only `1,619 / 25,000`.
   Lesson learned: clean measurement now makes the demand gap unavoidable.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22687](/BUY/issues/BUY-22687)

Active work in progress:
- traffic growth via distribution lanes
- integration growth
- KPI access remediation

Source of truth:
- same-heartbeat PostHog HogQL queries
- same-heartbeat Paperclip API directory and secrets calls
- [docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-27385-lyra-traffic-kpi-contamination-2026-05-30.md)

## Reed

Current focus:
- keep live usage telemetry current while distinguishing it from still-broken search quality

24-hour movement and required pace:
- through the closed `2026-06-13` UTC window, June MTD usage is `7,144` API queries, `7,073` MCP tool calls, and `145` active AI agents
- day-over-day movement is `+11` API queries, `+1,388` MCP tool calls, and `0` active AI agents
- live production search health is still poor on the latest direct `query_log` artifact: `9.50%` zero-result over the trailing `7` days in the `2026-06-05 -> 2026-06-12` window
- the accepted relevance benchmark remains `0%` canonical REST and `2.67%` accepted MCP

Plan and adjustments being made today:
- keep usage telemetry live and explicit
- keep the live `query_log` health row separate from the accepted benchmark row
- carry the quiet competitor-intelligence day into the product narrative without overstating it into KPI progress

Five biggest failures of the day:
1. Search benchmarked quality is still near zero.
   Lesson learned: adoption does not fix a still-broken benchmark.
2. Live production zero-result is still `9.50%`.
   Lesson learned: direct traffic evidence is now good enough to show the real gap.
3. API-query growth is still far below target pace.
   Lesson learned: a live counter is progress, not victory.
4. MCP tool calls improved sharply but are still far below target.
   Lesson learned: growth from a small base is still a small base.
5. The strategic competitor day was quiet.
   Lesson learned: a quiet market day does not create internal delivery slack.

Current blockers:
- [BUY-37423](/BUY/issues/BUY-37423)
- [BUY-42533](/BUY/issues/BUY-42533)
- [BUY-22731](/BUY/issues/BUY-22731)

Active work in progress:
- usage telemetry tracking
- search-quality improvement
- competitor-intelligence follow-through

Source of truth:
- same-heartbeat PostHog HogQL queries
- [docs/buy-42533-zero-result-gap-2026-06-12.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-42533-zero-result-gap-2026-06-12.md)
- [docs/buy-47606-daily-competitor-intel-2026-06-14.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-47606-daily-competitor-intel-2026-06-14.md)

## Source Inputs

- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)
- [docs/daily-product-target-shortfall-2026-06-14.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-14.md)
- [docs/buy-42533-zero-result-gap-2026-06-12.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-42533-zero-result-gap-2026-06-12.md)
- [docs/buy-47606-daily-competitor-intel-2026-06-14.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-47606-daily-competitor-intel-2026-06-14.md)
- same-heartbeat PostHog HogQL queries against project `415112` for `api_query`, `mcp_tool_call`, active agents, browser `$pageview`, and `agent_framework`
- same-heartbeat Paperclip API calls for `user-directory` and `secrets`
- same-heartbeat `scripts/system_health_monitor.py` output
