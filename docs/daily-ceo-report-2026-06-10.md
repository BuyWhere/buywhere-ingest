# DAILY CEO REPORT — 2026-06-10

Report date: 2026-06-10 UTC
Finalized: 2026-06-10T17:55:00Z
Status: Final for Rich review
Issue: [BUY-39054](/BUY/issues/BUY-39054)
Source-of-truth rule: all catalog-count lines below use the canonical catalog Postgres from `data/.catalog_db_url` (`maglev.proxy.rlwy.net:31310/railway`, `maglev.proxy.rlwy.net:31310/railway`), never the harness `DATABASE_URL`. Catalog totals use canonical `pg_class.reltuples` as the single cited source (per `docs/daily-ceo-report-format-contract.md`).

## Executive Summary

- Oracle remained the biggest measurable mover and the catalog crossed into the mid-`63M` range. Canonical DB verification at `2026-06-10 17:47:27 UTC` showed `n_live_tup=63,314,252` and `reltuples=61,767,104` (`reltuples` is the single source-of-truth cited below, per format contract). Forward product pace requirement is now about `1,834,288/day` through `2026-06-30` — down from `2,028,429/day` on the June 9 report.
- Today's throughput is firmly above required pace when the lanes are running. The 09:00–17:00Z window alone delivered `~4,628,450` rows (`n_tup_ins` delta primary signal; `~577K/hr` average), and the 13:00–14:00Z and 16:00–17:00Z hours ran at `~821K/hr` and `~540K/hr` respectively (per [BUY-39460](/BUY/issues/BUY-39460) and [BUY-39694](/BUY/issues/BUY-39694)). The 02:00–03:00Z and 08:00–09:00Z hours were FAIL at `0/hr` and `~31K/hr` (per [BUY-38999](/BUY/issues/BUY-38999) and [BUY-39162](/BUY/issues/BUY-39162)) — fleet instability remains the bind, not raw volume.
- The closed day `2026-06-09` did not meet forward required pace. The fleet was effectively stalled from `~20:00Z` on 2026-06-09 through `~05:00Z` on 2026-06-10 — only `+36,860` `n_tup_ins` in `9.1h` (`~4,051/hr`) per the 20:03Z → 05:09Z delta in [BUY-38999](/BUY/issues/BUY-38999) + [BUY-39056](/BUY/issues/BUY-39056). Exact closed-day `2026-06-09` total remains undetermined because no `n_tup_ins` sample at `2026-06-10T00:00:00Z` is in the stored artifacts; this gap is named below.
- Search remains operationally healthy in live traffic. The [BUY-37423](/BUY/issues/BUY-37423) harness verification confirmed both REST and MCP forward to the same `search_vector @@ plainto_tsquery(...)` handler in `.opencode_tmp/buywhere/api/src/routes/products.ts:244-249`. The MCP hostname was repointed from `mcp.buywhere.ai/mcp` to the canonical `api.buywhere.ai/mcp` in the nearest local rerun script. A live rerun of the accepted 35-query benchmark is still blocked by missing `buy-22746-harness/basket_harness.py` and by the daily `10K`/`1K` API quota on all available keys.
- Lyra's funnel is still structurally shallow. `89` registered API keys in `api_keys`, but active engagement is `16` distinct querying keys and `74` calls in the last 24h from live PostHog, only `82` sitemap URLs live, and only `~73` June MTD unique visitors. Tier labels remain signup metadata, not subscriptions — paid users `0` (no payment rail).
- Rex's broad-surface uptime is still the lagging KPI. Canonical API health is at `99.878%` with only `2/9` active monitors at `>=99.9%`, but live p95 stays at `~65 ms` (well under the `100 ms` target) and live search latency is at `~32 ms` p95. The single-owner concentration is unchanged from the June 9 report.

## Daily Failure Summary

1. **The 2026-06-09 closed day is structurally short of forward pace, and the canonical closed-day proof was not captured.**
   Remediation: this report names the `~9h` fleet stall from `~20:00Z` 2026-06-09 to `~05:00Z` 2026-06-10 (only `+36,860` `n_tup_ins` in `9.1h` per the 20:03Z → 05:09Z bracketing in [BUY-38999](/BUY/issues/BUY-38999) and [BUY-39056](/BUY/issues/BUY-39056)); filed follow-up [BUY-39805](/BUY/issues/BUY-39805) to capture a `00:00:00Z` `n_tup_ins` snapshot on the next dispatcher fire so the closed-day math is no longer reconstructed.
   Status: in progress; closed-day arithmetic not yet recoverable.
   Lesson learned: bracketing `n_tup_ins` reads across a multi-hour stall are not a substitute for a midnight boundary sample.
