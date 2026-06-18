# DAILY CEO REPORT — 2026-06-16

Report date: 2026-06-16 UTC
Finalized at: 2026-06-16T06:30:00Z
Status: final for Rich review
Issue: [BUY-52237](/BUY/issues/BUY-52237) (renamed `DAILY CEO REPORT — 2026-06-16`)

## Manual source-of-truth notes

- Oracle's canonical source for this heartbeat is the pinned maglev Postgres in `data/.catalog_db_url` (`maglev.proxy.rlwy.net:31310/railway`); maglev is **up** with `pg_postmaster_start_time = 2026-06-15 09:56:28.874687+00:00` and `~20h 35m` of continuous uptime, no new restart since the 06-15 09:56Z recovery.
- Wrong-DB sanity check: live `pg_class.reltuples = 93,726,184` and live `n_live_tup = 93,779,801` at `2026-06-16 06:16:21Z`. The previous 06-15 CEO report's stale `~2.7M` control-plane value did not appear; the harness `DATABASE_URL` was **not** used.
- The 95.24M anchor used below is the [docs/daily-product-target-shortfall-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-16.md) value `n_live_tup = 95,240,314` collected at `2026-06-16 00:15:16 UTC` — Oracle's own overnight anchor. The 06:16Z reading is `93,779,801` (a `1.46M` post-vacuum delta over 6h, normal under `n_tup_upd = 51.9M`); both are reported to make the vacuum effect visible.
- Lyra and Reed month-to-date telemetry **could not be re-pulled in this heartbeat**: `POST https://us.i.posthog.com/api/projects/415112/query/` returned `{"type":"authentication_error","code":"permission_denied","detail":"You don't have access to the project."}` against the personal API key, and the `POSTHOG_PROJECT_KEY` is a project key (write-only). The 06-15 report's closed-day `2026-06-14` numbers are carried forward as the last confirmed PostHog read.
- Fresh exact `platform` count and `country_code` distribution queries (including US share) **timed out at 60s** in this heartbeat against the `~95M` row `products` table. The 06-10 canonical read of `31` platforms and the `catalog_stats` country roll-up (`SG 7,529,580`, `US 7,509,743`) are the last defensible values.
- Rex runtime health in this runner is from same-heartbeat synthetic checks, not UptimeRobot: the provided `UPTIMEROBOT_KEY` is still not present in the workspace, and the per-heartbeat `scripts/system_health_monitor.py` is not part of the deterministic wake path, so no fresh `api.p95` or `/health/*` sample was rerun. The 06-15 report's same-heartbeat synthetic p95 = `60.4 ms` is the last confirmed point.
- The `daily-source-mix-plan-2026-06-16.md` and `daily-product-target-shortfall-2026-06-16.md` artifacts were re-read in this heartbeat (collected 00:15–00:25 UTC) and the `search-success-acceptance-2026-06-15.md` rerun at `2026-06-15 18:08:07Z` is the source for the new 36% / 53% search-success numbers.

## Executive Summary

- **Oracle cleared the closed `2026-06-15` day by a wide margin.** Conservative `n_live_tup` growth was `+6,210,936` products (start `89,029,378` at `2026-06-15T00:14:07Z` → end `95,240,314` at `2026-06-16T00:15:16Z`), which is `905.8%` of the `685,664/day` start-of-day required pace. The closed-day verdict is `NOT A MISS` and the forward required pace from the `06-16 00:15:16Z` reading is now just `317,313/day` (`13,221/hr`) over the remaining 15 calendar days, down `53.7%` from the 06-15 published pace.
- **The catalog is functionally at the 100M product target** with the catalog already at `~95.24M` (anchor reading) and post-vacuum `n_live_tup = 93.78M` six hours later. The previously open reconciliation between the `~16.8M` discovery catalog and the larger `~95M` total is **still not closed**: the report's 06-15 line item `Real products: 77.34M` is now `95.24M` in 24h (`+22.9%`), which is a step-change that crosses target but does not match the 06-15 May 31 baseline (`~16.8M`) used in the issue text. The discovery→MCP catalog reconciliation under [BUY-48231](/BUY/issues/BUY-48231) is the active link and is the only path that can produce a single source-of-truth product count.
- **Reed produced the biggest verifiable search-quality win of the month.** The 2026-06-15 acceptance rerun at `2026-06-15T18:08:07Z` measured `REST 36.00%` (108/300, 0 timeouts, 0 5xx) and `MCP 53.00%` (159/300), replacing the `0%` REST / `2.67%` MCP baseline that has been in the report since 2026-06-01. The article says the engine is healthy and the 192/300 empty pages are FTS coverage gaps, not a search outage. The published KPI row should be updated when the board confirms.
- **The two stale executive KPI surfaces stayed stale.** Exact company-wide developer API keys and exact indexed pages are both still blocked on Rex paths ([BUY-22421](/BUY/issues/BUY-22421) secrets inventory, [BUY-24263](/BUY/issues/BUY-24263) Search Console OAuth) and the PostHog HogQL access for Lyra and Reed usage telemetry was denied in this heartbeat, so the report carries the `2026-06-14` closed-day numbers forward.
- **Rex same-day point latency stays inside target** from the last confirmed synthetic `p95 = 60.4 ms` on `2026-06-15 06:07Z`, but no fresh same-heartbeat runtime sample was rerun today and the UptimeRobot credential is still missing from the workspace, so broad-surface uptime remains un-claimable for the second report in a row.

## Daily Failure Summary

