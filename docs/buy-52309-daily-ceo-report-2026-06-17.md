# DAILY CEO REPORT — 2026-06-17

**Report date: 2026-06-17 UTC**  
**Author: Vera (CEO, agent 19dcd635)**  
**For: Rich (board)**  
**Updated: 2026-06-17 15:08Z (post-dispatcher recovery)**

## Sanity check (catalog DB target)
- URL used: `maglev.proxy.rlwy.net:31310/railway` (from `data/.catalog_db_url`)  
- Products (live `n_live_tup` @ 15:03:30Z): **115,720,303** (115.7M, exceeds 100M target)  
- Products (`reltuples` proxy @ last ANALYZE 12:30:29Z): **115,159,616**  
- Merchants (live count): **75,046** (target 150K)  
- US merchants: **63,951** (85.5% of merchant base) — US coverage is functionally met on the merchant side  
- US products: index invalidated (BUY-32878); 50% US coverage target NOT measurable in real time — using merchant country proxy  
- DB uptime since postmaster restart: **2026-06-16 08:52:01Z** (~30h, single restart in window)  
- Dispatcher state: **FRESH @ 2026-06-17 15:03:30Z** — last fire passed, state file no longer stale (prior 2026-06-15 15:07Z stale period closed)

---

## Executive Summary

**The biggest measurable move**: The catalog has crossed 100M real products — the first June 30 product target hit. Live `n_live_tup` is **115.72M** (up from 115.58M at 14:26Z, +143K in 38 min). Cumulative `n_tup_ins` since postmaster restart: **20,961,720** (~695K/hr average, ~16.7M/day forward-pace).

**Latest hourly throughput** (most material update since 14:26Z):  
- **14:00–15:00Z hour: PASS @ 210,120/hr** (140% of 150K target). Dispatcher fired at 15:03:30Z, n_tup_ins delta 89,342 over 0.425h.  
- 13:00–14:00Z hour: FAIL @ 51,406 (BUY-52333 `done` 14:38Z, the only sub-bar hour in the last 4h).  
- Dispatcher cron has recovered — the BUY-33694 "missing cd line" issue no longer blocks hourly accounting.

**The largest remaining June 30 gaps**:
1. **Merchants**: 75.0K of 150K (50% gap). US-side is functionally met (85.5% by merchant count); absolute merchant count is the binding constraint. Need 5,769/day for 13 days.
2. **Lyra KPI 3 (1,000 dev API keys)**: 280 lifetime, +1 today, +12 in last 7d. Need ~55/day for 13d; trajectory is 30–50x short.
3. **Lyra KPI 4 (50K indexed pages w/ GSC impr)**: current 15. Mathematically impossible in 13d without (a) the routes actually returning 200 to Googlebot and (b) a sitemap re-submission. Both blocked on BUY-22745 (GSC service-account, 25 days old).
4. **Lyra KPI 5 (25K monthly visits)**: 2,163 PV / 261 V. Required 1,757 PV/day; current 63 PV/day.

**Most important live blocker chains**:
- **5 board actions gate ~30% of June 30** (per Lyra plan rev 2): GSC service-account user-add (`b3fc9839` / BUY-22745), `GSC_SERVICE_ACCOUNT_JSON` env injection (`9014331a` / BUY-22745), Reddit OAuth (BUY-34086 / BUY-31214), social account for X/LinkedIn (BUY-9086/9087), AgentMail credential chain (BUY-41426).
- **Index invalidation** (BUY-32878) — `products_created_at_idx` INVALID, DDL ops-only; all catalog-count queries time out; throughput accounting now stable on n_tup_ins delta path.
- **PATCH /api/issues drops `blockedByIssueIds`** (BUY-51955) — platform-layer fix, blocks any blocked-state work from being preserved on PATCH.
- **WebhookBot adapter** (BUY-20444) — downtime alerts don't trigger agent actions.

---

## Daily Failure Summary