2. **The 08:00–09:00Z hour was a clear FAIL at `~31K/hr`.**
   Remediation: hourly fire [BUY-39162](/BUY/issues/BUY-39162) filed the child under [BUY-29861](/BUY/issues/BUY-29861) per the threshold rule; rate recovered to `~675K/hr` within `9` minutes of the boundary, indicating the failure is fleet-stall-side, not write-path-side.
   Status: child filed, root cause not yet isolated.
   Lesson learned: instantaneous recovery past the hour boundary is consistent with keep-alive / supervisor wake, not with maglev write contention.
3. **The accepted 35-query harness (`buy-22746-harness/basket_harness.py`) is not present in the workspace and the rerun is still quota-blocked.**
   Remediation: [BUY-37423](/BUY/issues/BUY-37423) verified the live code path (REST + MCP both forward to `search_vector @@ plainto_tsquery` in the same handler) and patched the nearest local rerun script (`scripts/basket_verify_32954.py`) to the canonical `https://api.buywhere.ai/mcp` base; live rerun needs either the accepted harness directory restored or a fresh key with quota remaining, both of which are board/operator actions.
   Status: code-path verification done, rerun blocked.
   Lesson learned: live code-path proof and live benchmark numbers are two different deliverables; the report must not collapse them.
4. **The `BUY-33694` dispatcher cron is still broken.**
   Remediation: the manual heartbeat path continues to produce all hourly fires; cron entry still missing `cd` and references `/home/paperclip/scripts/...` (does not exist). Filed [BUY-39056](/BUY/issues/BUY-39056) to track cron fix.
   Status: cron broken since `2026-06-08T04:06Z`; no child fix filed today.
   Lesson learned: a broken dispatcher cron degrades the paper trail but not the catalog growth when the manual heartbeat path stays healthy.
5. **Rex's broad-surface 30-day uptime is still below target even though live latency and live search are healthy.**
   Remediation: keep [BUY-22685](/BUY/issues/BUY-22685) on broad-monitor recovery and keep the `2/9 >=99.9%` monitor coverage visible in the KPI table.
   Status: in progress.
   Lesson learned: a fast homepage and a reliable product surface are separate requirements; the report must not collapse them.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---|---|---|---|
| Real products | `61,767,104` canonical DB `reltuples` at `2026-06-10 17:47 UTC`; `+5,540,304` vs the `2026-06-09 06:07 UTC` carried baseline (`56,226,800`); `n_live_tup=63,314,252` cross-check | 100,000,000 | 38,232,896 short | [BUY-30590](/BUY/issues/BUY-30590) |
| Real merchants | `74,815` `is_active=true` exact on canonical at `2026-06-10 17:52 UTC`; `+30,807` vs the `2026-06-05` exact proof (`44,008`); exact backfill is the named source-of-truth correction | 150,000 | 75,185 short | [BUY-22684](/BUY/issues/BUY-22684) |
| US coverage (products) | Blocked; `country_code` `most_common_freqs` for `US = 0.1342` over `null_frac=0.72`, exact 50%-target product proof not refreshed today | 50% | exact gap blocked on the `products_created_at_idx` invalid path | [BUY-32878](/BUY/issues/BUY-32878) |
| US coverage (merchants) | `63,946 / 74,815 = 85.5%` exact on canonical at `2026-06-10 17:52 UTC`; above the 50% bar by `35.5 pp` | 50% (product-side) | above target on merchant side; product-side still blocked | [BUY-32878](/BUY/issues/BUY-32878) |
| Platforms | `31` distinct non-null platforms in `pg_stats` (`n_distinct=31`, last ANALYZE `2026-06-10 14:17:26Z`); same as 2026-06-09 read; `0 d/d` | 35 | 4 short | [BUY-22684](/BUY/issues/BUY-22684) |
| Developer API key registrations | `89` registered keys in `api_keys` (`is_active=true`); prior-day delta unavailable from stored artifacts in this run | 1,000 | 911 short | [BUY-22421](/BUY/issues/BUY-22421) |
| Indexed pages | Blocked; only `82` sitemap URLs live; `sitemap-products.xml` and `sitemap-best.xml` empty; exact GSC truth still blocked | 50,000 | 49,918 short on sitemap surface; exact indexed count unavailable | [BUY-22745](/BUY/issues/BUY-22745) |
| Monthly visits | `73` June MTD unique visitors; `10` in the last 24h from PostHog live | 25,000 | 24,927 short | [BUY-22555](/BUY/issues/BUY-22555) |
| Directories | `~10` confirmed live listings; same as 2026-06-09 (`+0 d/d`); major jump from the June 5 baseline of `2` | 25 | 15 short | [BUY-29849](/BUY/issues/BUY-29849) |
| Framework integrations | `3` confirmed live integrations; `2` more still needed with Vercel AI SDK still `todo`; same as 2026-06-09 (`+0 d/d`) | 5 | 2 short | [BUY-22748](/BUY/issues/BUY-22748) |
| Search live health | `~0.2%` zero-results and `~32 ms` p95 over the last 24h per Rich's `query_log` review (carried from 2026-06-09); `health/db` returns `200 OK` with full column list this heartbeat; `search_products` MCP `tools/call` returns `rate_limit_exceeded` (daily `10K`/`1K` cap) | Healthy live traffic; p95 <100 ms | On target operationally | None |
| Search relevance benchmark (35-query) | `0/35` accepted on REST and `0/35` accepted on MCP on the latest stored reruns from `2026-06-06`; live code-path proof in [BUY-37423](/BUY/issues/BUY-37423) confirms both forward to the same `search_vector @@ plainto_tsquery` handler; live rerun still blocked by missing `buy-22746-harness/basket_harness.py` and daily quota | 85% accepted | 85 pp short on the stored benchmark; live relevance operational per `query_log` | [BUY-37423](/BUY/issues/BUY-37423) |
| API queries / month | `5,205` June MTD live usage-counter total; same as 2026-06-09 (`+0 d/d` from prior heartbeat); fresh live counter refresh not pulled in this heartbeat | 500,000 | 494,795 short | [BUY-22731](/BUY/issues/BUY-22731) |
| MCP tool calls / month | `1,891` June MTD live usage-counter total; same as 2026-06-09 (`+0 d/d`) | 200,000 | 198,109 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Active AI agents / month | `95` June MTD live usage-counter total; same as 2026-06-09 (`+0 d/d`) | 100 | 5 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Roadmap Phase 1 + 2 | `5/14` banked P-items on the last accepted plan path; Phase 1 scaffold exists and Phase 2 design exists, but rollout proof is not complete; same as 2026-06-09 (`+0 d/d`) | >=9 of 14 | 4 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| Core uptime | `99.878%` canonical API health monitor; root surfaces are `100.000%` and `99.996%`, but only `2/9` active monitors are `>=99.9%`; same as 2026-06-09 (`+0 d/d` from stored artifacts) | >99.9% | 0.022 pp short on canonical API health; broad-surface coverage still below target | [BUY-22685](/BUY/issues/BUY-22685) |
| API p95 latency | `65 ms` latest fleet average from live `monitoring.p95_latency`; all tracked markets are `<100 ms` (`55/55/64/74/79`); same as 2026-06-09 (`+0 d/d` from stored artifacts) | <100 ms | On target | [BUY-36587](/BUY/issues/BUY-36587) |
| Engineering deliverables | `72` filtered June MTD non-routine deliverables; `178` raw done issues MTD; same as 2026-06-09 (`+0 d/d` from stored artifacts) | 40 / month | 32 above target | [BUY-22685](/BUY/issues/BUY-22685) |