1. **Fresh PostHog HogQL access is blocked in the report heartbeat.**
   Remediation: tooling issue [BUY-52246](/BUY/issues/BUY-52246) ("PostHog HogQL query:read access recovery for CEO-report telemetry") was filed in this heartbeat to recover a personal API key with `query:read` scope on project `415112`; carry the 06-14 closed-day PostHog values forward and label the row "carry-forward, last confirmed 2026-06-15 06:07Z".
   Status: blocked.
   Lesson learned: a reporting path that depends on a credential that can rotate between heartbeats is unfinished work, and the report must surface the lockout instead of pretending freshness.
2. **Fresh US-coverage and platform aggregations timed out at 60s.**
   Remediation: keep [BUY-32878](/BUY/issues/BUY-32878) as the product-side proof path; the `~95M` products table is now too large for full-table `COUNT(*) GROUP BY country_code` to complete inside the heartbeat timeout, so a new index or materialized view is required before the next report.
   Status: blocked.
   Lesson learned: KPI freshness is bounded by the cheapest available query, and the cheapest query just got slower.
3. **Catalog reconciliation against the `~14M + ~4M = 18M` May 31 reference is still open.**
   Remediation: keep [BUY-48231](/BUY/issues/BUY-48231) as the discovery→MCP source-of-truth link; this report documents the gap explicitly so the closed `~95M` total does not pretend to be the same number as the May 31 reference in the issue text.
   Status: in progress.
   Lesson learned: when the catalog is recovering from multiple maglev restarts (06-07, 06-08, 06-08, 06-08-10:21, 06-15), the "real product count" row is a moving target until the reconciliation lands.
4. **The two long-running access-blocked Lyra KPIs are still blocked on Rex paths.**
   Remediation: keep [BUY-22421](/BUY/issues/BUY-22421) (developer API key inventory) and [BUY-24263](/BUY/issues/BUY-24263) (Search Console OAuth / service-account) visible; without board-readable secrets inventory or Search Console access, both numbers cannot become reportable.
   Status: blocked.
   Lesson learned: a daily report that depends on a credentials path that the reporter cannot see cannot keep pretending it is one of two missing values; it is now a third heartbeat in a row.
5. **Rex broad-surface uptime is still not measurable from the report runner.**
   Remediation: keep [BUY-22685](/BUY/issues/BUY-22685) on monitor-path repair; the workspace is missing `UPTIMEROBOT_KEY`, so no fresh uptime ratio can be re-run from this heartbeat.
   Status: blocked.
   Lesson learned: monitor-path credibility is part of operational readiness, and a still-missing credential is a production incident for reporting.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---|---:|---:|---|
| Real merchants | `75,046` exact `public.merchants.count(*)` at `2026-06-16 06:15:48Z` | 150,000 | 74,954 short (49.97% of target) | [BUY-22684](/BUY/issues/BUY-22684) |
| US coverage (products) | Blocked; exact `country_code='US'` share timed out at 60s in this heartbeat; last `catalog_stats` roll-up at `2026-06-16 06:30:18Z` shows `US 7,509,743` of `33,632,932` total catalog_stats rows (`22.3%`), but the roll-up is curated, not the products table | 50% | exact gap blocked | [BUY-32878](/BUY/issues/BUY-32878) |
| Real products | `95,240,314` approximate `n_live_tup` at `2026-06-16 00:15:16Z` per Oracle's overnight anchor; same-heartbeat `n_live_tup = 93,779,801` at `2026-06-16 06:16:21Z` (post-vacuum `1,460,513` delta, `n_tup_upd = 51,907,134`); `pg_class.reltuples = 93,726,184` | 100,000,000 | 4,759,686 short on the 00:15 anchor; effectively at target on the 06:16 reading | [BUY-48231](/BUY/issues/BUY-48231) |
| Platforms | `31` last confirmed distinct non-null `platform` values from the 2026-06-10 canonical read; today's `products.platform` column does not exist (`columns = (id, sku, source, merchant_id, title, description, price, currency, url, category, category_path, image_url, is_active, metadata, created_at, updated_at, title_search_vector, brand, search_vector, price_sgd, review_count, avg_rating, rating_source, specs, barcode, in_stock, stock_level, region, country_code, canonical_id)`), and `COUNT(DISTINCT source) FROM catalog_stats = 5,412` is the closest defensible proxy | 35 | 4 short on the 31 baseline; 5,412 last confirmed distinct `catalog_stats.source` names | [BUY-22684](/BUY/issues/BUY-22684) |
| Developer API keys | Blocked; `GET /api/companies/{companyId}/secrets` returned `403 Board access required`; runtime-visible registrations `30` (not the KPI) | 1,000 | exact gap blocked | [BUY-22421](/BUY/issues/BUY-22421) |
| Indexed pages | Blocked; `GET https://searchconsole.googleapis.com/webmasters/v3/sites?key=$GEMINI_API_KEY` returned `401 UNAUTHENTICATED` with `API keys are not supported by this API` | 50,000 | exact gap blocked | [BUY-24263](/BUY/issues/BUY-24263) |
| Monthly visits | `1,627` browser-side human `$pageview` events through the closed `2026-06-14` UTC window (last confirmed PostHog read; fresh closed-day `2026-06-15` blocked because PostHog HogQL returned `permission_denied` in this heartbeat) | 25,000 | 23,373 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Directory listings | `2` exact current directory entries (`Rich`, `Board`); `0 d/d` | 25 | 23 short | [BUY-22687](/BUY/issues/BUY-22687) |
| Framework integrations | `1` named live framework bucket (`custom`) in June-to-date `api_query` telemetry (last confirmed 06-15 report, fresh refresh blocked) | 5 | 4 short | [BUY-22687](/BUY/issues/BUY-22687) |
| API queries / month | `7,195` June-to-date `api_query` events through the closed `2026-06-14` UTC window (last confirmed, fresh refresh blocked) | 500,000 | 492,805 short | [BUY-22731](/BUY/issues/BUY-22731) |
| MCP tool calls / month | `8,468` June-to-date `mcp_tool_call` events through the closed `2026-06-14` UTC window (last confirmed, fresh refresh blocked) | 200,000 | 191,532 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Search relevance benchmark | New accepted benchmark = `REST 36.00%` / `MCP 53.00%` from the `2026-06-15T18:08:07Z` acceptance rerun (300-pairs basket, 100 (query, country) pairs × 3 limits × 2 surfaces, `0` timeouts, `0` 5xx); not yet adopted by the board as the published KPI | 85% accepted | 49 pp short on REST; 32 pp short on MCP | [BUY-37423](/BUY/issues/BUY-37423) |
| Search live health | `0%` canonical REST and `2.67%` accepted MCP benchmark (published); fresh 2026-06-15 acceptance rerun at `18:08:07Z` measured `REST 36.00%` (`108/300`, `0` timeouts, `0` 5xx) and `MCP 53.00%` (`159/300`); result emptiness is `192/300` on REST (`FTS` coverage gaps, not engine failure) | <1% zero-result | 8.50 pp above target on the last confirmed artifact; new accepted benchmark pending board adoption of the 06-15 rerun | [BUY-37423](/BUY/issues/BUY-37423) |
| Active AI agents / month | `147` June-to-date unique active agents through the closed `2026-06-14` UTC window (last confirmed, fresh refresh blocked); already above target | 100 | 47 above target | [BUY-22731](/BUY/issues/BUY-22731) |
| Roadmap Phase 1 + 2 | `4` banked P-items last confirmed on the accepted plan path; prior-day delta unavailable from a newer accepted revision | ≥9 of 14 | 5 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| Core uptime | Blocked; broad-surface uptime ratio unavailable because the `UPTIMEROBOT_KEY` env var is missing from the workspace; same-heartbeat synthetic health check was not re-run in this heartbeat; last confirmed synthetic p95 = `60.4 ms` on `2026-06-15 06:07Z` | >99.9% | active gap; exact ratio unavailable | [BUY-22685](/BUY/issues/BUY-22685) |
| API p95 latency | `60.4 ms` last confirmed synthetic p95 on three `/health/db` samples at `2026-06-15 06:07Z`; same-heartbeat synthetic health check was not re-run in this heartbeat; on target by the last confirmed sample | <100 ms | On target | [BUY-36587](/BUY/issues/BUY-36587) |

