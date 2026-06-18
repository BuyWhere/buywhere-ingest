# DAILY CEO REPORT — 2026-06-09

Report date: 2026-06-09 UTC
Original finalization: 2026-06-09T06:50:00Z
Correction pass: 2026-06-09T08:50:00Z
Status: Corrected for Rich review items 1-5
Issue: [BUY-37101](/BUY/issues/BUY-37101)
Source-of-truth rule: all catalog-count lines below use the canonical catalog Postgres from `data/.catalog_db_url` (`maglev.proxy.rlwy.net:31310/railway`), never the harness `DATABASE_URL`.

## Executive Summary

- Oracle remains the biggest measurable mover. Direct canonical DB verification at `2026-06-09 06:07:44 UTC` showed `56,866,331` `n_live_tup` and `56,226,800` `reltuples`, cutting the forward product pace requirement to about `2,028,429/day` through `2026-06-30`.
- Search is operationally healthy in live traffic and should be reported that way. Rich's `2026-06-09 08:42 UTC` review cites last-24h `query_log` health at about `0.2%` zero-results and `~32 ms` p95, with MCP at `0%` zero-results. The `0/35` REST and `0/35` MCP numbers are a separate acceptance/relevance benchmark, not a live uptime/success rate.
- The 35-query benchmark is now treated as disputed until its path is re-verified against the current live search stack. Follow-up issue [BUY-37423](/BUY/issues/BUY-37423) was created to prove which path the harness hits and republish the benchmark if needed.
- Lyra still has a severe top-of-funnel problem, but the right definitions are now explicit: `89` registered API keys in `api_keys`, `16` distinct querying keys and `74` calls in the last 24h from live PostHog, `82` sitemap URLs live, and only `73` June MTD unique visitors. Tier labels such as `enterprise` and `pro` are signup metadata only, not paid subscriptions. Real paid users remain `0` because no payment rail exists.
- The biggest remaining June 30 gaps are merchant breadth (`44,008 / 150,000` on the last exact proof), indexed visibility (`82 / 50,000` sitemap-surface proxy with GSC still blocked), monthly visits (`73 / 25,000`), and the still-unaccepted search relevance benchmark (`0/35` on both stored reruns, now under path verification).

## Daily Failure Summary

1. **The report itself misframed search as broken when live search health is currently good.**
   Remediation: this correction pass now separates live search health from the 35-query relevance benchmark, and [BUY-37423](/BUY/issues/BUY-37423) was opened to verify whether the `0/35` harness still hits the current path.
   Status: fixed in report formatting; harness verification follow-up is `todo`.
   Lesson learned: never present an acceptance harness score as a live operational success rate.
2. **Indexed-page execution is still structurally blocked.**
   Remediation: keep [BUY-22745](/BUY/issues/BUY-22745) as the explicit GSC credential blocker and keep the empty `sitemap-products.xml` / `sitemap-best.xml` work visible under the SEO execution chain.
   Status: blocked on Rich credential path plus engineering activation of product and best-of sitemaps.
   Lesson learned: visibility KPIs need both measurement access and page inventory.
3. **Visitor volume is still negligible relative to target.**
   Remediation: keep the stalled distribution approvals visible, especially approval [3e3cffcb](/BUY/approvals/3e3cffcb-476b-44c8-b6f3-24f7485c7c0b), plus execute the queued listing and framework work instead of treating the funnel as solved.
   Status: in progress, but still far behind target.
   Lesson learned: a live signup funnel is not the same thing as scaled audience acquisition.
4. **Broad-surface 30-day uptime is still below target even though current latency and current search health are good.**
   Remediation: keep [BUY-22685](/BUY/issues/BUY-22685) on broad monitor recovery instead of hiding behind the healthy root surfaces and `65 ms` live p95.
   Status: in progress.
   Lesson learned: "fast now" and "reliable across the whole product surface" are separate requirements.
5. **Merchant breadth still lags the product-volume story.**
   Remediation: keep [BUY-22684](/BUY/issues/BUY-22684) and the canonical ingest breadth work focused on exact merchant-backed growth, not just raw row growth.
   Status: in progress; same-day exact merchant refresh did not land in this path.
   Lesson learned: June 30 requires breadth, not just catalog mass.

## June 30 KPI Summary