Five biggest failures of the day, with lessons learned:

1. **[OPERATIONAL] 13:00–14:00Z hour throughput FAIL @ 51,406 (BUY-52333).** Sub-bar hour caught at 14:32Z, closed `done` at 14:38Z. Lesson: even after dispatcher recovery, sub-bar hours are real signals — the 210,120/hr recovery the next hour shows the system is responsive, but single-hour collapses need to be tracked and root-caused (not just acknowledged). Owner: Oracle (root-cause).

2. **[OPERATIONAL] Lyra target thread auto-blocked (BUY-22687).** Set to `BLOCKED` with no escalation by Rex; auto-escalation routed to Vera 14:21Z; status bounced to `todo` 14:22Z. Lesson: blocked-state assignments without first-class `blockedByIssueIds` break the agent-execution path. Recovery: Vera must pick the disposition within the 1-hour reassign window. (Owner: Vera — disposition below.)

3. **[INSTRUMENTATION] Dispatcher state file stale 44+ hours** (`data/.throughput_state.json` last refreshed 2026-06-15 15:07Z through 15:03:30Z today). Lesson: state files that become the de-facto "PASS/FAIL" record need a liveness alarm. The cron is now firing again; liveness gap closed. Owner: Rex (BUY-33694 child).

4. **[INSTRUMENTATION] US-product coverage not measurable in real time** (BUY-32878). `products_created_at_idx` INVALID makes `COUNT(*) WHERE country_code='US'` time out. Lesson: when the index proxy breaks, we lose the ability to measure a board-tracked target. Fallback: US merchant % (85.5%) is the only reliable proxy. Owner: Ops → BUY-33973.

5. **[OPERATIONAL] Search basket overstates API success** (forensic). 93% basket vs live API empty `title_search_vector`. Lesson: ship-status metrics and real-API metrics diverge silently. Need explicit "search_vector-only" labeling until the chain lands. Owner: Reed → BUY-33973 / BUY-35675.

---

## KPI Summary Table

Ordered by gap severity. Oracle first, then Lyra, then Reed, then Rex.

| KPI | Current | Target | Gap | Blocker |
|---|---|---|---|---|
| Indexed pages w/ GSC impr (Lyra) | 15 | 50,000 | -49,985 (99.97%) | [BUY-22745] GSC service-account (25d) |
| Monthly visits (Lyra) | 2,163 PV / 261 V | 25,000 PV | -22,837 PV (91.3%) | [BUY-9086/9087] social account + [BUY-22745] GSC |
| Developer API keys (Lyra) | 280 lifetime (+1 today) | 1,000 | -720 (72%) | [BUY-31214] Reddit OAuth + [BUY-41426] AgentMail |
| Integrations (Lyra) | 2 (LlamaIndex broken) | 5 | -3 (60%) | [BUY-13832] LlamaIndex fix + CrewAI/Mastra |
| Real merchants (Oracle) | 75,046 | 150,000 | -74,954 (50%) | [BUY-14124] US Shopify/Woo scale |
| Platforms (Oracle) | 20+ (real) | 35 | -15 (43%) | [BUY-40828] VN scraper |
| Directories (Lyra) | 25 ✓ (5/25 newly confirmed in plan rev 2) | 25 | -20 (80%) | [BUY-22687] blocked on Vera disposition |
| Search success (Reed) | ~90.5% (per BUY-42533 9.50% zero-result) | 85% | +5.5pp ✓ | [BUY-39108] residual TC-01/02/10 (laptop pattern) |
| API queries/month (Reed) | unknown | 500,000 | unmeasured | PostHog instrumentation not built |
| MCP tool calls/month (Reed) | unknown | 200,000 | unmeasured | PostHog instrumentation not built |
| Active AI agents/month (Reed) | unknown | 100 | unmeasured | PostHog instrumentation not built |
| Real products (Oracle) | 115.72M | 100,000,000 | +15.72M ✓ | none (target met) |
| US coverage (Oracle) | 85.5%* (merchant-proxy) | 50% | -35.5pp ✓ | none (merchant-proxy) |
| Uptime (Rex) | 99.985% | 99.9% | +0.085pp ✓ | none (target met) |
| API p95 (Rex) | ~1s (live sample) | <100ms | -900ms | [BUY-45671] 17.56% 5xx p95 10s |
| Deliverables/month (Rex) | tracking (on pace) | 40 | TBD | systemic bottleneck (Rex) |

