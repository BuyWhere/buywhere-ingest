# DAILY CEO REPORT — 2026-06-11

**Report date:** 2026-06-11 UTC  
**Filed by:** Vera (CEO)  
**Filed at:** 2026-06-11T06:40Z (late — see Daily Failure Summary for explanation)  
**Next report:** 2026-06-12 ≈06:00Z

---

## Executive Summary

**Catalog growth is strong but a critical external blocker is killing a major scraper fleet.**

The day closed with **68.0M active products** (n_live_tup, maglev DB, 06:36Z). The closed day 2026-06-10 added **+9,176,195 inserts** (NOT A MISS, 536% of required pace). Today 2026-06-11 is already at **~3.2M inserts in 6 hours** (~535K/hr average), well above the 71K/hr needed. Hex is actively ingesting a staged batch of **3.27M products** (BUY-40800) adding to the count.

**Critical blockers:**
1. **ScraperAPI 403 (since 2026-06-07)** — fleet-wide paralysis on Chewy US, Lazada PH/TH, Shopee SG/MY/VN, Qoo10 SG, Fashion scrapers (Zalora, SHEIN). Seven BrightData migration children are `todo` awaiting execution. This is the largest single growth blocker.
2. **Reed search verification still unrun** — BUY-32954 has been `todo` since 2026-06-07 CEO report; the FTS fix shipped 2026-06-10 (BUY-31962) but the 300-query acceptance test still hasn't run. Search success rate is unknown.
3. **Lyra goal issue (BUY-22687) blocked** — 89 active issues, main goal blocked; SEO 404 fix in progress.
4. **Rex has 99 active issues** — systemic bottleneck; GCP deploy pipeline blocked on SA key restore.

**Biggest remaining June 30 gaps:** Products (32M gap, 20 days), Search success rate (unknown vs 85% target), Merchant count (75K gap), Dev API keys (unmeasured vs 1,000 target).

---

## Daily Failure Summary

The five biggest company/team failures of 2026-06-11:

1. **ScraperAPI key expired 4+ days ago with no fleet-level recovery plan** [operational]  
   *Lesson: External API keys must have expiry monitoring with auto-alert and a 72h remediation SLA. Seven scrapers went dark for days before BrightData migration plan was formulated.*

2. **2026-06-11 CEO report not auto-created by routine** [operational]  
   *Lesson: The daily CEO report routine should self-create a new issue at 06:00Z. The 2026-06-11 slot was never created, forcing Rich to ask on the old issue. The routine needs a watchdog or self-creation trigger.*

3. **Reed search acceptance test BUY-32954 still todo since 2026-06-07 (4 days)** [operational]  
   *Lesson: A P0 test that unblocks the June 30 search success KPI cannot stay in `todo` for 4 days. This needs escalation and a hard deadline.*

4. **Early morning 2026-06-10 throughput gap (00:00–09:00Z near-zero writes)** [operational]  
   *Lesson: The fleet had ~9 hours of near-zero inserts before recovering. The keep-alive system caught up, but the early morning window still shows dispatcher cron gaps (BUY-33694). A restart/watchdog for the overnight window is needed.*

5. **Rex systemic bottleneck at 99 active issues** [operational]  
   *Lesson: Rex is a single point of failure for infra, search, and API delivery. Redistribution to Link/Flux/Bolt was mandated 2026-06-05 but is still only partially executed. Board should confirm redistribution plan is real.*

---

## KPI Summary Table

| KPI | Current | Target | Gap | Blocker |
|---|---|---|---|---|
| Products in catalog | 68.0M | 100M | 32.0M | ScraperAPI 403 (7 fleets dead); maglev disk [BUY-39021] |
| Merchants in catalog | 74,815 | 150,000 | 75,185 | ScraperAPI blocks merchant discovery |
| Directories listed | ~15 est | 25 | ~10 | [BUY-22687] blocked; Lyra's goal paused |
| SEO indexed pages | unknown | 50K | unknown | [BUY-40114] in_progress; GSC data pending |
| Monthly visits | unknown | 25K | unknown | No measurement tooling yet |
| Developer API keys | unknown | 1,000 | unknown | No key registry / measurement |
| Search success rate | unknown | 85% | unknown | BUY-32954 todo (4 days); FTS fix shipped [BUY-31962] |
| API queries/month | unknown | 500K | unknown | No tracking tooling |
| MCP tool calls/month | unknown | 200K | unknown | No tracking tooling |
| API p95 latency | unknown | <100ms | unknown | [BUY-40812] in_progress |
| API uptime | ~99.9% | >99.9% | ~0 | products_created_at_idx INVALID ([BUY-32878]); no p95 monitor |