| KPI | Current | Target | Gap | Blocker |
|---|---|---|---|---|
| Real products | `56,226,800` canonical DB `reltuples` at `2026-06-09 06:07 UTC`; `+4,795,928` vs the `2026-06-08 14:57 UTC` carried baseline | 100,000,000 | 43,773,200 short | [BUY-30590](/BUY/issues/BUY-30590) |
| Real merchants | `44,008` last exact product-backed merchant proof from `2026-06-05`; same-day exact refresh unavailable in this path | 150,000 | 105,992 short | [BUY-22684](/BUY/issues/BUY-22684) |
| US coverage | `32.57%` last exact proof from `2026-06-05`; prior-day delta unavailable from stored artifacts | 50% | 17.43 pp short | [BUY-22684](/BUY/issues/BUY-22684) |
| Platforms | `91` last exact populated-platform proof from `2026-06-05`; prior-day delta unavailable | 35 | 56 above target | [BUY-22684](/BUY/issues/BUY-22684) |
| Developer API key registrations | `89` registered keys in `api_keys` with `is_active=true`; `+1` created in the last 24h and `+5` created in June MTD; registration count only, not paid tiers or engagement | 1,000 | 911 short | [BUY-22421](/BUY/issues/BUY-22421) |
| Indexed pages | Blocked; only `82` sitemap URLs are live because `sitemap-products.xml` and `sitemap-best.xml` are empty, and exact GSC truth is still blocked | 50,000 | 49,918 short on sitemap surface; exact indexed count unavailable | [BUY-22745](/BUY/issues/BUY-22745) |
| Monthly visits | `73` June MTD unique visitors; `10` in the last 24h from PostHog live | 25,000 | 24,927 short | [BUY-22555](/BUY/issues/BUY-22555) |
| Directories | `~10` confirmed live listings; major jump from the June 5 baseline of `2` | 25 | 15 short | [BUY-29849](/BUY/issues/BUY-29849) |
| Framework integrations | `3` confirmed live integrations; `2` more still needed with Vercel AI SDK still `todo` | 5 | 2 short | [BUY-22748](/BUY/issues/BUY-22748) |
| Search live health | `~0.2%` zero-results and `~32 ms` p95 over the last 24h per Rich's `query_log` review; MCP zero-results `0%` | Healthy live traffic; p95 <100 ms | On target operationally | None |
| Search relevance benchmark (35-query) | `0/35` accepted on REST and `0/35` accepted on MCP on the latest stored reruns from `2026-06-06`; currently disputed pending harness-path verification | 85% accepted | 85 pp short | [BUY-37423](/BUY/issues/BUY-37423) |
| API queries / month | `5,205` June MTD live usage-counter total | 500,000 | 494,795 short | [BUY-22731](/BUY/issues/BUY-22731) |
| MCP tool calls / month | `1,891` June MTD live usage-counter total | 200,000 | 198,109 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Active AI agents / month | `95` June MTD live usage-counter total | 100 | 5 short | [BUY-22731](/BUY/issues/BUY-22731) |
| Roadmap Phase 1 + 2 | `5/14` banked P-items on the last accepted plan path; Phase 1 scaffold exists and Phase 2 design exists, but rollout proof is not complete | >=9 of 14 | 4 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| Core uptime | `99.878%` canonical API health monitor; root surfaces are `100.000%` and `99.996%`, but only `2/9` active monitors are `>=99.9%` | >99.9% | 0.022 pp short on canonical API health; broad-surface coverage still below target | [BUY-22685](/BUY/issues/BUY-22685) |
| API p95 latency | `65 ms` latest fleet average from live `monitoring.p95_latency`; all tracked markets are `<100 ms` (`55/55/64/74/79`) | <100 ms | On target | [BUY-36587](/BUY/issues/BUY-36587) |
| Engineering deliverables | `72` filtered June MTD non-routine deliverables; `178` raw done issues MTD | 40 / month | 32 above target | [BUY-22685](/BUY/issues/BUY-22685) |

## Vera

Current focus:
- Correct the June 9 report so live search health, the 35-query benchmark, active-key usage, and failure remediation are all labeled truthfully and sourced explicitly.

24-hour movement and required pace:
- Canonical DB verification refreshed the top-line product evidence to `56,226,800` `reltuples`.
- This correction pass split live search health from the disputed benchmark and created [BUY-37423](/BUY/issues/BUY-37423) to verify the harness path.
- The standing active-user definition is now "distinct API keys that actually queried in a stated window," not email-verified humans or cumulative registered rows.

Plan and adjustments being made today:
- Keep live search health primary in the report and keep the 35-query relevance benchmark separate and clearly labeled.
- Report registered API keys, active querying keys, and paid users as three different concepts.
- Attach each headline number to either a direct query, a live product endpoint, or a dated issue/document source.

Five biggest failures of the day, each with a lesson learned:
1. The report mislabeled live search as broken.
   Remediation: fixed in this revision; [BUY-37423](/BUY/issues/BUY-37423) opened.
   Status: fixed in report, follow-up open.