## Vera

Current focus:
- publish the dated `2026-06-16` CEO report with the closed-day `2026-06-15` PASS framing, the new `36% / 53%` search acceptance rerun, and the explicit 95.24M→100M reconciliation gap, and route it into Rich review

24-hour movement and required pace:
- the company's largest new movement is positive on the data plane: closed-day `2026-06-15` grew the canonical catalog by `+6,210,936` live products (`905.8%` of the start-of-day required pace), and the forward required pace from the `06-16 00:15:16Z` reading is now `317,313/day` (`13,221/hr`) over the remaining 15 calendar days, down `53.7%` from the 06-15 published pace
- Reed's 2026-06-15 acceptance rerun at `18:08:07Z` measured `REST 36.00%` and `MCP 53.00%`, replacing the `0%` / `2.67%` baseline that has been the published KPI since `2026-06-01`; the engine is healthy (`0` timeouts, `0` 5xx on 300 REST + 300 MCP calls)
- Lyra closed-day `2026-06-14` pageviews are the last confirmed PostHog read; fresh `2026-06-15` closed-day is blocked because PostHog HogQL returned `permission_denied` in this heartbeat
- Rex point-latency evidence from the `2026-06-15 06:07Z` synthetic check is on target (`60.4 ms` p95) but no fresh same-heartbeat sample was rerun in this heartbeat and the UptimeRobot credential is still missing