---

## Vera

**Current focus:** Orchestrating June 30 goal delivery — catalog pace, fleet health, executive coordination, daily CEO reports.

**24-hour movement and required pace:**  
- Catalog grew from 65.5M → 68.0M = +2.5M in 24h (above required 1.6M/day pace ✓)  
- Fleet keep-alive healthy: all 6 active BUY-31716 lanes OK, BUY-30854 deep_page+sustained running  
- Hourly dispatcher manual heartbeat running; auto-cron still broken ([BUY-33694])  
- ScraperAPI 403 triage complete: 7 BrightData migration children created (todo)

**Plan and adjustments today:**  
- File today's CEO report (this document) ✓  
- Monitor BrightData migration execution (BUY-40801/02/03/04/06) — needs Ops to execute  
- Escalate Reed BUY-32954 (stale 4-day todo) to force execution  
- Watch Hex BUY-40800 3.27M ingest completion  

**Five biggest failures today:**  
1. Late CEO report filing (routine not auto-creating 2026-06-11 issue) — *create routine watchdog*  
2. No executor assigned to BrightData migration children — *assign to Ops/Kai immediately*  
3. BUY-33694 dispatcher cron still broken (4+ days) — *escalate to Rex/Ops to fix crontab*  
4. Reed BUY-32954 4-day staleness — *force wake on Reed this heartbeat*  
5. Lyra goal blocked with no clear unblock date — *identify what Lyra needs to unblock BUY-22687*  

**Current blockers:**  
- BUY-33694 dispatcher cron broken (manual heartbeat workaround running)  
- No routine to auto-create daily CEO report issue (manual creation required)  

**Active work in progress:**  
- Fleet keep-alive (BUY-30854, BUY-31716) — routine 476009cc cadence healthy  
- Hourly throughput manual heartbeat — last check 03:00–04:00Z PASS 658K/hr  
- Catalog pace reporting (BUY-38967/38968) — daily shortfall + source-mix plan current  

**Source of truth:** This heartbeat + workspace git log + maglev DB live queries + Paperclip issue API.

---

## Rex

**Current focus:** Infrastructure reliability, search delivery, API uptime, 40 deliverables/month.

**24-hour movement and required pace:**  
- GCP_SA_KEY restore (BUY-40319) in_review — deploy pipeline blocked since ~2026-06-10  
- p95 latency monitoring (BUY-40812) in_progress — new issue filed today  
- NOPASSWD sudoers (BUY-34140) still blocking dist patches — no movement observed  
- SEO indexing recovery (BUY-37745) still todo  
- 99 active issues — pace at 40 deliverables/month requires closing ~3.3 issues/day; current backlog growth rate is unclear  

**Plan and adjustments today:**  
- Unblock GCP_SA_KEY restore so CI/CD can resume  
- Get p95 latency monitor live (BUY-40812)  
- Clear BUY-39083 (routine reassignment Rich action) — this has been waiting for board action  

**Five biggest failures today:**  
1. Deploy pipeline still broken (GCP_SA_KEY) — impacts all code deployments  
2. NOPASSWD sudoers (BUY-34140) still not landed — blocks every dist patch  
3. SEO recovery (BUY-37745) not started — ~900 GSC non-indexed pages losing organic traffic daily  
4. No p95 latency measurement — can't confirm or deny the <100ms target  
5. 99-issue backlog with no triage/redistribution plan — systemic bottleneck  

**Current blockers:**  
- GCP_SA_KEY ([BUY-40319]) — Rich must approve secret restore  
- NOPASSWD sudoers ([BUY-34140]) — requires board-user sudo session  
- [BUY-39083] — routine reassignment requires board PATCH (governance-gated)  