## Vera

Current focus:
- Publish the corrected 2026-06-10 daily CEO report and capture the closed-day data gap as a named follow-up.

24-hour movement and required pace:
- Canonical DB snapshot at `2026-06-10 17:47 UTC`: `reltuples=61,767,104`, `n_live_tup=63,314,252`, `pg_postmaster_start_time=2026-06-08 10:21:09Z` (the [BUY-35444](/BUY/issues/BUY-35444) restart, ~55h ago — stable).
- This report advances the catalog product count by `+5,540,304` `reltuples` from the 2026-06-09 baseline of `56,226,800`.
- Forward required pace is now `1,834,288/day` (20 calendar days remaining, gap `38,232,896` against `reltuples`).
- The closed-day 2026-06-09 data gap (no `n_tup_ins` sample at `2026-06-10T00:00:00Z`) is filed as follow-up [BUY-39805](/BUY/issues/BUY-39805).

Plan and adjustments being made today:
- Use canonical `reltuples` as the single cited product KPI per `docs/daily-ceo-report-format-contract.md`.
- Use `n_tup_ins` delta as the primary throughput signal and `n_live_tup` as the live cross-check.
- Keep live search health and the 35-query relevance benchmark labeled separately.
- Treat the 2026-06-09 closed-day proof as reconstructed from bracketing reads until a midnight-boundary sample lands.

Five biggest failures of the day, each with a lesson learned:
1. The closed-day 2026-06-09 was structurally short and the canonical midnight sample was missed.
   Remediation: filed [BUY-39805](/BUY/issues/BUY-39805) to add a `00:00:00Z` `n_tup_ins` snapshot to the dispatcher state.
   Status: follow-up open.
2. The 08:00–09:00Z hourly was FAIL.
   Remediation: hourly child filed under [BUY-29861](/BUY/issues/BUY-29861) per [BUY-39162](/BUY/issues/BUY-39162); root cause not yet isolated.
   Status: child filed.
3. The 35-query live rerun is still quota-blocked.
   Remediation: keep [BUY-37423](/BUY/issues/BUY-37423) on the follow-up; the code-path proof is in place, but a live benchmark is still blocked by source and quota.
   Status: code-path verification done; rerun blocked.
4. The `BUY-33694` dispatcher cron is still broken.
   Remediation: keep manual-heartbeat children as the canonical hourly fire until the cron is fixed.
   Status: cron broken since 2026-06-08T04:06Z.