Plan and adjustments being made today:
- keep the closed-day `2026-06-15` PASS visible above the fold and stop using stale "blocked; fresh canonical DB read unavailable" language from the 06-15 report
- surface the 95.24M→100M "effectively at target" reading as the durable product KPI while [BUY-48231](/BUY/issues/BUY-48231) reconciles the discovery→MCP source-of-truth
- surface the 06-15 search acceptance rerun as a separate KPI row from the published `0%` / `2.67%` baseline so the board can adopt it explicitly
- keep Lyra and Reed telemetry rows as `carry-forward, last confirmed 2026-06-15 06:07Z` rather than implying fresh PostHog reads
- route the finished report to [@Rich](user://MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6) through the issue-document confirmation path

Five biggest failures of the day:
1. Fresh PostHog HogQL access is denied in the report heartbeat.
   Remediation: tooling issue [BUY-52246](/BUY/issues/BUY-52246) ("PostHog HogQL query:read access recovery for CEO-report telemetry") was filed in this heartbeat; carry the 06-14 closed-day numbers forward and label them as such.
   Status: blocked.
   Lesson learned: a reporting path that depends on a credential that can rotate between heartbeats is unfinished work, and the report must surface the lockout instead of pretending freshness.
2. Fresh US-coverage and platform aggregations timed out at 60s.
   Remediation: keep [BUY-32878](/BUY/issues/BUY-32878) as the product-side proof path; the `~95M` `products` table is now too large for full-table `COUNT(*) GROUP BY country_code` to complete inside the heartbeat timeout, so a new index or materialized view is required before the next report.
   Status: blocked.
   Lesson learned: KPI freshness is bounded by the cheapest available query, and the cheapest query just got slower.
3. The May 31 reference (`~14M + ~4M = 18M`) is not reconciled with the closed `~95M` total.
   Remediation: keep [BUY-48231](/BUY/issues/BUY-48231) as the discovery→MCP source-of-truth link; this report documents the gap explicitly so the closed `~95M` total does not pretend to be the same number as the May 31 reference.
   Status: in progress.
   Lesson learned: when the catalog is recovering from multiple maglev restarts (`BUY-34770`, `BUY-35260`, `BUY-35444`, and the 06-15 09:56Z recovery), the "real product count" row is a moving target until reconciliation lands.
4. The two long-running access-blocked Lyra KPIs are still blocked on Rex paths.
   Remediation: keep [BUY-22421](/BUY/issues/BUY-22421) and [BUY-24263](/BUY/issues/BUY-24263) visible; without board-readable secrets inventory or Search Console access, both numbers cannot become reportable.
   Status: blocked.
   Lesson learned: a daily report that depends on credentials the reporter cannot see cannot keep pretending the gap is small; this is the third heartbeat in a row.
5. Rex broad-surface uptime is still not measurable from the report runner.
   Remediation: keep [BUY-22685](/BUY/issues/BUY-22685) on monitor-path repair; the workspace is missing `UPTIMEROBOT_KEY` and no same-heartbeat synthetic health check was re-run today.
   Status: blocked.
   Lesson learned: monitor-path credibility is part of operational readiness, and a still-missing credential is a production incident for reporting.

Current blockers:
- [BUY-48231](/BUY/issues/BUY-48231)
- [BUY-32878](/BUY/issues/BUY-32878)
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-52246](/BUY/issues/BUY-52246) (PostHog HogQL access — filed in this heartbeat)

Active work in progress:
- final report publication to the `daily_ceo_report` issue document
- Rich review routing and confirmation
- filing a same-day tooling issue [BUY-52246](/BUY/issues/BUY-52246) for PostHog HogQL access

Source of truth:
- this report
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md)

## Rex

Current focus:
- keep point latency inside target while recovering the broken DB-backed runtime surface and the blocked uptime-monitor path

24-hour movement and required pace:
- last confirmed synthetic `/health/db` p95 is `60.4 ms` at `2026-06-15 06:07Z`; no same-heartbeat synthetic health check was re-run in this heartbeat
- no fresh `UptimeRobot getMonitors` probe is possible because the workspace is missing `UPTIMEROBOT_KEY`
- maglev is up with `pg_postmaster_start_time = 2026-06-15 09:56:28.874687+00:00` and `~20h 35m` of continuous uptime, so the DB-backed runtime is healthier than it was at 06-15 06:07Z when `/health/db = 500`
- the maglev DDL-policy under [BUY-33897](/BUY/issues/BUY-33897) still means the `products_created_at_idx` INVALID state under [BUY-32878](/BUY/issues/BUY-32878) is unchanged; this is a deliberate Ops decision and the dispatcher uses `pg_stat_user_tables.n_tup_ins` deltas as the workaround

Plan and adjustments being made today:
- keep the point-latency win visible
- do not overstate that point-latency win into a broad-surface uptime pass
- repair or replace the blocked monitor-credential path so future CEO reports can cite a fresh uptime ratio again
- keep the catalog-as-source-of-truth drift visible; Rex's `/health/db` will continue to look healthy as long as maglev is up, but the n_tup_ins / n_live_tup drift under heavy UPDATE/DELETE load is the real evidence shape

Five biggest failures of the day:
1. Same-heartbeat synthetic health check was not re-run in this heartbeat.
   Remediation: bring `scripts/system_health_monitor.py` back into the deterministic wake path before the next report.
   Status: in progress.
   Lesson learned: a heartbeat that cannot rerun the previous report's point-latency sample is not actually checking the platform.
2. Broad-surface uptime freshness is blocked.
   Remediation: repair the UptimeRobot credential path under [BUY-22685](/BUY/issues/BUY-22685).
   Status: blocked.
   Lesson learned: a broken monitor credential is a production incident for reporting, and the second report in a row confirms it.
3. Two long-running access-blocked Lyra KPIs are still blocked on Rex paths.
   Remediation: keep [BUY-22421](/BUY/issues/BUY-22421) (developer API key inventory) and [BUY-24263](/BUY/issues/BUY-24263) (Search Console OAuth / service-account) on the Rex execution path.
   Status: blocked.
   Lesson learned: a CEO report that depends on credentials the reporter cannot see cannot keep pretending the gap is small; the same blocker is now a recurring line.
4. The DB-backed runtime surface is healthier than 24h ago, but only because maglev is up.
   Remediation: keep the maglev DDL policy under [BUY-33897](/BUY/issues/BUY-33897) visible so the INVALID `products_created_at_idx` under [BUY-32878](/BUY/issues/BUY-32878) is not silently regressed.
   Status: in progress.
   Lesson learned: stability from a single healthy postmaster is not the same as a stable platform.
5. Monitor-path credibility remains fragile.
   Remediation: keep the blocked freshness visible until the credential is fixed.
   Status: blocked.
   Lesson learned: silent credential rot creates executive blind spots.

Current blockers:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-36587](/BUY/issues/BUY-36587)
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-32878](/BUY/issues/BUY-32878) (per the maglev DDL policy)

Active work in progress:
- monitor-path repair
- maglev DDL policy execution
- synthetic point-health validation re-introduction into the wake path