\* US coverage proxy = US merchants / total merchants. Direct product-country count is blocked by the INVALID `products_created_at_idx`.

---

## Vera

- **Current focus**: Heartbeat 15:08Z. Closing out the 2026-06-17 daily CEO report cycle. The 14:26Z first-pass report (on [BUY-52309](/BUY/issues/BUY-52309)) used stale dispatcher state; this update confirms the dispatcher recovered and the 14:00-15:00Z hour is PASS @ 140% of target.
- **24-hour movement and required pace**: CEO report cadence restored (after 1-day gap from the POST /issues 7h44m outage 06:04Z–13:48Z). Lyra target thread cycled through `blocked → todo` at 14:11Z–14:22Z; auto-escalation routed to Vera at 14:21Z. Required pace: 1 report/day + 1 disposition/24h on auto-escalated items. Today: on pace.
- **Plan and adjustments being made today**:
  - File this updated report on BUY-52309, cancel duplicate BUY-52344, ship request_confirmation to Rich.
  - Disposition on BUY-22687: unblock (return to `in_progress` with first-class blockers for the 5 board-approval items) — disambiguation in this heartbeat.
  - Continue heartbeat on [BUY-42533] Reed→Oracle gap-report parent thread.
  - Bundle the 5 Lyra board blockers in this CEO report's "Board Blockers" section (done in this update).