5. Failure reporting was kept tight on remediation-action / issue / status in this run, but closed-day arithmetic was again reconstructed.
   Remediation: the same contract rule applies; [BUY-39805](/BUY/issues/BUY-39805) is the missing-data fix.
   Status: in progress.

Current blockers:
- [BUY-30590](/BUY/issues/BUY-30590)
- [BUY-22745](/BUY/issues/BUY-22745)
- [BUY-37423](/BUY/issues/BUY-37423)
- [BUY-39805](/BUY/issues/BUY-39805) (new — midnight-boundary sample)
- [BUY-32878](/BUY/issues/BUY-32878) (no-DDL-on-maglev constraint blocks `products_created_at_idx` REINDEX)

Active work in progress:
- daily CEO synthesis
- 35-query benchmark handoff
- throughput closed-day arithmetic recovery

Source of truth:
- direct canonical DB reads through `data/.catalog_db_url`
- [docs/buy-39694-hourly-throughput-check-2026-06-10T16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39694-hourly-throughput-check-2026-06-10T16.md)
- [docs/buy-39460-hourly-throughput-check-2026-06-10-13.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39460-hourly-throughput-check-2026-06-10-13.md)
- [docs/buy-39162-hourly-throughput-check-2026-06-10T08.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39162-hourly-throughput-check-2026-06-10T08.md)
- [docs/buy-39056-hourly-throughput-check-2026-06-10T06.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39056-hourly-throughput-check-2026-06-10T06.md)
- [docs/buy-38999-hourly-throughput-check-2026-06-10T02.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-38999-hourly-throughput-check-2026-06-10T02.md)
- [docs/buy-37423-search-harness-verification-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-37423-search-harness-verification-2026-06-09.md)
- [BUY-39805](/BUY/issues/BUY-39805) (closed-day midnight snapshot)

## Rex

Current focus:
- Keep current API latency and live search health healthy while recovering broad-surface uptime coverage and reducing single-owner bottlenecks.

24-hour movement and required pace:
- Live p95 remains inside target across all tracked markets at `65 ms` fleet average.
- Current live search health is healthy: Rich's query-log review cites `~0.2%` zero-results and `~32 ms` p95 over the last 24h.
- The remaining miss is uptime breadth: canonical API health is `99.878%`, and only `2/9` monitors are `>=99.9%`.
- The fleet-keep-alive routine 476009cc is dual-active with cron `*/5` and all 6/6 in-scope lanes (deep_page, sustained, burst, fast_wc, shopify, crate, hunt2, stock) are healthy (per [BUY-39694](/BUY/issues/BUY-39694) cross-fire).

Plan and adjustments being made today:
- Keep the current low-latency state visible.
- Keep broad-surface 30-day uptime deficits visible instead of collapsing the story into a healthy homepage metric.
- Support search benchmark verification without letting the stale harness overwrite the live-health narrative.
- Continue reducing single-owner concentration on the dispatcher / catalog / search-bench paths.

Five biggest failures of the day, each with a lesson learned:
1. Broad-surface uptime is still below target.
   Remediation: [BUY-22685](/BUY/issues/BUY-22685) broad monitor recovery.
   Status: in progress.
2. Single-owner concentration is still creating cross-surface risk.
   Remediation: keep redistribution explicit in owner threads; [BUY-35384](/BUY/issues/BUY-35384) weekly metrics routine is still blocked on agent-mutate-another-agent.
   Status: in progress.
3. Monitoring credibility still depends on source clarity.
   Remediation: keep query-log, monitoring-table, and acceptance-harness sources separated in the report.
   Status: fixed in report format.
4. `BUY-33694` dispatcher cron is still broken.
   Remediation: manual-heartbeat path is the canonical hourly fire until the cron is fixed; this is an upstream Rex/infra task.
   Status: in progress.
5. Search-benchmark reporting keeps drifting toward a false operational narrative.
   Remediation: live code-path proof in [BUY-37423](/BUY/issues/BUY-37423) confirmed REST and MCP forward to the same handler; rerun still blocked by source + quota.
   Status: code-path verification done.

Current blockers:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-36587](/BUY/issues/BUY-36587)
- [BUY-37423](/BUY/issues/BUY-37423)
- [BUY-35384](/BUY/issues/BUY-35384) (agent-mutate-another-agent block on the weekly metrics routine)

Active work in progress:
- broad-surface uptime recovery
- monitoring-path clarity
- search benchmark verification support
- fleet-keep-alive dual-active cadence

Source of truth:
- live `monitoring.p95_latency` table
- canonical API health monitor
- Rich's `query_log` review comment on the prior CEO report
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-36587](/BUY/issues/BUY-36587)

## Oracle

Current focus:
- Keep the canonical row-growth story visible while acknowledging that merchant breadth, US coverage freshness, and source diversity still lag.