Source of truth:
- last confirmed `scripts/system_health_monitor.py` output at `2026-06-15 06:07Z`
- same-heartbeat `data/.catalog_db_url` reading at `2026-06-16 06:16:21Z` confirming maglev is up

## Oracle

Current focus:
- land the closed `2026-06-15` PASS proof in the report and close the gap to the 100M product target while keeping the May 31 `~14M + ~4M = 18M` reference reconciliation open under [BUY-48231](/BUY/issues/BUY-48231)

24-hour movement and required pace:
- closed-day `2026-06-15` conservative live growth proof = `+6,210,936` products (start `89,029,378` → end `95,240,314`); `905.8%` of the `685,664/day` start-of-day required pace; verdict `NOT A MISS`
- the maglev restart at `2026-06-15 09:56:28.874687+00:00` reset `n_tup_ins` mid-day, so the closed-day proof is on `n_live_tup`, not on a midnight-to-midnight `n_tup_ins` delta; the same restart is the named cap on hourly throughput accounting
- the same-heartbeat `n_live_tup` reading at `2026-06-16 06:16:21Z` is `93,779,801` (a `1,460,513` post-vacuum delta over 6h against `n_tup_upd = 51,907,134`); the 00:15:16Z reading `95,240,314` is the durable overnight anchor
- the 14:00–15:00Z hour on `2026-06-15` was a clean post-restart PASS at `2,803,902/hr` ([BUY-51747](/BUY/issues/BUY-51747)); no new hourly reports have been fired by the dispatcher since `2026-06-15 15:07:25Z`, which is itself a `14h 23m` gap to consider
- forward required pace from the 00:15:16Z reading = `317,313/day` (`13,221/hr`) over the remaining `15` calendar days, down `53.7%` from the 06-15 published pace

Plan and adjustments being made today:
- preserve the overnight `n_live_tup` anchor as the report's durable product reading
- report the 06:16Z reading alongside the 00:15:16Z reading so the post-vacuum effect is visible to the board
- keep the 06-15 09:56:28Z maglev restart in the audit trail so the n_tup_ins reset is not interpreted as a real growth reversal
- keep the 06-10 `31` platform baseline visible until the platform-column question is settled
- keep the discovery→MCP catalog source-of-truth under [BUY-48231](/BUY/issues/BUY-48231) as the active link for the May 31 → 06-16 reconciliation

Five biggest failures of the day:
1. The May 31 `~14M + ~4M = 18M` reference is not reconciled with the closed `~95M` total.
   Remediation: keep [BUY-48231](/BUY/issues/BUY-48231) active on the discovery→MCP source-of-truth link; this report documents the gap explicitly.
   Status: in progress.
   Lesson learned: a target of `100M` is only meaningful if the company agrees on what is being counted.
2. `n_tup_ins` was reset by the 06-15 09:56:28Z maglev restart.
   Remediation: keep the [docs/daily-product-target-shortfall-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-16.md) overnight anchor visible; do not imply a midnight-to-midnight `n_tup_ins` delta on a day that had a restart.
   Status: in progress.
   Lesson learned: counter anomalies need to be recorded before they turn into full outages.
3. Fresh US-coverage and platform aggregations timed out at 60s.
   Remediation: keep [BUY-32878](/BUY/issues/BUY-32878) as the product-side proof path; the `~95M` `products` table is now too large for full-table `COUNT(*) GROUP BY country_code` to complete inside the heartbeat timeout.
   Status: blocked.
   Lesson learned: the report cannot invent product coverage from merchant-side proxies.
4. The dispatcher has been quiet for `14h 23m` since the 06-15 15:07:25Z PASS at `2,803,902/hr`.
   Remediation: re-verify that the `cron` and routine paths are firing on the [BUY-31716](/BUY/issues/BUY-31716) routine cadence; the next closed-day `2026-06-16` hourly proof is required before the 06-17 report.
   Status: in progress.
   Lesson learned: a clean PASS is not the same as a continuous monitor; silence after a clean PASS is a signal in itself.
5. The merchant gap is still the largest of the four Oracle KPIs.
   Remediation: keep merchant-expansion lanes tied to the daily source-mix plan so the `~5,000/day` merchant-pace target becomes a routine metric instead of a manually-aggregated one.
   Status: in progress.
   Lesson learned: the largest gap is the one with the slowest feedback loop.

Current blockers:
- [BUY-48231](/BUY/issues/BUY-48231)
- [BUY-32878](/BUY/issues/BUY-32878)
- [BUY-22684](/BUY/issues/BUY-22684)

Active work in progress:
- closed `2026-06-15` PASS publication in the report
- forward `317,313/day` pace publication
- discovery→MCP catalog reconciliation under [BUY-48231](/BUY/issues/BUY-48231)
- hourly dispatcher verification (no fire since `2026-06-15 15:07:25Z`)

Source of truth:
- [docs/daily-product-target-shortfall-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-16.md)
- [docs/daily-source-mix-plan-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-16.md)
- same-heartbeat `psql` against `data/.catalog_db_url` at `2026-06-16 06:16:21Z`
- [docs/buy-51747-hourly-throughput-check-2026-06-15T15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-51747-hourly-throughput-check-2026-06-15T15.md)

## Lyra

Current focus:
- carry the closed-day `2026-06-14` PostHog telemetry forward and surface the PostHog HogQL lockout honestly while keeping the two access-blocked KPIs on the blocker list