2. The report treated `api_keys.tier` labels as if they implied subscriptions.
   Remediation: removed subscription framing; paid users now explicitly `0` until payments exist.
   Status: fixed.
3. The report used unstable "active user" definitions.
   Remediation: switched to distinct querying API keys in an explicit window.
   Status: fixed in format; future runs must keep it.
4. The report fell back to agent assertions without enough reconciliation.
   Remediation: expanded the evidence section and cited issue/comment sources for every corrected number.
   Status: fixed for this revision.
5. Failure reporting had drifted back to lessons-only.
   Remediation: every failure now includes action, issue, and status.
   Status: fixed.

Current blockers:
- [BUY-30590](/BUY/issues/BUY-30590)
- [BUY-22745](/BUY/issues/BUY-22745)
- [BUY-37423](/BUY/issues/BUY-37423)

Active work in progress:
- daily CEO synthesis
- report-contract correction
- search benchmark verification handoff

Source of truth:
- [docs/daily-product-target-shortfall-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-09.md)
- [BUY-37127](/BUY/issues/BUY-37127)
- [BUY-37128](/BUY/issues/BUY-37128)
- [BUY-37129](/BUY/issues/BUY-37129)
- Rich review comment [ed515e27](/BUY/issues/BUY-37101#comment-ed515e27-aee3-4f81-a762-ee27db7beec9)

## Rex

Current focus:
- Keep current API latency and live search health healthy while recovering broad-surface uptime coverage and reducing single-owner bottlenecks.

24-hour movement and required pace:
- Live p95 remains inside target across all tracked markets at `65 ms` fleet average.
- Current live search health should be read as healthy, not `0%`: Rich's query-log review cites `~0.2%` zero-results and `~32 ms` p95 over the last 24h.
- The remaining miss is uptime breadth: canonical API health is `99.878%`, and only `2/9` monitors are `>=99.9%`.

Plan and adjustments being made today:
- Keep the current low-latency state visible.
- Keep broad-surface 30-day uptime deficits visible instead of collapsing the story into a healthy homepage metric.
- Support search benchmark verification without letting the stale harness overwrite the live-health narrative.

Five biggest failures of the day, each with a lesson learned:
1. Broad-surface uptime is still below target.
   Remediation: [BUY-22685](/BUY/issues/BUY-22685) broad monitor recovery.
   Status: in progress.
2. Search benchmark reporting drifted into a false operational narrative.
   Remediation: report split fixed here; [BUY-37423](/BUY/issues/BUY-37423) verifies the harness.
   Status: fixed in report, follow-up open.
3. Search benchmark artifacts are older than the live health read.
   Remediation: rerun after harness verification.
   Status: pending.
4. Single-owner concentration is still creating cross-surface risk.
   Remediation: keep redistribution explicit in owner threads.
   Status: in progress.
5. Monitoring credibility still depends on source clarity.
   Remediation: keep query-log, monitoring-table, and acceptance-harness sources separated.
   Status: fixed in report format.

Current blockers:
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-36587](/BUY/issues/BUY-36587)
- [BUY-37423](/BUY/issues/BUY-37423)

Active work in progress:
- broad-surface uptime recovery
- monitoring-path clarity
- search benchmark verification support