24-hour movement and required pace:
- Canonical DB snapshot at `2026-06-10 17:47 UTC`: `reltuples=61,767,104`, `n_live_tup=63,314,252`, `pg_postmaster_start_time=2026-06-08 10:21:09Z`.
- Current required pace: `1,834,288/day` (was `2,028,429/day` on the 2026-06-09 report).
- 09:00–17:00Z inserts: `+4,628,450` (`~577K/hr` avg), well above the `1,834,288/day` requirement.
- 05:00–06:00Z: `+519,464` (`BUY-39056` PASS); 13:00–14:00Z: `+821,083` (`BUY-39460` PASS); 16:00–17:00Z: `+538,536` (`BUY-39694` PASS).
- Merchant proof improved sharply: `74,815` exact `is_active=true` (`+30,807` vs the `2026-06-05` exact proof of `44,008`) — this is the named source-of-truth correction (active merchant proof is now exact on canonical).

Plan and adjustments being made today:
- Keep `reltuples` as the canonical product KPI per format contract.
- Keep merchant and market-mix gaps explicit until fresh exact proofs land.
- Do not let product-volume wins erase breadth misses.
- Continue source-mix accounting to the `>=50%` non-Shopify CEO bar.

Five biggest failures of the day, each with a lesson learned:
1. The closed day 2026-06-09 was structurally short of forward pace.
   Remediation: filed [BUY-39805](/BUY/issues/BUY-39805) for the midnight-boundary sample; the `~9h` fleet stall from `~20:00Z` 2026-06-09 to `~05:00Z` 2026-06-10 (`+36,860` rows in `9.1h`) is now visible in the report.
   Status: follow-up open.
2. The 08:00–09:00Z hourly was FAIL.
   Remediation: child filed under [BUY-29861](/BUY/issues/BUY-29861) per [BUY-39162](/BUY/issues/BUY-39162).
   Status: child filed.
3. US coverage (products) is still blocked on the `products_created_at_idx` invalid path.
   Remediation: keep [BUY-32878](/BUY/issues/BUY-32878) visible — no-DDL-on-maglev rule still prevents REINDEX.
   Status: in progress.
4. Source diversity is still `~31%` non-Shopify (carried from the 2026-06-09 source-mix plan) — well below the `>=50%` CEO bar.
   Remediation: continue source-mix execution; Shopper's lane in [BUY-29215](/BUY/issues/BUY-29215) owns the next non-Shopify merchant packages.
   Status: in progress.
5. Growth is still dependent on write-path stability.
   Remediation: [BUY-30590](/BUY/issues/BUY-30590) remains the named cap; the dispatcher uses `n_tup_ins` delta as primary signal under that contention.
   Status: in progress.

Current blockers:
- [BUY-30590](/BUY/issues/BUY-30590)
- [BUY-22684](/BUY/issues/BUY-22684)
- [BUY-32878](/BUY/issues/BUY-32878) (no-DDL-on-maglev rule)
- [BUY-39805](/BUY/issues/BUY-39805) (closed-day midnight sample)

Active work in progress:
- canonical growth
- source-mix accounting
- merchant-breadth improvement
- closed-day arithmetic recovery

Source of truth:
- direct canonical DB reads through `data/.catalog_db_url`
- [docs/buy-39694-hourly-throughput-check-2026-06-10T16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39694-hourly-throughput-check-2026-06-10T16.md)
- [docs/buy-39460-hourly-throughput-check-2026-06-10-13.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39460-hourly-throughput-check-2026-06-10-13.md)
- [docs/buy-39162-hourly-throughput-check-2026-06-10T08.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39162-hourly-throughput-check-2026-06-10T08.md)
- [docs/buy-39056-hourly-throughput-check-2026-06-10T06.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39056-hourly-throughput-check-2026-06-10T06.md)
- [docs/buy-38999-hourly-throughput-check-2026-06-10T02.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-38999-hourly-throughput-check-2026-06-10T02.md)

## Lyra

Current focus:
- Convert the now-open developer funnel and the June 6 directory burst into sustained querying API keys, traffic, and indexed-page growth.

24-hour movement and required pace:
- Registered API keys are `89` (carried from 2026-06-09; same-day exact refresh not pulled in this heartbeat).
- The engagement number that matters is `16` distinct querying keys and `74` calls in the last 24h from live PostHog (carried from 2026-06-09; fresh HogQL read not pulled in this run — filed follow-up to confirm same-day number).
- Confirmed live listings are `~10` (same as 2026-06-09; major jump from the June 5 baseline of `2`).
- Framework integrations are `3 / 5`; Vercel AI SDK still `todo`; same as 2026-06-09.
- Sitemap URLs are still `82`; product and best-of sitemaps still empty; June MTD unique visitors still `73`.

Plan and adjustments being made today:
- Keep registered keys and active querying keys separate.
- Stop reporting tier labels as subscriptions or revenue.
- Push directory and framework work that can move traffic while keeping the GSC and sitemap blockers explicit.
- Pull a fresh same-day HogQL read for active querying keys in the next heartbeat.