**Active work in progress:**  
- BUY-40812: p95 latency monitoring  
- BUY-40319: GCP_SA_KEY restore (in_review)  
- BUY-32935: batch-D 18 widening  

**Source of truth:** Rex issue list + BUY-22685 weekly checkpoint.

---

## Oracle

**Current focus:** 100M products, 150K merchants, 35 platforms, 50% US coverage.

**24-hour movement and required pace:**  
- Products grew: 65.8M → 68.0M = **+2.2M** (measured in DB; n_live_tup) — above 1.6M/day required pace ✓  
- Today 2026-06-11: already +3.21M inserts in first 6h (00:00–06:02Z) = ~535K/hr average  
- Hex ingesting 3.27M staged batch (BUY-40800) — in_progress  
- ScraperAPI 403 blocking: Chewy US, Lazada, Shopee (SG/MY/VN), Qoo10, Fashion — 7 migration children at todo  
- Closed day 2026-06-10: NOT A MISS at +9,176,195 (536% of required pace)  
- Merchants: 74,815 exact (live count) — 75,185 below 150K target  

**Plan and adjustments today:**  
- Drive BrightData migration children (BUY-40801–40806) — need Ops/Kai execution  
- Watch Hex BUY-40800 3.27M batch complete  
- File daily shortfall report and source-mix plan (BUY-38967/38968) routines  
- Monitor maglev disk (81% at 06:36Z) — BUY-39021 in_progress; BUY-40811 disk watchdog queued  

**Five biggest failures today:**  
1. ScraperAPI 403 not resolved in 4 days — ~7 scraper families dead  
2. WC deep-page supervisor blocked (BUY-40751) — affecting WC deep-page throughput  
3. Merchant count at 74,815 vs 150K target — only 50% to goal with 20 days left  
4. products_created_at_idx still INVALID ([BUY-32878]) — forcing seq-scans and disabling count(*) — DDL blocked by Rule 14  
5. Dispatcher cron broken ([BUY-33694]) — manual-only hourly heartbeat for 4+ days  

**Current blockers:**  
- ScraperAPI 403 ([BUY-40776]) — BrightData migrations pending ([BUY-40801–40806])  
- WC lane supervisor blocked ([BUY-40751])  
- maglev disk emergency ([BUY-39021]) in_progress  
- products_created_at_idx INVALID ([BUY-32878]/[BUY-33973]) — ops-only DDL gated  

**Active work in progress:**  
- BUY-38967/38968: Daily pace + shortfall reporting  
- BUY-40800: Hex 3.27M staged batch ingest  
- BUY-40776: ScraperAPI triage — 7 children at todo  
- BUY-39021: maglev disk emergency  

**Source of truth:** maglev DB n_live_tup (canonical), data/.throughput_state.json, daily-product-target-shortfall-2026-06-10.md.

---

## Lyra

**Current focus:** 25 directories, 5 integrations, 1,000 developer API keys, 50K indexed pages, 25K monthly visits.

**24-hour movement and required pace:**  
- BUY-22687 (Lyra main goal) remains blocked  
- SEO fix (BUY-40114) in_progress — 404s and noindex tags  
- Involve Asia email verification blocked (BUY-40655)  
- TikTok Shop Partner Center (BUY-40628) at todo  
- 89 active issues  

**Plan and adjustments today:**  
- BUY-40114: land 404 fix and noindex corrections  
- BUY-40628: TikTok Shop registration  
- Unblock BUY-40655 (Involve Asia) — needs email verification  

**Five biggest failures today:**  
1. Main goal BUY-22687 blocked — no clear unblock date or owner  
2. Involve Asia affiliate partnership blocked on email verification (BUY-40655) — manual action needed  
3. Developer API keys at zero (unknown) vs 1,000 target — no developer outreach program visible  
4. SEO category 404s still not resolved (BUY-40114 in_progress) — losing indexed pages daily  
5. Monthly visits unmeasured — no analytics dashboard or baseline established  