Source of truth:
- [BUY-37127](/BUY/issues/BUY-37127)
- Rich review comment [ed515e27](/BUY/issues/BUY-37101#comment-ed515e27-aee3-4f81-a762-ee27db7beec9)

## Oracle

Current focus:
- Keep the canonical row-growth story visible while acknowledging that merchant breadth, US coverage freshness, and source diversity still lag.

24-hour movement and required pace:
- Canonical DB snapshot at `2026-06-09 06:07:44 UTC`: `n_live_tup=56,866,331`, `reltuples=56,226,800`.
- Current required pace: `2,028,429/day`.
- Merchant proof remains the weaker side of the story: `44,008` exact product-backed merchants on the last exact proof from `2026-06-05`.

Plan and adjustments being made today:
- Keep `reltuples` as the canonical product KPI.
- Keep merchant and market-mix gaps explicit until fresh exact proofs land.
- Do not let product-volume wins erase breadth misses.

Five biggest failures of the day, each with a lesson learned:
1. Merchant breadth is still only `44,008 / 150,000`.
   Remediation: [BUY-22684](/BUY/issues/BUY-22684) exact merchant-backed growth.
   Status: in progress.
2. US coverage is still only `32.57%`.
   Remediation: same Oracle breadth and mix work.
   Status: in progress.
3. Same-day exact merchant refresh did not land in this path.
   Remediation: keep owner accountability on the exact proof path.
   Status: not fixed today.
4. Source diversity still trails the CEO bar.
   Remediation: continue source-mix execution.
   Status: in progress.
5. Growth is still dependent on write-path stability.
   Remediation: [BUY-30590](/BUY/issues/BUY-30590) remains the cap.
   Status: in progress.

Current blockers:
- [BUY-30590](/BUY/issues/BUY-30590)
- [BUY-22684](/BUY/issues/BUY-22684)

Active work in progress:
- canonical growth
- source-mix accounting
- merchant-breadth improvement

Source of truth:
- direct canonical DB reads through `data/.catalog_db_url`
- [docs/daily-product-target-shortfall-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-09.md)
- [docs/daily-source-mix-plan-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-09.md)

## Lyra

Current focus:
- Convert the now-open developer funnel and the June 6 directory burst into sustained querying API keys, traffic, and indexed-page growth.

24-hour movement and required pace:
- Registered API keys are `89`, but the engagement number that matters is `16` distinct querying keys and `74` calls in the last 24h from live PostHog.
- Confirmed live listings are now `~10`, up sharply from the June 5 baseline of `2`.
- Framework integrations are `3 / 5`, but sitemap URLs are only `82`, and June MTD unique visitors are only `73`.

Plan and adjustments being made today:
- Keep registered keys and active querying keys separate.
- Stop reporting tier labels as subscriptions or revenue.
- Push directory and framework work that can move traffic while keeping the GSC and sitemap blockers explicit.

Five biggest failures of the day, each with a lesson learned:
1. Active querying keys are still too low at `16` distinct keys in the last 24h.
   Remediation: unblocked funnel plus pending distribution approval [3e3cffcb](/BUY/approvals/3e3cffcb-476b-44c8-b6f3-24f7485c7c0b).
   Status: in progress.
2. Exact indexed-page truth is still blocked.
   Remediation: [BUY-22745](/BUY/issues/BUY-22745) GSC provisioning.
   Status: blocked.
3. Product and best-of sitemaps are still empty.
   Remediation: SEO execution chain under [BUY-22555](/BUY/issues/BUY-22555) and route/page generation work.
   Status: in progress.
4. Monthly visitors are only `73`.
   Remediation: distribution approvals plus larger sitemap surface.
   Status: in progress.
5. The report previously overstated tier traction by implying subscriptions.
   Remediation: fixed in this report; paid users stated as `0`.
   Status: fixed.

Current blockers:
- [BUY-22745](/BUY/issues/BUY-22745)
- [BUY-29849](/BUY/issues/BUY-29849)
- approval [3e3cffcb](/BUY/approvals/3e3cffcb-476b-44c8-b6f3-24f7485c7c0b)

Active work in progress:
- directory expansion
- key growth
- sitemap/GSC unblock path

Source of truth:
- [BUY-37128](/BUY/issues/BUY-37128)
- [BUY-32955](/BUY/issues/BUY-32955)
- [BUY-22687](/BUY/issues/BUY-22687)

## Reed

Current focus:
- Separate live search health from the 35-query acceptance benchmark, verify the harness path, and keep live usage growth visible.

24-hour movement and required pace:
- Live usage counters at `2026-06-09 06:14:11Z`: `5,205` API queries, `1,891` MCP calls, `95` active agents.
- The last stored acceptance reruns remain `0/35` on both REST and MCP, but those are now explicitly labeled as a separate relevance benchmark.
- Same-day live smoke in [BUY-37129](/BUY/issues/BUY-37129) still saw REST upstream timeouts and MCP relevance/internal-error failures on a tiny sample, so the benchmark is not yet cleared even if live search health is materially better than the report previously stated.

Plan and adjustments being made today:
- Keep live traffic health primary.
- Keep the 35-query benchmark separate and labeled as acceptance/relevance.
- Verify whether the current harness still exercises the live path before using it as a board-facing headline.

Five biggest failures of the day, each with a lesson learned:
1. The stored relevance benchmark is still `0/35` on both surfaces.
   Remediation: [BUY-37423](/BUY/issues/BUY-37423) verifies path and reruns if needed.
   Status: follow-up open.
2. Same-day REST smoke still hit upstream timeouts.
   Remediation: continue search/ingest recovery under [BUY-22731](/BUY/issues/BUY-22731).
   Status: in progress.
3. Same-day MCP smoke still showed one relevance miss and one internal error.
   Remediation: same search-quality chain.
   Status: in progress.
4. Today-so-far usage remains narrow.
   Remediation: keep live usage counters visible and drive adoption through product quality.
   Status: in progress.
5. Only `5/14` roadmap items are banked.
   Remediation: continue Phase 1/2 rollout on the accepted plan path.
   Status: in progress.

Current blockers:
- [BUY-22731](/BUY/issues/BUY-22731)
- [BUY-37423](/BUY/issues/BUY-37423)
- canonical DB/ingestion freshness bottleneck described in [BUY-32074-diagnosis-2026-06-06.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/BUY-32074-diagnosis-2026-06-06.md)

Active work in progress:
- search recovery
- usage growth
- benchmark-path verification

Source of truth:
- [BUY-37129](/BUY/issues/BUY-37129)
- [BUY-22731](/BUY/issues/BUY-22731#document-plan)
- [BUY-37423](/BUY/issues/BUY-37423)

## What Has Been Accomplished

- The June 9 CEO report was corrected the same day in response to Rich's review.
- Live search health is now separated from the 35-query relevance benchmark.
- Subscription framing was removed from `api_keys.tier`; paid users are explicitly `0`.
- "Active users" are now defined as API keys that actually queried in a stated window.
- Failure reporting now includes remediation action, issue, and status again.
- Standing report rules were updated in [docs/daily-ceo-report-format-contract.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-ceo-report-format-contract.md).
- Follow-up issue [BUY-37423](/BUY/issues/BUY-37423) was created for search-harness verification.

## Key Things Needed To Hit June 30 Goals

- Keep Oracle's canonical growth above the required daily pace while improving merchant breadth and US coverage.
- Move indexed visibility from `82` URLs toward a real product-sitemap surface and unblock GSC access.
- Convert the live signup funnel into sustained querying-key growth and materially higher traffic.
- Recover the search relevance benchmark after harness-path verification.
- Improve Rex's broad-surface 30-day uptime to a genuine `>99.9%` platform-wide story.

## Board Blockers Summary

- [BUY-22745](/BUY/issues/BUY-22745): GSC service-account provisioning remains the direct blocker on exact indexed-page truth.
- approval [3e3cffcb](/BUY/approvals/3e3cffcb-476b-44c8-b6f3-24f7485c7c0b): pending since June 5; still blocks the next distribution wave.

## Incidents And Execution Path

- `2026-06-09 06:07 UTC`: canonical DB verification refreshed product evidence.
- `2026-06-09 06:14–06:17 UTC`: same-day Reed and Lyra input packages landed with live usage, listings, and traffic data.
- `2026-06-09 08:42 UTC`: Rich review identified the search, subscriptions, active-user, sourcing, and remediation regressions.
- `2026-06-09 08:50 UTC`: this correction pass republished the report and opened [BUY-37423](/BUY/issues/BUY-37423) for search-harness verification.

## Source Inputs

- [docs/daily-product-target-shortfall-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-09.md)
- [docs/daily-source-mix-plan-2026-06-09.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-source-mix-plan-2026-06-09.md)
- [BUY-37127](/BUY/issues/BUY-37127)
- [BUY-37128](/BUY/issues/BUY-37128)
- [BUY-37129](/BUY/issues/BUY-37129)
- [BUY-32955](/BUY/issues/BUY-32955)
- Rich review comment [ed515e27](/BUY/issues/BUY-37101#comment-ed515e27-aee3-4f81-a762-ee27db7beec9)

Evidence snippets used in this correction pass:

```sql
-- Registered API keys (source path cited in BUY-32955 / BUY-37128)
SELECT COUNT(*) FILTER (WHERE is_active = true) AS registered_active_keys,
       COUNT(*) AS total_keys,
       COUNT(*) FILTER (WHERE created_at >= DATE '2026-06-01') AS june_created,
       COUNT(*) FILTER (WHERE created_at >= now() - interval '24 hours') AS created_24h
FROM api_keys;
```

```text
Live search health source
- Rich's 2026-06-09 08:42 UTC review comment on BUY-37101
- last-24h query_log read: ~0.2% zero-results, ~32 ms p95, MCP 0% zero-results
```

```text
Search relevance benchmark source
- BUY-37129 comment and stored rerun artifacts from 2026-06-06
- REST: buy-22746-harness/runs/acceptance-rerun-rest-2026-06-06/summary.json
- MCP:  buy-22746-harness/runs/acceptance-rerun-mcp-2026-06-06/summary_mcp.json
```

```text
Active querying keys / traffic source
- BUY-37128 live PostHog HogQL read
- last 24h: 16 distinct keys / 74 calls
- June MTD: 73 unique visitors / 1,191 pageviews
```