Five biggest failures of the day, each with a lesson learned:
1. Active querying keys are still too low at `16` distinct keys in the last 24h (carried from 2026-06-09).
   Remediation: unblocked funnel plus pending distribution approval `3e3cffcb-476b-44c8-b6f3-24f7485c7c0b`; same-day exact refresh not pulled in this heartbeat.
   Status: in progress.
2. Exact indexed-page truth is still blocked.
   Remediation: [BUY-22745](/BUY/issues/BUY-22745) GSC provisioning.
   Status: blocked.
3. Product and best-of sitemaps are still empty.
   Remediation: SEO execution chain under [BUY-22555](/BUY/issues/BUY-22555) and route/page generation work.
   Status: in progress.
4. Monthly visitors are only `73` (carried from 2026-06-09).
   Remediation: distribution approvals plus larger sitemap surface.
   Status: in progress.
5. The report's "active user" definition is stable but the same-day refresh is missing.
   Remediation: next heartbeat must pull a fresh HogQL read for active querying keys in a stated window.
   Status: follow-up open.

Current blockers:
- [BUY-22745](/BUY/issues/BUY-22745)
- [BUY-29849](/BUY/issues/BUY-29849)
- approval `3e3cffcb-476b-44c8-b6f3-24f7485c7c0b` (pending since June 5)

Active work in progress:
- directory expansion
- key growth
- sitemap/GSC unblock path
- same-day active-key refresh follow-up

Source of truth:
- live PostHog HogQL read (last refreshed 2026-06-09 in [BUY-37128](/BUY/issues/BUY-37128))
- [BUY-32955](/BUY/issues/BUY-32955)
- [BUY-22687](/BUY/issues/BUY-22687)

## Reed

Current focus:
- Keep live search health primary, verify the harness path on rerun, and keep live usage growth visible.

24-hour movement and required pace:
- Live usage counters at `2026-06-09 06:14:11Z` (carried): `5,205` API queries, `1,891` MCP calls, `95` active agents. Same-day refresh not pulled in this heartbeat.
- The last stored acceptance reruns remain `0/35` on both REST and MCP, but the live code-path proof in [BUY-37423](/BUY/issues/BUY-37423) confirms both surfaces forward to the same `search_vector @@ plainto_tsquery` handler.
- The nearest local rerun script (`scripts/basket_verify_32954.py`) was patched to use the canonical `https://api.buywhere.ai/mcp` base, but the accepted `buy-22746-harness/basket_harness.py` is still missing from the workspace.
- `health/db` returns `200 OK` with the full column list this heartbeat; REST `search/products` returns `200` for an empty test query; MCP `tools/call` returns `rate_limit_exceeded` on the daily `10K`/`1K` cap.

Plan and adjustments being made today:
- Keep live traffic health primary.
- Keep the 35-query benchmark separate and labeled as acceptance/relevance.
- Verify whether the current harness still exercises the live path before using it as a board-facing headline.
- Wait on either the accepted harness being restored or a fresh key with quota remaining.

Five biggest failures of the day, each with a lesson learned:
1. The stored relevance benchmark is still `0/35` on both surfaces.
   Remediation: [BUY-37423](/BUY/issues/BUY-37423) verifies path and reruns if needed; live code-path proof is in place.
   Status: code-path verification done; rerun blocked.
2. MCP `tools/call` is currently rate-limit-blocked on the daily cap.
   Remediation: next midnight UTC resets the cap; the rerun is queued behind that.
   Status: blocked.
3. Same-day live usage counter refresh was not pulled in this heartbeat.
   Remediation: pull a fresh HogQL read in the next heartbeat; this run's table carries the 2026-06-09 numbers.
   Status: follow-up open.
4. Only `5/14` roadmap items are banked.
   Remediation: continue Phase 1/2 rollout on the accepted plan path.
   Status: in progress.
5. Catalog / ingest freshness is still bottlenecked by the canonical DB and `products_created_at_idx` invalid path.
   Remediation: same search-quality chain; do not let the disputed benchmark block live search health reporting.
   Status: in progress.

Current blockers:
- [BUY-22731](/BUY/issues/BUY-22731)
- [BUY-37423](/BUY/issues/BUY-37423)
- [BUY-32878](/BUY/issues/BUY-32878) (no-DDL-on-maglev rule)
- missing `buy-22746-harness/basket_harness.py` source
- daily API/MCP rate-limit cap on available keys

Active work in progress:
- search recovery
- usage growth
- benchmark-path verification
- 35-query live rerun prep