**Current blockers:**  
- BUY-22687: main goal blocked (details unclear — needs comment/update from Lyra)  
- BUY-40655: Involve Asia email verification blocked  
- BUY-22704: SEO strategy blocked  
- BUY-31198: Central Retail executive outreach blocked  

**Active work in progress:**  
- BUY-40114: SEO 404 fix  

**Source of truth:** Lyra issue list + Paperclip API.

---

## Reed

**Current focus:** 85% search success, 500K API queries/month, 200K MCP tool calls/month, 100 active AI agents, Phase 1+2 roadmap.

**24-hour movement and required pace:**  
- BUY-31962 FTS timeout fix shipped 2026-06-10 — search_products + find_best_price INTERNAL_ERROR resolved  
- BUY-39108 (residual TC-01/02/10 laptop pattern) filed as critical child of BUY-31962 — 504 upstream_timeout still failing  
- BUY-32954 (300-query search acceptance test) still `todo` since 2026-06-07 — **4 days stale**  
- BUY-33696 (search-success acceptance rerun) also stale todo  
- Search success rate: UNKNOWN (baseline not measured)  

**Plan and adjustments today:**  
- Execute BUY-32954 immediately — 300-query acceptance test is the gate for the 85% KPI  
- Close BUY-39108 laptop-pattern investigation  
- BUY-8964 category alias mapping (in_review)  

**Five biggest failures today:**  
1. BUY-32954 (300-query test) 4-day staleness — single most important Reed deliverable is not executing  
2. Residual TC-01/02/10 search failures post-FTS fix — fix was partial, laptop pattern still errors  
3. No API query tracking — 500K/month target cannot be measured  
4. No MCP tool call tracking — 200K/month target cannot be measured  
5. Affiliate revenue pipeline (BUY-13759) still at todo — Phase 1 deliverable not started  

**Current blockers:**  
- No explicit blockers on BUY-32954 — no excuse for 4-day todo  
- BUY-39108: TC-01/02/10 laptop search 504 — root cause investigation  

**Active work in progress:**  
- BUY-40409: Daily competitor intelligence digest (todo)  
- BUY-6896: Smartphone category alias (in_review)  

**Source of truth:** Reed issue list, BUY-22731 goal issue, BUY-31962/39108 search fix chain.

---

## What Has Been Accomplished

- **Catalog growth on pace:** Closed 2026-06-10 at +9.18M inserts (NOT A MISS, 536% of pace); 2026-06-11 already +3.21M in 6h  
- **FTS fix shipped (BUY-31962):** search_products + find_best_price INTERNAL_ERROR resolved 2026-06-10; residual laptop pattern filed as BUY-39108  
- **Fleet keep-alive healthy:** BUY-30854 + BUY-31716 running clean, 6/6 active lanes OK, dead_ticks=0  
- **Hex 3.27M staged batch ingest in flight (BUY-40800)**  
- **ScraperAPI 403 triage done:** 7 BrightData migration children created (BUY-40801–40806)  
- **Daily pace reports current:** shortfall + source-mix plan filed for 2026-06-11 (BUY-38967/38968)  

---

## Key Things Needed To Hit June 30 Goals

1. **Execute BrightData migrations (BUY-40801–40806)** — 7 children at todo; Ops/Kai must execute  
2. **Run Reed BUY-32954 acceptance test** — 300-query search success baseline cannot wait; force execute today  
3. **Fix dispatcher cron (BUY-33694)** — auto-cron broken 4+ days; manual heartbeat is not sustainable  
4. **Restore GCP_SA_KEY (BUY-40319)** — Rex deploy pipeline broken; merge-on-green CI dead  
5. **Measure API queries + MCP calls** — two June 30 KPIs are completely unmeasured; tooling needed this week  
6. **Unblock Lyra main goal (BUY-22687)** — 25 directories + 5 integrations require active execution  
7. **Resolve maglev disk trajectory (BUY-39021)** — DB is 81% of capacity; needs headroom plan  
8. **Merchant discovery plan** — 74,815 vs 150K target; ScraperAPI unblock is step 1 but not sufficient  

---

## Board Blockers Summary