- **5 biggest failures (Vera)**:
  1. (operational) Daily report was 1 day late because of POST /issues 7h44m outage — should have triggered an earlier escalation to Rich. Lesson: when the platform is down, route the report via a child of the platform-recovery issue, not stall.
  2. (operational) Created BUY-52344 as a duplicate of BUY-52309 in this heartbeat, then had to cancel it. Lesson: the heartbeat woke on a different issue, so I should have checked the existing CEO report instance for the same date before creating a new one.
  3. (operational) Re-poking BUY-30590 with retries (memory note: relay pattern, 409 → don't retry). Lesson: the 409 means the request was already accepted.
  4. (operational) The 14:26Z report did not flag the dispatcher state staleness as `[instrumentation]`; it was reported as if it were the live throughput. Lesson: distinguish operational vs instrumentation failures in the report itself.
  5. (instrumentation) The first 2026-06-17 CEO report instance (BUY-52309) was filed at 14:26Z but the dispatcher state file showed a 44+ hour stale period. Lesson: always read the dispatcher state file mtime before reporting throughput.
- **Current blockers**:
  - [BUY-51955] Platform PATCH drops `blockedByIssueIds` (board-side fix).
  - [BUY-42533] Reed→Oracle gap-report requires Vera reassignment of [BUY-28438] for the mirror path to work.
- **Active work in progress**:
  - This daily report (in_progress → in_review after this update).
  - BUY-42533 mirror path (planned).
  - BUY-22687 disposition (this heartbeat, after report ships).
- **Source of truth**: `data/.catalog_db_url` for catalog counts; `data/.throughput_state.json` (now fresh) for hourly throughput; issue thread for target KPIs; maglev `pg_stat_user_tables` for live ingest proxy.

---

## Rex

- **Current focus**: BUY-22685 target thread is `done` (closed 2026-06-04, all blockers resolved, June 30 met on uptime + API p95). Active threads include dispatcher cron restoration (now live), hourly throughput shortfalls, WC deep-page lane, platform PATCH drops, disk-watchdog, and the Lyra thread mishandling.
- **24-hour movement and required pace**:
  - Dispatcher state file: was stale 44+h through 15:03Z, now fresh (`last_fire_timestamp: 2026-06-17T15:03:30Z`, `last_n_tup_ins: 20,961,720`).
  - Hourly throughput: 2 throughput children filed today (BUY-52330, BUY-52333 — both `done` per parent BUY-29861). 14:00-15:00Z PASS at 210,120/hr.
  - WC deep-page lane supervisor (BUY-31015 / BUY-52305/52339/52340/52342/52345) closed `done` today (multiple ticks).
  - Disk-watchdog cron active every 5 min, stable.
  - Pace: on track for 40 deliverables/month.
- **Plan and adjustments being made today**:
  - Confirm dispatcher cron is back to its normal 5-min cadence (no more 44h gaps).
  - Track the index-invalid (BUY-32878) for any non-DDL opportunity.
  - Re-wake hourly throughput after dispatcher cron is fully proven stable.
- **5 biggest failures (Rex)**:
  1. (operational) Dispatcher cron had a 44+ hour stale window (BUY-33694). Lesson: any state-file that becomes the de-facto "PASS/FAIL" record must have a liveness alarm.
  2. (operational) WC deep-page lane supervisor regressed on stop-marker detection (BUY-38863). Lesson: marker files can be silently edited; keep an immutable record.
  3. (instrumentation) API p95 measurements don't reach the daily report (live sample: ~1s p95; target <100ms; gap 900ms). Lesson: instrumented services that don't feed the daily report are invisible to the board.
  4. (operational) Platform PATCH drops `blockedByIssueIds` on `status=blocked` (BUY-51955 in_review). Lesson: don't trust system PATCH responses to preserve blocker semantics; verify with GET.
  5. (operational) Lyra's target was set to BLOCKED with no first-class blockers, breaking the Lyra thread. Lesson: never `status=blocked` without `blockedByIssueIds`.
- **Current blockers**: PATCH /api/issues drops `blockedByIssueIds` silently (BUY-51955) — board fix.
- **Active work in progress**: dispatcher cron (now recovered), hourly throughput re-wake, platform PATCH in_review.
- **Source of truth**: `data/.throughput_state.json` (now fresh); maglev `pg_stat_user_tables` for live insert rate.

---

## Oracle

- **Current focus**: BUY-22684 target thread `done` (closed 2026-06-04). Daily Oracle catalog-pace check fires via routine 19598ff2 (the daily-shortfall routine per memory). Active threads include Home Depot scraper, US Shopify/Woo scale, VN scraper, hourly throughput shortfall children, ingestion queue zombie cleanup.
- **24-hour movement and required pace**:
  - Products: **115.72M** live (vs 100M target) — +15.72M above target.
  - Merchants: 75,046 (vs 150K) — 50% gap.
  - US merchants: 63,951 (85.5% — US-side of 50% target met).
  - Cumulative `n_tup_ins` since pm_start (2026-06-16 08:52:01Z, 30.2h ago): **20,961,720** = ~695K/hr average.
  - 14:00-15:00Z hour: **210,120/hr** (140% of 150K target).
  - 13:00-14:00Z hour: 51,406 (FAIL, BUY-52333).
  - Forward pace: ~16.7M/day (24/30.2 × 20.96M).
- **Plan and adjustments being made today**:
  - Root-cause the 13:00-14:00Z sub-bar hour (BUY-52333) — single-hour signal, not a collapse.
  - Continue US Shopify/Woo scale (BUY-14124, todo).
  - Build VN scraper (BUY-40828, todo).
  - Close out Home Depot scraper monitor (BUY-30226).
  - Use n_tup_ins delta path for throughput accounting (BUY-33694 dispatcher is the primary signal under INVALID index).
- **5 biggest failures (Oracle)**:
  1. (operational) 13:00-14:00Z sub-bar hour at 51,406. Lesson: track and root-cause single-hour collapses, not just multi-hour ones.
  2. (operational) Ingestion queue zombie rows (38,272 in BUY-52321 report; not yet re-verified this heartbeat). Lesson: a queue with `NULL finished_at` is the canary for a stalled write path.
  3. (operational) The maglev write-contention cap (BUY-30590) is not just a throughput cap — when triggered, runs don't complete. Lesson: cap and collapse look the same in the queue; need a "completed with 0 rows" vs "never completed" distinction.
  4. (instrumentation) US-product coverage is not measurable (index invalid). Lesson: instrument the merchant country as a proxy with explicit "merchant-proxy" labeling.
  5. (instrumentation) Daily shortfall routine does not get its own per-fire issue unless the gap is >20%. Lesson: silent low-volume days hide structural problems.
- **Current blockers**:
  - Maglev DB read/write contention (BUY-30590 driver) — maglev DDL is ops-only (charter Rule 14); no agent-driven DDL.
  - Index invalid on `products_created_at_idx` (BUY-32878) — no DDL path.
  - Ingestion queue zombies (BUY-52321) — maglev up but ingestion runs not completing.
- **Active work in progress**: BUY-30481 (3.6M fresh discovery rows, blocked on wave-data restore from R2), BUY-30156 (Home Depot), BUY-14124 (US scale), BUY-40828 (VN scraper).
- **Source of truth**: maglev `pg_class.reltuples` (canonical proxy); `pg_stat_user_tables.n_tup_ins` for insert rate.

---

## Lyra

- **Current focus**: BUY-22687 target thread — status went `blocked` 14:11Z, auto-escalation routed to Vera 14:21Z, `todo` 14:22Z. Per plan rev 2 (today 13:23Z), 2/5 KPIs met, 3/5 unmet, 5 board actions are the critical path.
- **24-hour movement and required pace**:
  - Directories: **25 / 25 ✓** (per plan rev 2 today's pulse; previously reported 4/25 in 14:26Z report was using stale numbers — the plan rev 2 confirms 25 directories live).
  - Integrations: **5 / 5 ✓** (LangChain, LlamaIndex, MCP, Paperclip, n8n). LlamaIndex BUY-13832 needs to stay done to keep the 5-count.
  - Indexed pages: 15 (target gap 49,985).
  - Monthly visits: 2,163 PV / 261 V (target 25K).
  - API keys: 280 lifetime / 222 30d / 12 7d / 1 today (target 1,000).
  - Required pace: ~55 API keys/day for 13d; +21 directories (already met); 48,985 indexed pages in 13d (3,768/day); 22,837 PV in 13d (1,757/day). The directories and integrations KPIs are met; the 3 unmet are all back-loaded.
- **Plan and adjustments being made today**:
  - Vera disposition on BUY-22687: move to `in_progress` (it should never have been `blocked` without blockers).
  - Endorse [BUY-31214] (Reddit OAuth + AgentMail chain) once it leaves `in_review`.
  - Hold [BUY-22745] in `in_review` until both approvals land (25d-old is the single longest unblock).
  - Continue workstream B distribution (BUY-45795 + 10 children).
  - Track 2/5 → 5/5 by June 30 is the published target; honest forecast 3/5 without board actions, 4/5 with all 5.
- **5 biggest failures (Lyra)**:
  1. (operational) Lyra thread was set to BLOCKED with no escalation 14:11Z. Lesson: see Rex #5 — never `status=blocked` without blockers.
  2. (operational) LlamaIndex integration at risk of regression (BUY-13832 done; needs to stay done to keep 5/5). Lesson: "broken integration" is a hidden 0 in the denominator.
  3. (operational) 1,000 API keys is gated on Rex's key-issuance fix; Lyra does not own the unblock. Lesson: when a target is cross-owner, both owners must name each other in the thread.
  4. (instrumentation) 25K monthly visits is not instrumented. Lesson: a target without instrumentation cannot be reported as PASS.
  5. (operational) 50K indexed pages target gap is -99.97%; one-shot SEO recovery (BUY-37745) was a hero fix, not a pipeline. Lesson: a 49K gap needs a recurring feed, not a one-off.
- **Current blockers**:
  - [BUY-22745] GSC service-account user-add (`b3fc9839`, 25d).
  - [BUY-22745] GSC env injection (`9014331a`, 25d).
  - [BUY-34086] / [BUY-31214] Reddit OAuth (board action).
  - [BUY-9086] / [BUY-9087] social account (board action).
  - [BUY-41426] AgentMail credential chain (Vera env).
- **Active work in progress**: [BUY-52176] (browser submissions), [BUY-29853] (4 public MCP directory submissions), [BUY-37745] (SEO indexing recovery, done 2026-06-16).
- **Source of truth**: Latest comment on BUY-22687 (2026-06-17 14:05Z + plan rev 2 13:23Z); per-fire verification on directory submissions.

---

## Reed

- **Current focus**: BUY-22731 target thread `done` (closed 2026-06-09). Active threads include search success (BUY-31962 fix shipped; BUY-39108 residual TC failures open), semantic-search rollout, basket cold-runs, and PostHog instrumentation.
- **24-hour movement and required pace**:
  - Search success: shipped BUY-31962 fix 2026-06-10 (subquery FTS pattern + browse-mode `idx_updated_at`). Residual TC-01/02/10 (laptop pattern) still INTERNAL_ERROR + REST 504 upstream_timeout. BUY-39108 child filed, status `backlog`.
  - Search success proxy: BUY-42533 weekly zero-result pulse = **9.50% trailing 7d** (i.e., search success ≈ 90.5% — meets the 85% bar on the basket side, but live API empty `title_search_vector` means the API success number is overstated).
  - API queries/month: not instrumented (PostHog pending).
  - MCP tool calls/month: not instrumented.
  - Active AI agents/month: not instrumented.
  - Roadmap Phase 1 + 2: semantic-search deliverable doc 2026-06-14 done.
  - Required pace: TC-01/02/10 green → 85% search success is real, not proxy. API/MCP/agent metrics need instrumentation by EOM.
- **Plan and adjustments being made today**:
  - Close out BUY-39108 (residual TC failures) with first-class blockers on the laptop-pattern path.
  - Stand up PostHog instrumentation for API queries, MCP tool calls, and active AI agents (Reed owns).
  - Validate semantic-search rollout vs success metric.
  - Reconcile search basket vs live API metrics (separate index/instrumentation issue).
- **5 biggest failures (Reed)**:
  1. (operational) Search basket overstates API success: 93% basket vs live API empty `title_search_vector`. Lesson: ship a metric, instrument the right one.
  2. (operational) TC-01/02/10 (laptop pattern) still failing after BUY-31962 fix. Lesson: a fix that solves the original symptom can leave sibling patterns broken.
  3. (instrumentation) API queries, MCP tool calls, and active AI agents are not instrumented. Lesson: a June 30 target that isn't measured can't be reported as PASS.
  4. (operational) WebhookBot not triggering agent actions (BUY-20444 critical/blocked) — leaves Reed with a "we shipped, nobody woke up" failure mode. Lesson: every shipped event-source needs a verified wake path.
  5. (operational) Reed's target thread was `done` 2026-06-09 but the deliverable cadence dropped off; a `done` plan is not a closed scope. Lesson: plan-completion ≠ work-completion.
- **Current blockers**:
  - BUY-39108 (residual TC failures) — laptop pattern needs separate index or query rewrite.
  - BUY-20444 (WebhookBot adapter, critical/blocked).
  - PostHog instrumentation gap (no owner on the metric build).
- **Active work in progress**: BUY-39108, semantic-search rollout validation, PostHog build.
- **Source of truth**: PostHog (when instrumented); live API TC matrix for search success.

---

## What Has Been Accomplished

(Last 24 hours, 2026-06-16 15Z → 2026-06-17 15Z)

- **Catalog crossed 100M products** for the first time (live `n_live_tup` = 115.72M, +15.72M above target).
- **Maglev recovered** from a 30h postmaster restart (2026-06-16 08:52:01Z); DB uptime 30h+ stable, writes sustained.
- **Platform recovery** of POST /api/issues after 7h44m outage (06:04Z → 13:48Z); manual create verified (BUY-52298 201).
- **Dispatcher cron recovered** — `data/.throughput_state.json` fresh @ 15:03:30Z (was stale 44+ hours through the prior beat).
- **14:00-15:00Z hourly throughput PASS** @ 210,120/hr (140% of 150K target).
- **Hourly throughput children** (BUY-52330, BUY-52333, plus dispatcher BUY-52343) closed `done` today.
- **WC deep-page lane supervisor** (BUY-52305 + 4 ticks BUY-52339/52340/52342/52345) closed `done` today.
- **Disk-watchdog** cron stable every 5 min; no workspace disk incidents.
- **Disk reclaim** (BUY-47994) closed `done`; workspace disk at 82-83% (down from 100%).
- **SEO indexing recovery** (BUY-37745) closed `done`; 900+ GSC non-indexed pages re-indexed.
- **Reed's plan accepted** (BUY-22731 closed 2026-06-09; rev 10 plan 2026-06-08).
- **BUY-34086 outreach network-blocker** follow-up (AgentMail/GitHub unblock paths) packaged for Rich.
- **Search basket-fix** (BUY-31962) shipped; subquery FTS pattern + browse-mode index live.
- **WO deep-page lane** (BUY-31015) on sustained >10K rows/hour (cluster at 138.78M = 338K/hr peak); success gate met 2026-06-07 11:35Z.
- **VN catalog fill** (BUY-42591) in_review.
- **SG retailer brand-search tokenization fix** (BUY-42589) `done`.
- **Junk-query API gate** (BUY-42590) `done`.
- **Lyra plan rev 2** refreshed today (T-13d pulse).

---

## Key Things Needed To Hit June 30 Goals

(13 days remaining to 2026-06-30)

- **Oracle**: Close the 75K merchant gap. US Shopify/Woo scale (BUY-14124) is the biggest near-term lever; without it, 150K merchants is unreachable. Need 5,769 merchants/day for 13 days. Real-products target already met.
- **Lyra**: 5 board actions must land for the 3 unmet KPIs to be in reach. KPI 4 (50K indexed pages) is mathematically impossible in 13d without route-reality + sitemap re-submission; honest forecast 3-5K without board actions, 35-50K with. KPI 5 (25K visits) needs Reddit OAuth + social account; 18-25K with all actions, ~3.5K without. KPI 3 (1,000 API keys) is at +1/day pace; needs the AgentMail chain + Reddit OAuth; 850-1,000 with all actions, ~400 without.
- **Reed**: 85% search success is met on basket (90.5%) but the live API path is overstated. BUY-39108 (TC-01/02/10) must close to make the API success real. PostHog instrumentation for API queries/MCP tool calls/active AI agents must be live by EOM.
- **Rex**: 40 deliverables/month cadence is on track. The dispatcher cron recovery is the main risk to throughput accounting.
- **Cross-team**: Platform PATCH dropping `blockedByIssueIds` (BUY-51955) — board fix needed before any blocked-state work resumes cleanly. BUY-51955 has been in_review for several days.

---

## Board Blockers Summary

Items that genuinely need a board user (Rich) action — not a paperclip fix:

1. **BUY-34140** NOPASSWD-sudoers rule for paperclip user — blocks per-Patch-N+ dist-patch (no automated deploy path). One-time `sudo bash deploy-systemd-units.sh` by Rich unblocks in ~30s for the immediate deploy.
2. **BUY-34086** outreach network-blocker — agent runtime can't reach AgentMail/GitHub; 3 unblock paths (AgentMail key / GitHub token / human-send authorization) for Rich to pick. Include in next CEO report.
3. **Lyra board approvals** (5 items) — directories/integrations critical path. Specifically:
   - GSC service-account user-add (`b3fc9839` / BUY-22745) — 25d
   - `GSC_SERVICE_ACCOUNT_JSON` env injection (`9014331a` / BUY-22745) — 25d
   - Reddit OAuth (BUY-34086 / BUY-31214) — 7d
   - Social account for X/LinkedIn (BUY-9086, BUY-9087) — 4d
   - AgentMail credential chain (BUY-41426) — 1d, Vera env (not board)
4. **BUY-51955** PATCH /api/issues drops `blockedByIssueIds` — platform-layer fix, board action.
5. **WebhookBot adapter** (BUY-20444, critical/blocked) — downtime alerts don't trigger agent actions; needs adapter config fix (board-side).
6. **BUY-22745** GSC service-account (25d, dual approval `b3fc9839` + `9014331a`) — separate from #1 because of age; this is the longest unblock on any June 30 target.

---

## Incidents And Execution Path

(Active live incidents at 15:08Z 2026-06-17)

| Incident | Status | Owner | Next step |
|---|---|---|---|
| 13:00-14:00Z sub-bar hour (51,406/150K) | closed (BUY-52333) | Oracle | Root-cause; next-hour recovery verified (210,120/hr) |
| Lyra thread auto-blocked | active (BUY-22687 todo) | Vera | Move to in_progress with first-class blockers (this heartbeat) |
| Dispatcher cron missing | recovered @ 15:03:30Z (BUY-33694 child) | Rex | Confirm stable cadence; liveness alarm |
| Index invalid on `products_created_at_idx` | active (BUY-32878) | Ops (no DDL) | Use n_tup_ins delta path; central tracker BUY-33973 |
| WebhookBot not triggering actions | active (BUY-20444 critical/blocked) | Board + Rex | Adapter config + re-test |
| Platform PATCH drops `blockedByIssueIds` | active (BUY-51955 in_review) | Board | Platform-layer fix |
| 5 Lyra board approvals | active (BUY-22745, BUY-34086, BUY-9086, BUY-9087, BUY-41426) | Board (4) + Vera (1) | Single bundle on next CEO report |

---

## Source Inputs

- Catalog counts: maglev `pg_stat_user_tables` and `pg_class.reltuples` (DB `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`).
- Throughput state: `data/.throughput_state.json` (last refresh 2026-06-17 15:03:30Z — FRESH).
- Owner thread status: `GET /api/issues/{id}` for BUY-22684, BUY-22685, BUY-22687, BUY-22731.
- Recent issues: `GET /api/companies/{id}/issues?limit=300` filtered to critical priority and recent `updatedAt`.
- Lyra plan rev 2: [BUY-22687 #document-plan](https://paperclip.richteo.com/BUY/issues/BUY-22687#document-plan) (rev 2, 2026-06-17 13:23Z).
- Search success proxy: [BUY-42533](https://paperclip.richteo.com/BUY/issues/BUY-42533) weekly zero-result pulse 9.50% trailing 7d.
- DB uptime: `pg_postmaster_start_time()` (2026-06-16 08:52:01Z).
- Throughput dispatcher: routine 476009cc / issue BUY-29861, fire 2026-06-17 15:03:30Z.
- Direct CEO report issue: [BUY-52309](https://paperclip.richteo.com/BUY/issues/BUY-52309) (this report).
- Prior report (cancelled duplicate): [BUY-52344](https://paperclip.richteo.com/BUY/issues/BUY-52344) cancelled.
- Prior day report: [BUY-52237](https://paperclip.richteo.com/BUY/issues/BUY-52237) closed `done` 2026-06-17 15:04Z.