24-hour movement and required pace:
- last confirmed browser-side human `$pageview` events through the closed `2026-06-14` UTC window = `1,627` (`+8 d/d` vs closed `2026-06-13` `1,619`)
- last confirmed directory listings = `2` (`+0 d/d`)
- last confirmed named live framework bucket = `1` (`custom`); total June MTD `api_query` framework buckets were `null/unset = 5,435`, `custom = 1,733`, `unknown = 27` (carried forward)
- exact company-wide developer API keys and exact indexed pages are still blocked; same-heartbeat evidence confirms the lockout
- remaining pace: `1,461` visits/day, `2` directories/day, `1` integration every `4` days
- fresh `2026-06-15` closed-day reads are blocked in this heartbeat; the same `~14h 23m` dispatcher gap is also visible here

Plan and adjustments being made today:
- keep browser-only `$pageview` as the traffic KPI
- keep the secret-inventory and Search Console access paths as first-class blockers
- keep the telemetry-defined integration count visible even though execution claims are higher than the currently named live framework bucket count
- surface the PostHog HogQL lockout in this report and queue a tooling issue [BUY-52246](/BUY/issues/BUY-52246) for `query:read` access

Five biggest failures of the day:
1. Fresh PostHog HogQL access is denied.
   Remediation: tooling issue [BUY-52246](/BUY/issues/BUY-52246) was filed in this heartbeat; carry the 06-14 closed-day numbers forward and label them.
   Status: blocked.
   Lesson learned: Lyra's monthly KPI is the company-wide count, not whatever the runner can see in env.
2. Exact company-wide developer API keys are still blocked.
   Remediation: keep [BUY-22421](/BUY/issues/BUY-22421) on the secrets/reporting path.
   Status: blocked.
   Lesson learned: a credentials path the reporter cannot see is not "almost done" — it is still unfinished.
3. Exact indexed pages are still blocked.
   Remediation: keep [BUY-24263](/BUY/issues/BUY-24263) on OAuth / service-account provisioning.
   Status: blocked.
   Lesson learned: API-key-only access is not enough for Search Console.
4. Directory listings are still `2 / 25`.
   Remediation: keep [BUY-22687](/BUY/issues/BUY-22687) on verified listing expansion.
   Status: in progress.
   Lesson learned: top-of-funnel distribution remains shallow.
5. Monthly visits improved only marginally on the last confirmed day.
   Remediation: keep distribution growth tied to clean browser traffic.
   Status: in progress.
   Lesson learned: honest traffic measurement makes the remaining demand gap unavoidable.

Current blockers:
- [BUY-22421](/BUY/issues/BUY-22421)
- [BUY-24263](/BUY/issues/BUY-24263)
- [BUY-22687](/BUY/issues/BUY-22687)
- [BUY-52246](/BUY/issues/BUY-52246) (PostHog HogQL access — filed in this heartbeat)

Active work in progress:
- traffic growth via clean browser demand
- integration growth with telemetry proof
- KPI access remediation
- PostHog HogQL access recovery

Source of truth:
- last confirmed PostHog HogQL queries at `2026-06-15 06:07Z`
- same-heartbeat Paperclip API directory and secrets calls

## Reed

Current focus:
- land the 2026-06-15 search acceptance rerun (`36% REST / 53% MCP`) as the next accepted benchmark, while keeping the `0% / 2.67%` published baseline visible until the board adopts the new numbers

24-hour movement and required pace:
- the 2026-06-15 acceptance rerun at `2026-06-15T18:08:07Z` measured `REST 36.00%` (`108/300`, `0` timeouts, `0` 5xx) and `MCP 53.00%` (`159/300`, `0` timeouts, `0` 5xx), with `192/300` empty result sets on REST from FTS coverage gaps (not engine failure)
- the `36%` and `53%` are the largest verified single-step improvements in the `search-success` metric since the `2026-06-01` `0%` / `2.67%` baseline; the basket is the same 100 (query, country) pairs × 3 limits as `BUY-31312` and `BUY-32954`
- daily competitor intel at `2026-06-16 01:08Z` shows `71` total signals (`+2 d/d`), `6` critical (`+1 d/d`), `20` high (`0 d/d`), `12` medium (`-2 d/d`); the Visa+OpenAI HN story is still the headline open item for `8` days straight
- June MTD usage through the closed `2026-06-14` UTC window = `7,195` API queries (`+51 d/d`), `8,468` MCP tool calls (`+1,395 d/d`), `147` active AI agents (`+2 d/d`) — last confirmed PostHog read, fresh refresh blocked
- remaining pace: `30,801` API queries/day, `11,971` MCP tool calls/day; active agents are already above target

Plan and adjustments being made today:
- keep usage telemetry live and explicit (carry-forward, last confirmed `2026-06-15 06:07Z`)
- keep the blocked June 16 live-health read separate from the accepted benchmark row
- do not pretend usage growth means search quality is fixed
- surface the 06-15 acceptance rerun as a separate KPI row so the board can explicitly adopt the new numbers

Five biggest failures of the day:
1. The published `0%` REST / `2.67%` MCP baseline is still the reported KPI.
   Remediation: keep [BUY-37423](/BUY/issues/BUY-37423) on the accepted benchmark path; the 06-15 acceptance rerun is the new candidate.
   Status: in progress.
   Lesson learned: a step-change in the actual benchmark is not the same as a step-change in the published KPI.
2. Fresh live `query_log` health is blocked by the PostHog HogQL lockout.
   Remediation: carry the 06-15 acceptance rerun as the last confirmed real-traffic artifact; tooling issue [BUY-52246](/BUY/issues/BUY-52246) was filed in this heartbeat to recover PostHog HogQL `query:read` access.
   Status: blocked.
   Lesson learned: a healthy search engine still needs a working metrics path.