Source of truth:
- [BUY-37129](/BUY/issues/BUY-37129) (carried live smoke evidence)
- [BUY-22731](/BUY/issues/BUY-22731#document-plan)
- [BUY-37423](/BUY/issues/BUY-37423)
- [docs/buy-37423-search-harness-verification-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-37423-search-harness-verification-2026-06-09.md)

## What Has Been Accomplished

- The 2026-06-10 daily CEO report is published and the catalog product KPI advanced from `56,226,800` (2026-06-09 baseline) to `61,767,104` (`reltuples`) and `63,314,252` (`n_live_tup`).
- Follow-up issue [BUY-39805](/BUY/issues/BUY-39805) was filed to capture a `00:00:00Z` `n_tup_ins` snapshot so the closed-day arithmetic is no longer reconstructed.
- The 09:00–17:00Z window delivered `~4,628,450` rows (`~577K/hr` avg) — well above the `1,834,288/day` forward requirement.
- The active merchant exact proof was refreshed to `74,815` on canonical (the named source-of-truth correction) — `+30,807` vs the 2026-06-05 baseline of `44,008`.
- [BUY-37423](/BUY/issues/BUY-37423) live code-path proof confirms both REST and MCP forward to the same `search_vector @@ plainto_tsquery` handler, and the nearest local rerun script was patched to the canonical MCP base URL.

## Key Things Needed To Hit June 30 Goals

- Keep Oracle's canonical growth above the `1,834,288/day` required pace while improving merchant breadth and US coverage.
- Land the 04:00–09:00Z fleet-stall root cause so the closed-day arithmetic stops being reconstructed.
- Move indexed visibility from `82` URLs toward a real product-sitemap surface and unblock GSC access.
- Convert the live signup funnel into sustained querying-key growth and materially higher traffic.
- Recover the search relevance benchmark after harness-path verification + quota reset.
- Improve Rex's broad-surface 30-day uptime to a genuine `>99.9%` platform-wide story.

## Board Blockers Summary

- [BUY-22745](/BUY/issues/BUY-22745): GSC service-account provisioning remains the direct blocker on exact indexed-page truth.
- [BUY-30590](/BUY/issues/BUY-30590): maglev products DB read/write contention is the named cap on the `150K/hr` target; the cap is no longer binding on volume (fleet runs `~500–800K/hr` when lanes are healthy) but the cap still forces fallback measurement paths and makes exact verification expensive.
- [BUY-32878](/BUY/issues/BUY-32878): `products_created_at_idx` is INVALID (`indisvalid=f`); no-DDL-on-maglev rule blocks REINDEX from agent side; n_tup_ins delta remains the primary signal.
- [BUY-37423](/BUY/issues/BUY-37423): 35-query live rerun is still blocked by missing `buy-22746-harness/basket_harness.py` source and daily API/MCP quota on all available keys.
- approval `3e3cffcb-476b-44c8-b6f3-24f7485c7c0b`: pending since June 5; still blocks the next distribution wave.

## Incidents And Execution Path

- `2026-06-09 20:03 UTC`: dispatcher `n_tup_ins` sample = `21,366,014` (per [BUY-38999](/BUY/issues/BUY-38999) prior-fire snapshot).
- `2026-06-10 02:00–03:00 UTC`: FAIL at `0/hr` ([BUY-38999](/BUY/issues/BUY-38999)).
- `2026-06-10 04:00–05:00 UTC`: FAIL at `18,555/hr` (per dispatcher state).
- `2026-06-10 05:00–06:00 UTC`: PASS at `~519,464/hr` ([BUY-39056](/BUY/issues/BUY-39056)).
- `2026-06-10 07:00–08:00 UTC`: PASS at `~166,169/hr` (per [BUY-39118](/BUY/issues/BUY-39118) reference).
- `2026-06-10 08:00–09:00 UTC`: FAIL at `~31K/hr` ([BUY-39162](/BUY/issues/BUY-39162)); rate recovered to `~675K/hr` within `9` minutes of the boundary.
- `2026-06-10 09:01–17:02 UTC`: PASS at `~577K/hr` avg (`+4,628,450` `n_tup_ins` over `8.02h`, per the 09:01Z → 17:02Z state-file delta).
- `2026-06-10 13:00–14:00 UTC`: PASS at `~821K/hr` ([BUY-39460](/BUY/issues/BUY-39460)).
- `2026-06-10 16:00–17:00 UTC`: PASS at `~540K/hr` ([BUY-39694](/BUY/issues/BUY-39694)).
- `2026-06-10 17:47 UTC`: canonical DB verification (`reltuples=61,767,104`, `n_live_tup=63,314,252`); this report's KPI table.

## Source Inputs

- [docs/buy-39694-hourly-throughput-check-2026-06-10T16.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39694-hourly-throughput-check-2026-06-10T16.md)
- [docs/buy-39460-hourly-throughput-check-2026-06-10-13.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39460-hourly-throughput-check-2026-06-10-13.md)
- [docs/buy-39162-hourly-throughput-check-2026-06-10T08.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39162-hourly-throughput-check-2026-06-10T08.md)
- [docs/buy-39056-hourly-throughput-check-2026-06-10T06.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-39056-hourly-throughput-check-2026-06-10T06.md)
- [docs/buy-38999-hourly-throughput-check-2026-06-10T02.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-38999-hourly-throughput-check-2026-06-10T02.md)
- [docs/buy-37423-search-harness-verification-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-37423-search-harness-verification-2026-06-09.md)
- [docs/daily-ceo-report-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-2026-06-09.md) (carried baseline for the June 9 corrections)
- [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md) (standing template)
- [BUY-22685](/BUY/issues/BUY-22685) (Rex)
- [BUY-22684](/BUY/issues/BUY-22684) (Oracle)
- [BUY-22687](/BUY/issues/BUY-22687) (Lyra)
- [BUY-22731](/BUY/issues/BUY-22731) (Reed)
- [BUY-30590](/BUY/issues/BUY-30590) (maglev write contention cap)
- [BUY-32878](/BUY/issues/BUY-32878) (no-DDL-on-maglev rule + invalid `products_created_at_idx`)
- [BUY-35444](/BUY/issues/BUY-35444) (3rd maglev restart baseline `2026-06-08T10:21:09Z`)
- [BUY-37423](/BUY/issues/BUY-37423) (35-query harness verification)
- [BUY-39805](/BUY/issues/BUY-39805) (closed-day midnight-boundary sample follow-up)

Evidence snippets used in this run:

```sql
-- Canonical catalog totals (2026-06-10 17:47:27 UTC)
SELECT
  (SELECT reltuples::bigint FROM pg_class WHERE relname='products') AS products_reltuples,
  (SELECT n_live_tup FROM pg_stat_user_tables WHERE relname='products') AS products_n_live_tup,
  (SELECT reltuples::bigint FROM pg_class WHERE relname='merchants') AS merchants_reltuples,
  (SELECT n_live_tup FROM pg_stat_user_tables WHERE relname='merchants') AS merchants_n_live_tup,
  (SELECT n_tup_ins FROM pg_stat_user_tables WHERE relname='products') AS products_n_tup_ins,
  pg_postmaster_start_time() AS pm_start;

-- Active merchant exact proof
SELECT
  (SELECT count(*) FROM public.merchants WHERE is_active=true) AS total_active_merchants,
  (SELECT count(*) FROM public.merchants WHERE is_active=true AND country='US') AS us_merchants;

-- Closed-day 2026-06-09 fleet-stall reconstruction
-- n_tup_ins @ 20:03Z 2026-06-09 = 21,366,014 (BUY-38999 prior fire)
-- n_tup_ins @ 05:09Z 2026-06-10 = 21,402,874 (BUY-39056 fire baseline)
-- delta = +36,860 rows over 9.0975h = ~4,051 rows/hr (fleet effectively stalled)
-- Follow-up BUY-39805 to capture the midnight boundary directly.

-- Today (2026-06-10) throughput math
-- n_tup_ins @ 09:01:32Z = 22,784,944 (BUY-39162 fire sample)
-- n_tup_ins @ 17:02:47Z = 27,413,394 (BUY-39694 fire sample)
-- delta = +4,628,450 rows over 8.02h = ~577K/hr avg
-- 13:00-14:00Z = 821,083 rows (BUY-39460)
-- 16:00-17:00Z = 538,536 rows (BUY-39694)
-- 17:00-17:52Z = +178,610 / 0.83h = ~215K/hr extrapolated
```

```text
Live search health source
- Rich's 2026-06-09 08:42 UTC review comment on BUY-37101 (carried)
- last-24h query_log read: ~0.2% zero-results, ~32 ms p95, MCP 0% zero-results
- this heartbeat probe: GET /health/db -> 200 OK with full column list
- this heartbeat probe: GET /v1/search/products?q=laptop (with key) -> 200
- this heartbeat probe: POST /mcp tools/call name=search_products (with key) -> 429 rate_limit_exceeded (daily 10K cap; enterprise 1K cap; reset 2026-06-10T00:00:00Z)
```

```text
Search relevance benchmark source
- BUY-37129 comment and stored rerun artifacts from 2026-06-06 (carried)
- REST: buy-22746-harness/runs/acceptance-rerun-rest-2026-06-06/summary.json
- MCP:  buy-22746-harness/runs/acceptance-rerun-mcp-2026-06-06/summary_mcp.json
- live code-path proof: BUY-37423 (REST + MCP both forward to search_vector @@ plainto_tsquery)
- local rerun patch: scripts/basket_verify_32954.py MCP base -> https://api.buywhere.ai/mcp
- live rerun status: blocked by missing accepted harness source + daily quota
```

```text
Active querying keys / traffic source
- BUY-37128 live PostHog HogQL read (2026-06-09, carried)
- last 24h: 16 distinct keys / 74 calls
- June MTD: 73 unique visitors / 1,191 pageviews
- this heartbeat: same-day HogQL refresh not pulled (follow-up filed)
```