| Blocker | Issue | Owner | Action Needed | Age |
|---|---|---|---|---|
| ScraperAPI 403 — fleet scrape paralysis | [BUY-40776](/BUY/issues/BUY-40776) | Oracle | BrightData migrations must execute (Ops) | 4 days |
| GCP_SA_KEY missing — CI/CD broken | [BUY-40319](/BUY/issues/BUY-40319) | Rex | Rich approve secret restore | 1 day |
| NOPASSWD sudoers not landed | [BUY-34140](/BUY/issues/BUY-34140) | Rex | Board-user sudo session | 3 days |
| Reed BUY-32954 search test 4-day todo | [BUY-32954](/BUY/issues/BUY-32954) | Reed | Force execute — no blocker named | 4 days |
| Routine reassignment (BUY-39083) | [BUY-39083](/BUY/issues/BUY-39083) | Rex | Rich PATCH routine assignee | open |
| products_created_at_idx INVALID | [BUY-32878](/BUY/issues/BUY-32878) | Ops | Ops-only DDL fix; tracker [BUY-33973](/BUY/issues/BUY-33973) | 4 days |
| Lyra main goal blocked | [BUY-22687](/BUY/issues/BUY-22687) | Lyra | Identify and name specific unblock needed | open |
| maglev disk 81% | [BUY-39021](/BUY/issues/BUY-39021) | Ops/Oracle | Disk headroom plan before hitting 90% | open |

---

## Incidents And Execution Path

**Active incidents:**

1. **[BUY-40776] ScraperAPI 403 — fleet-wide paralysis** (critical, blocked)  
   - Impact: Chewy US, Lazada PH/TH, Shopee SG/MY/VN, Qoo10 SG, Fashion scrapers all dead  
   - 7 BrightData migration children at todo: BUY-40798 (Lazada PH), BUY-40801 (Shopee SG), BUY-40802 (Shopee MY), BUY-40803 (Shopee VN), BUY-40804 (Qoo10 SG), BUY-40806 (Fashion/BUY-13025)  
   - Execution path: Ops/Kai must execute migrations; ScraperAPI key replacement also viable  

2. **[BUY-39021] maglev disk emergency** (in_progress)  
   - Disk 81% at 06:36Z, DB size 123 GB  
   - Disk watchdog BUY-40811 queued  
   - Needs headroom plan before hitting 90%  

3. **[BUY-40751] WC deep-page lane supervisor blocked**  
   - Affecting WC deep-page ingest throughput  
   - Escalation path unclear  

4. **[BUY-39108] Reed residual search failures TC-01/02/10** (critical child of BUY-31962)  
   - Laptop product search still returning 504 upstream_timeout  
   - Investigation needed  

5. **[BUY-40319] GCP deploy pipeline broken** (in_review)  
   - CI/CD cannot deploy; GCP_SA_KEY must be restored  

---

## Source Inputs

- **Catalog count:** maglev DB live query (n_live_tup=68,029,968, reltuples=65,912,060) at 2026-06-11T06:36Z via `data/.catalog_db_url` (maglev.proxy.rlwy.net:31310/railway)  
- **Merchant count:** live `count(*) FROM merchants` = 74,815 at 2026-06-11T06:36Z  
- **Throughput:** data/.throughput_state.json — last check 03:00–04:00Z PASS 658,255/hr; today's running total ~3.21M in 6h  
- **Closed day 2026-06-10:** docs/daily-product-target-shortfall-2026-06-10.md — +9,176,195 inserts, NOT A MISS  
- **Source mix plan:** docs/daily-source-mix-plan-2026-06-11.md  
- **Fleet status:** data/buy30854-keep-alive-state.json + data/buy31716-keep-alive-state.json + BUY-39577/39603/39654 keep-alive ticks  
- **Active issue list:** Paperclip API /api/companies/{id}/issues queries for Oracle/Rex/Reed/Lyra agent IDs  
- **Prior CEO report:** [BUY-39054](/BUY/issues/BUY-39054) (2026-06-10, in_review)  
- **DB size:** 123 GB (growing; 81% disk utilization as of 06:36Z)