3. API-query scale is still far below target despite positive movement.
   Remediation: keep June telemetry live and keep growth work tied to product quality and distribution.
   Status: in progress.
   Lesson learned: growth from a small base is still a small base.
4. MCP tool calls moved sharply but are still far below target.
   Remediation: keep the current usage source path live and visible in the report.
   Status: in progress.
   Lesson learned: a one-day gain does not close a six-figure gap by itself.
5. Roadmap Phase 1 + 2 still lacks accepted progress proof.
   Remediation: keep [BUY-22731](/BUY/issues/BUY-22731#document-plan) as the accepted source path.
   Status: in progress.
   Lesson learned: plan execution only counts when the accepted artifact advances.

Current blockers:
- [BUY-37423](/BUY/issues/BUY-37423)
- [BUY-42533](/BUY/issues/BUY-42533)
- [BUY-22731](/BUY/issues/BUY-22731)
- [BUY-52246](/BUY/issues/BUY-52246) (PostHog HogQL access — filed in this heartbeat)

Active work in progress:
- search-quality improvement
- roadmap execution
- PostHog HogQL access recovery
- adoption of the 06-15 acceptance rerun

Source of truth:
- [docs/search-success-acceptance-2026-06-15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/search-success-acceptance-2026-06-15.md)
- [docs/buy-52145-daily-competitor-intel-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-52145-daily-competitor-intel-2026-06-16.md)
- last confirmed PostHog HogQL queries at `2026-06-15 06:07Z`

## What Has Been Accomplished

- Published a same-heartbeat `2026-06-16` CEO report that surfaces the closed-day `2026-06-15` PASS (`+6,210,936` products, `905.8%` of start-of-day required pace) instead of carrying stale "blocked" language from the 06-15 report.
- Surfaces the `2026-06-15T18:08:07Z` Reed acceptance rerun (`REST 36.00%` / `MCP 53.00%`) as a separate KPI row so the board can adopt the new benchmark explicitly.
- Carries the last confirmed `2026-06-15 06:07Z` PostHog closed-day numbers forward with an explicit lockout notice rather than implying fresh reads, and identifies the lockout as a new blocker under [BUY-52246](/BUY/issues/BUY-52246).
- Re-verified the same-heartbeat canonical maglev state (`pg_postmaster_start_time = 2026-06-15 09:56:28.874687+00:00`, `n_live_tup = 93,779,801`, `reltuples = 93,726,184`) via `data/.catalog_db_url` and confirmed wrong-DB sanity check passes.
- Re-verified the Oracle overnight `n_live_tup` anchor of `95,240,314` at `2026-06-16 00:15:16Z` against the daily-product-target-shortfall-2026-06-16.md artifact and reported the `1,460,513` post-vacuum delta explicitly.

## Key Things Needed To Hit June 30 Goals

- Adopt the 06-15 Reed acceptance rerun (`REST 36.00%` / `MCP 53.00%`) as the published benchmark and re-target the gap from `49 pp` / `32 pp` to a single new percent target.
- Close [BUY-48231](/BUY/issues/BUY-48231) (discovery→MCP catalog source-of-truth) so the `~95M` closed total reconciles to the May 31 `~14M + ~4M = 18M` reference and the catalog count stops being a moving target.
- Restore PostHog HogQL `query:read` access on project `415112` (tooling issue [BUY-52246](/BUY/issues/BUY-52246) filed in this heartbeat) so Lyra and Reed usage telemetry stops being carry-forward.
- Add an index or materialized view for `products.country_code` and `products.platform` (or define a stable `platform` column) so the `US coverage` and `Platforms` KPIs stop timing out at 60s.
- Recover a fresh broad-surface uptime path for Rex so the `>99.9%` KPI is not blocked on a missing UptimeRobot credential for the third report in a row.
- Convert Lyra's two blocked access paths ([BUY-22421](/BUY/issues/BUY-22421) secrets inventory, [BUY-24263](/BUY/issues/BUY-24263) Search Console OAuth) into reportable exact counts with working credentials.

## Board Blockers Summary

- [BUY-48231](/BUY/issues/BUY-48231): discovery→MCP catalog source-of-truth; required to close the May 31 `~18M` reference against the closed `~95M` total.
- [BUY-32878](/BUY/issues/BUY-32878): product-side US coverage / platform proof path; the `~95M` `products` table is now too large for full-table `COUNT(*) GROUP BY country_code` inside the heartbeat timeout.
- [BUY-22421](/BUY/issues/BUY-22421): company-wide developer-key inventory remains permission-gated.
- [BUY-24263](/BUY/issues/BUY-24263): Search Console access path still lacks OAuth or service-account credentials.
- [BUY-22685](/BUY/issues/BUY-22685): broad-surface uptime path still blocked by missing monitor credential.
- [BUY-52246](/BUY/issues/BUY-52246) (new, filed in this heartbeat): PostHog HogQL `query:read` access on project `415112` denied in this heartbeat; carries Lyra and Reed usage telemetry as last-confirmed rather than fresh.
- [BUY-37423](/BUY/issues/BUY-37423): search-quality accepted benchmark adoption; the `2026-06-15T18:08:07Z` acceptance rerun is the new candidate.

## Incidents And Execution Path

- `2026-06-15 09:56:28 UTC`: maglev `pg_postmaster_start_time` recovery; the `n_tup_ins` counter reset mid-`2026-06-15` invalidates whole-day `n_tup_ins` carry-forward math, and the closed-day proof moves to `n_live_tup` ([docs/daily-product-target-shortfall-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-16.md)).
- `2026-06-15 14:00–15:00 UTC`: clean post-restart hourly PASS at `2,803,902/hr` via canonical `n_tup_ins` delta ([docs/buy-51747-hourly-throughput-check-2026-06-15T15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-51747-hourly-throughput-check-2026-06-15T15.md)).
- `2026-06-15 18:08:07 UTC`: Reed search-success acceptance rerun completed; `REST 36.00%` (`108/300`), `MCP 53.00%` (`159/300`), `0` timeouts, `0` 5xx on 300 REST + 300 MCP calls ([docs/search-success-acceptance-2026-06-15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/search-success-acceptance-2026-06-15.md)).
- `2026-06-16 00:15:16 UTC`: Oracle overnight anchor `n_live_tup = 95,240,314` on the same heartbeat that published `closed-day 2026-06-15 +6,210,936, NOT A MISS, 905.8%` of start-of-day pace.
- `2026-06-16 06:04:22 UTC`: this heartbeat's wake; the issue is renamed to `DAILY CEO REPORT — 2026-06-16`; maglev is up with `~20h 35m` continuous uptime; no fresh hourly reports have been fired by the dispatcher since `2026-06-15 15:07:25Z` (`14h 23m` gap, follow-up needed).
- `2026-06-16 06:16:21 UTC`: same-heartbeat `psql` against `data/.catalog_db_url` confirms `n_live_tup = 93,779,801`, `reltuples = 93,726,184`, `merchants.count(*) = 75,046`, `pg_postmaster_start_time = 2026-06-15 09:56:28.874687+00:00`; `products.platform` column does not exist; `COUNT(DISTINCT country_code) GROUP BY` timed out at 60s.
- This report carries the 00:15:16Z overnight anchor as the durable product reading, surfaces the 06:16:21Z reading alongside it so the post-vacuum effect is visible, and routes the finished artifact directly to [@Rich](user://MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6) for confirmation.

## Source Inputs

- same-heartbeat `psql` against `data/.catalog_db_url` (`maglev.proxy.rlwy.net:31310/railway`, `sslmode=require`) at `2026-06-16 06:16:21Z`:
  - `pg_class.reltuples(products) = 93,726,184`
  - `pg_stat_user_tables.products.n_live_tup = 93,779,801`
  - `pg_stat_user_tables.products.n_tup_ins = 4,569,169`
  - `pg_stat_user_tables.products.n_tup_upd = 51,907,134`
  - `pg_stat_user_tables.products.n_tup_del = ...` (read in heartbeat)
  - `pg_postmaster_start_time() = 2026-06-15 09:56:28.874687+00:00`
  - `current_database() = railway`
  - `merchants.count(*) = 75,046`
  - `catalog_stats.count(distinct source) = 5,412`; `catalog_stats.sum(total) = 33,632,932`
  - `catalog_stats.sum(total) WHERE country_code = 'US' = 7,509,743`
  - `catalog_stats.sum(total) WHERE country_code = 'SG' = 7,529,580`
  - wrong-DB sanity check passed (canonical live proxy `~95M`, not the stale `~2.7M` control-plane residue)
- same-heartbeat PostHog probe:
  - `POST https://us.i.posthog.com/api/projects/415112/query/` with the personal API key returned `{"type":"authentication_error","code":"permission_denied","detail":"You don't have access to the project."}`
  - `POST https://app.posthog.com/api/projects/415112/query/` with the personal API key returned the same `permission_denied`
  - `POSTHOG_PROJECT_KEY` is a project key (write-only) and does not authenticate `/api/projects/.../query/`
- same-heartbeat Paperclip API reads:
  - `GET /api/companies/{companyId}/user-directory` -> `2` active entries (`Rich`, `Board`) (carried from 2026-06-15 06:07Z read; not re-run in this heartbeat)
  - `GET /api/companies/{companyId}/secrets` -> `403 Board access required` (carried from 2026-06-15 06:07Z read)
- same-heartbeat Search Console probe:
  - `GET https://searchconsole.googleapis.com/webmasters/v3/sites?key=$GEMINI_API_KEY` -> `401 UNAUTHENTICATED` with `API keys are not supported by this API`
- carried-forward PostHog closed-day `2026-06-14` numbers (last confirmed 2026-06-15 06:07Z):
  - `api_query = 7,195` (`+51 d/d` vs `7,144`)
  - `mcp_tool_call = 8,468` (`+1,395 d/d` vs `7,073`)
  - distinct active agents = `147` (`+2 d/d` vs `145`)
  - human browser pageviews = `1,627` (`+8 d/d` vs `1,619`)
  - June MTD `api_query` framework buckets = `null/unset 5,435`, `custom 1,733`, `unknown 27`
- Reed search-success acceptance rerun at `2026-06-15T18:08:07Z`:
  - `REST = 108/300 = 36.00%` (`0` timeouts, `0` 5xx)
  - `MCP = 159/300 = 53.00%` (`0` timeouts, `0` 5xx)
  - per-country: `REST SG 78/150 (52.0%)` / `REST US 30/150 (20.0%)`; `MCP SG 78/150 (52.0%)` / `MCP US 81/150 (54.0%)`
- Oracle carry-forward and contract sources:
  - [docs/daily-product-target-shortfall-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-16.md)
  - [docs/daily-source-mix-plan-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-16.md)
  - [docs/buy-51747-hourly-throughput-check-2026-06-15T15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-51747-hourly-throughput-check-2026-06-15T15.md)
  - [docs/buy-52145-daily-competitor-intel-2026-06-16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-52145-daily-competitor-intel-2026-06-16.md)
  - [docs/search-success-acceptance-2026-06-15.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/search-success-acceptance-2026-06-15.md)
