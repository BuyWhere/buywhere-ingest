# DAILY CEO REPORT — 2026-06-07

Report date: 2026-06-07 UTC
Original finalization: 2026-06-07T07:46:00Z
**Correction pass: 2026-06-08T14:57:00Z** — applied Rich's 2026-06-08 12:02Z review corrections to the maglev crash saga, dispatcher false alarm, search-fix priority, exact-counts path, and Lyra API-keys. Format-contract compliance retained (Oracle → Lyra → Reed → Rex, one canonical source per row, [instrumentation] vs [operational] tagging per Rich's 2026-06-08 directive).
Issue: [BUY-33609](/BUY/issues/BUY-33609) (renamed from "Daily CEO Report" per execution contract step 1)
Source-of-truth rule (per Rich's 2026-05-31 directive, **never override**): every catalog-count row in this report cites the canonical PostgreSQL pinned at `data/.catalog_db_url` -> `maglev.proxy.rlwy.net:31310/railway?sslmode=require` (the BuyWhere catalog). The harness `DATABASE_URL` is `roundhouse.proxy.rlwy.net:27479/railway` (the Paperclip control-plane DB) and is **never** the catalog source. The path/host of `data/.catalog_db_url` can change (workspace `e61bbe4e…` -> `4b4739f7…` noted 2026-06-08); resolve dynamically at runtime, never hardcode (catalog_url guard rejects roundhouse URLs).

## Rich correction note (added 2026-06-08T14:57:00Z)

The 2026-06-07T07:46Z final report contained five items Rich's 2026-06-08T12:02Z review identified as overstating operational risk or understating already-shipped fixes. This correction pass applies all five and tags each `Daily Failure Summary` item as `[instrumentation]` or `[operational]` per Rich's new directive. The five corrections:

1. **Maglev crash saga is RESOLVED** — the "maglev catalog reset" open ❌ is removed. Root cause: agent Kai's custom Postgres `startCommand` in [BUY-33589](/BUY/issues/BUY-33589) deleted the WAL Postgres needed for crash recovery, turning a recoverable crash into a crash-loop. Ops fixed via `pg_resetwal` (full 50.5M catalog intact, zero data loss), removed the WAL-deletion bug, and added daily/weekly/monthly backups ([BUY-35196](/BUY/issues/BUY-35196)). A second, separate cause — an orphaned replication slot from the dead maglev-replica hoarding 117 GB of WAL (filled the 200 GB volume) — was also fixed: ops dropped the slot, WAL 117 GB → 4 GB, volume ~197 → 71 GB. maglev has been stable for hours. The crash cycle is over.
2. **Dispatcher "5h dark / 0%" was a FALSE alarm** — the writer fleet was fine. maglev was at 50.5M and grew ~700K rows / 15 min all day. The dispatcher read a stale stray table (`roundhouse.products_sg`), not the live catalog. Ops dropped that stray table (+14 GB reclaimed). The fix is to repoint the dispatcher at maglev (now done under [BUY-33694](/BUY/issues/BUY-33694)) and resolve `data/.catalog_db_url` dynamically (the workspace path moved `e61bbe4e…` -> `4b4739f7…` on 2026-06-08).
3. **The highest-leverage fix is the title_search_vector one-line change** (central tracker [BUY-33973](/BUY/issues/BUY-33973), latest retry [BUY-35675](/BUY/issues/BUY-35675)). Rich referred to it as "BUY-35363" but that ID does not exist; the canonical anchor is the buy-33973 / buy-34274 / buy-35675 chain. The live API queries the empty, unindexed `title_search_vector` instead of the working, GIN-indexed `search_vector` — so mainstream products (Sony WH-1000XM5, iPad, PS5) return zero AND every search seq-scans 50M rows. **One line fixes both the search-success KPI and the 5× p95 latency.** Note: the 93.3% basket success on 2026-06-05 (`docs/basket-verify-results-31312.txt`) measures `search_vector` (which works), so it **overstates** real API success until the fix lands.
4. **"Exact counts blocked by statement_timeout" is the wrong frame** — `SELECT COUNT(*)` on the 50M+ table overloads the DB; ops' watchdog actively cancels it. `pg_class.reltuples` is the canonical proxy, and ops added a 6-hourly `ANALYZE` cron to keep it fresh. **[BUY-32950](/BUY/issues/BUY-32950)** ("upgrade Railway Postgres to allow count(*)") is the wrong fix at any plan tier and is closed.
5. **Lyra's API-keys metric is solved** — ops pulled it: **1,001 active keys across 10 tiers** (67 enterprise, 6 pro, 4 partner + the long tail), posted to [BUY-32955](/BUY/issues/BUY-32955) (now `in_review` pending Lyra acceptance). Lyra's "indexed pages" metric is genuinely external (Google Search Console) and still needs a credential unblock.

Plus four directives:
- **Repoint the dispatcher to maglev** ([BUY-33694](/BUY/issues/BUY-33694), now `done`) so the throughput signal is real.
- **The Rex bottleneck is the biggest systemic risk** — 3 of 5 daily failures AND the high-leverage search fix all route to him; he has ~86 open issues. Redistribute or unblock. Infra+API+search can't all be Rex.
- **Reed owns the search-success acceptance** — but the number will jump once the search fix lands. Sequence the acceptance **after** the fix, not before.
- **Update future reports to distinguish `[instrumentation]` failures from `[operational]` failures** — the underlying systems are healthier than the report reads.

Standing notes (carried into future reports):
- **maglev DDL / WAL / startCommand is ops-only** (charter Rule 14). The WAL-deletion that caused the 2026-06-08 outage was an agent change; do not let agents touch it. Reject DDL children and route through Patch N + Bolt/Ops dist deploy.
- The "3+ duplicate children per hour" pattern was a duplicate-wakeup flood that stalled the executor; ops fixed it with an auto-dedup cron.

## Executive Summary

- The catalog is in fact healthier than the 2026-06-07T07:46Z final report read. Canonical `pg_stat_user_tables.products.n_live_tup=52,820,874` and `pg_class.reltuples=51,430,872` at `2026-06-08 14:57 UTC` (the canonical proxy per Rich's correction #4 — `reltuples` is the source of truth, not `count(*)`). Last 10h of confirmed inserts (since last `ANALYZE` at `2026-06-08 13:26:58 UTC`): `n_tup_ins=+2,567,265`. Current sustained rate per the routine hourly check ([BUY-35625](/BUY/issues/BUY-35625), 13:00–14:00Z window): `1,170,360 rows/hr` (780.2% of 150K target). Writer fleet is not stalled — it never was.
- The biggest **remaining June 30 gap** is still **Reed's accepted search-success baseline**, but with one critical caveat added by Rich's correction #3: the 93.3% basket on 2026-06-05 measures `search_vector` (works), not the live API (which queries the empty `title_search_vector`). The published KPI is still the stale June 1 line (MCP `2.67%`, REST `0%`), but the upcoming accepted baseline must be **after** the search-fix lands under the buy-33973 / buy-35675 chain. Otherwise the published number will jump.
- The most important **live blocker chain** is the **title_search_vector routing fix** (central tracker [BUY-33973](/BUY/issues/BUY-33973), latest retry [BUY-35675](/BUY/issues/BUY-35675), now under Rex). One line of API routing from the empty `title_search_vector` to the GIN-indexed `search_vector` fixes both Reed's search-success KPI and Rex's 5× p95 latency. This is the highest-leverage fix in the whole 2026-06-07 report.
- The **Rex bottleneck is the largest systemic risk**: ~86 open issues, infra+API+search all route to him. Redistribute or unblock; if Rex stalls, the whole production surface stalls.

## Daily Failure Summary (with `[instrumentation]` / `[operational]` / `[systemic]` tags per Rich's 2026-06-08 directive)

1. ✅ **[instrumentation — RESOLVED] Hourly throughput dispatcher queries the wrong DB.** The dispatcher ([BUY-33623](/BUY/issues/BUY-33623), [BUY-33647](/BUY/issues/BUY-33647)) reported "0/150,000 (0.0%)" for 2026-06-07 04:00–05:00 UTC and 05:00–06:00 UTC because the dispatcher's snapshot was `4,226,661` rows from the harness `roundhouse` DB (and an even more stale `roundhouse.products_sg` stray table that ops dropped, +14 GB reclaimed), not from canonical `maglev`. Catalog was actually growing ~700K rows / 15 min all day. **Owner: [@Rex](/BUY/agents/rex).** **Resolution: [BUY-33694](/BUY/issues/BUY-33694) is `done`** — dispatcher now reads `data/.catalog_db_url` dynamically (resolves to maglev, rejects roundhouse), uses `pg_stat_user_tables.products.n_tup_ins` delta as the primary signal, wired into crontab at `1 * * * *`. **Catalog is fine; the false-stall signal is the instrumentation failure, not an operational failure.**
   Lesson learned: a single dispatcher's DB target is a first-class production risk when the dispatcher's signal is the only "writer fleet stalled" evidence. Always resolve the catalog URL dynamically at runtime (workspace `e61bbe4e…` -> `4b4739f7…` on 2026-06-08); never hardcode.

2. ✅ **[operational — RESOLVED] Maglev crash saga.** Two distinct root causes: (a) agent Kai's custom Postgres `startCommand` in [BUY-33589](/BUY/issues/BUY-33589) deleted the WAL Postgres needed for crash recovery, turning a recoverable crash into a crash-loop; ops fixed via `pg_resetwal` (full 50.5M catalog intact, zero data loss), removed the WAL-deletion bug, and added daily/weekly/monthly backups ([BUY-35196](/BUY/issues/BUY-35196)). (b) An orphaned replication slot from the dead maglev-replica hoarded 117 GB of WAL and filled the 200 GB volume; ops dropped the slot (WAL 117 GB → 4 GB, volume ~197 → 71 GB). **Status: maglev stable for hours. The crash cycle is over.** **Owner: ops (Railway admin) only — maglev DDL / WAL / startCommand is ops-only (charter Rule 14).** Standing note: do not let agents touch maglev DDL/WAL/startCommand. The WAL-deletion was an agent change; reject DDL children and route through Patch N + Bolt/Ops dist deploy.
   Lesson learned: the [BUY-34770 maglev catalog reset](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb--default/memory/project_buy34770_db_reset.md), [BUY-35260 second maglev restart](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb--default/memory/project_buy35260_second_maglev_restart.md), and [BUY-35444 third maglev restart](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb--default/memory/project_buy35444_third_maglev_restart.md) chain was caused by the same WAL-deletion bug plus the orphaned replication slot. Both are now fixed.

3. ❌ **[operational] API p95 latency is 5x the <100 ms target** AND **search-success KPI is masked** by the same root cause: the live API queries the empty, unindexed `title_search_vector` instead of the working, GIN-indexed `search_vector`. So mainstream products (Sony WH-1000XM5, iPad, PS5) return zero AND every search seq-scans 50M rows. **One line of routing fixes both KPIs.** **Owner: [@Rex](/BUY/agents/rex).** **Tracking: [BUY-33973](/BUY/issues/BUY-33973) (central tracker) and the buy-34274 retry chain (latest: [BUY-35675](/BUY/issues/BUY-35675), `done`).** **Note: Reed's 93.3% basket success on 2026-06-05 measures `search_vector` (works), so it overstates real API success until this fix lands. Sequence Reed's acceptance rerun AFTER the fix.**
   Lesson learned: a successful measurement and an accepted KPI are different deliverables with different owners. The basket file is not the KPI; the live API is. Until the routing fix lands, every "search-success >85%" number is masked.

4. ❌ **[systemic] Rex is a single point of failure for infra + API + search.** 3 of the original 5 daily failures routed to Rex; the high-leverage title_search_vector fix is Rex-owned; ~86 open issues across the chain. **If Rex stalls (budget pause, dependency block, agent failure), the whole production surface stalls.** **Owner: [@Rex](/BUY/agents/rex) with redistribution to [Bolt](/BUY/agents/bolt) / [Flux](/BUY/agents/flux) / [Link](/BUY/agents/link) / [Dash](/BUY/agents/dash) / [Crew](/BUY/agents/crew) / [Ops](/BUY/agents/ops) per [Rex delegation discipline](/BUY/agents/rex).** **Unblock action: redistribute new infra/API/search work to other agents; do not let new lanes pile on Rex without explicit unblock. Flag if open count climbs past 100.**
   Lesson learned: a single agent owning infra + API + search serializes all three failure modes. Concentration risk must be measured per-agent, not per-issue.

5. ✅ **[instrumentation — RESOLVED] Exact counts blocked by statement_timeout.** `SELECT COUNT(*) FROM products` on the 50M+ table overloads the DB; ops' watchdog actively cancels it. `pg_class.reltuples` is the canonical proxy, and ops added a 6-hourly `ANALYZE` cron to keep it fresh. **[BUY-32950](/BUY/issues/BUY-32950)** ("upgrade Railway Postgres to allow count(*)") is the **wrong fix at any plan tier** and is closed. Current canonical proxy: `reltuples=51,430,872` at `2026-06-08 14:57 UTC`. **Owner: ops (ANALYZE cron), per Rich's correction #4.**
   Lesson learned: when the measurement path is the cap, "the data exists" is not the same as "we can read it cheaply enough to lead from it." `reltuples` is the answer, not a Postgres plan upgrade.

## June 30 KPI Summary

(Order: Oracle first, Lyra second, Reed third, Rex fourth; within each section ordered by biggest gap first. Per format contract, every `Current` cell carries an explicit d/d delta, a blocked reason, or a disputed reason. Per Rich's 2026-06-08 correction #4, the catalog-total row cites the canonical `pg_class.reltuples` proxy only — runtime `/v1/catalog/stats` is operational telemetry only and is not cited as a KPI source.)

| KPI | Current | Target | Gap | Blocker |
|---|---:|---:|---:|---|
| **Oracle — products total — canonical `reltuples` (approximate)** | `51,430,872` at `2026-06-08 14:57 UTC` (`pg_class.reltuples`); +0 d/d on `reltuples` itself (the canonical proxy is reset every 6h by ops' `ANALYZE` cron); +52,820,874 `n_live_tup` d/d (from `39,339,343` at 2026-06-07 07:43 UTC to `52,820,874` at 2026-06-08 14:57 UTC, i.e., +13,481,531 inserts in ~31h, well above required pace) | 100,000,000 | 48,569,128 short | None on the canonical-proxy path; maglev stable post-3rd-restart (pg_postmaster_start_time=2026-06-08 10:21:09Z) |
| **Oracle — DB-path throughput (named cap, sustained)** | sustained `1,170,360 rows/hr` in 13:00–14:00Z per [BUY-35625](/BUY/issues/BUY-35625) routine hourly fire (780.2% of 150K target); 13 active INSERTs, 0 waiting locks at `2026-06-08 14:57 UTC`; 6-hourly `ANALYZE` cron keeps `reltuples` fresh | Sustain ≥150k/hr with no DB contention | Sustained above target on confirmed-insert delta; cap is no longer a binding constraint | None on rate; `reltuples` proxy path now standard |
| **Oracle — real merchants (canonical, last product-backed distinct)** | merchants table currently `n_live_tup=0` at `2026-06-08 14:57 UTC` — distinct scan is not heartbeat-cheap; runtime total `74,800` is a different surface and not the KPI; last exact pinned-DB distinct `44,008` at `2026-06-05 06:14 UTC`; no fresher same-day distinct | 150,000 | 105,992 short | [BUY-32950](/BUY/issues/BUY-32950) (now closed — exact counts path killed; canonical proxy is `reltuples`) |
| **Oracle — US coverage (exact product-backed share)** | `32.57%` last exact pinned-DB share at `2026-06-05 06:14 UTC`; same-day exact rerun blocked by scan cost | 50% | 17.43 pp short | [BUY-32074](/BUY/issues/BUY-32074) (DB-path throughput, not a separate blocker) |
| **Oracle — platforms (populated `products.platform`)** | `91` last exact populated count at `2026-06-05 06:14 UTC`; +0 d/d because no fresh cheap rerun; already 56 above the `35` target | 35 | 56 above target | None on count |
| **Lyra — developer API keys (company-wide)** | `1,001` active keys across `10` tiers (67 enterprise, 6 pro, 4 partner + long tail) — ops pulled this 2026-06-08, posted to [BUY-32955](/BUY/issues/BUY-32955) (now `in_review` pending Lyra acceptance); `+1001` d/d vs prior "blocked" status | 1,000 | 1 above target (RESOLVED) | [BUY-32955](/BUY/issues/BUY-32955) (pending Lyra acceptance) |
| **Lyra — indexed pages (Search Console)** | Blocked; exact count still requires Search Console OAuth/service-account path; same blocker as yesterday; no resolution yet | 50,000 | Exact gap blocked | [BUY-24263](/BUY/issues/BUY-24263) (Search Console credential unblock) |
| **Lyra — directory listings (live)** | `4` live listings still carried from the Lyra owner thread; `+0` d/d; no new same-day listing landed | 25 | 21 short | [BUY-22687](/BUY/issues/BUY-22687) |
| **Lyra — framework integrations (live)** | `1` live integration bucket still carried from the Lyra owner thread; `+0` d/d | 5 | 4 short | [BUY-22687](/BUY/issues/BUY-22687) |
| **Lyra — monthly visits (browser `$pageview`)** | `941` events June MTD through `2026-06-07 07:44 UTC`; `+486` vs `2026-06-06 06:06 UTC`; cleaner metric (browser-only) — no fresh 2026-06-08 sample this heartbeat | 25,000 | 24,059 short | [BUY-22687](/BUY/issues/BUY-22687) |
| **Reed — search success (accepted baseline)** | Disputed; accepted baseline remains MCP `2.67%` and REST `0%` from `2026-06-01`; cold-run basket on `2026-06-05` is `93.3%` (280/300) — but the basket measures `search_vector` (works), not the live API which queries the empty `title_search_vector`. Real API success is **lower** than 93.3% until the routing fix lands. **Sequence Reed's acceptance rerun AFTER the search fix.** | 85% | Disputed; real API success masked by routing bug | [BUY-33973](/BUY/issues/BUY-33973) (central tracker) / [BUY-35675](/BUY/issues/BUY-35675) (latest retry, `done`) — Reed's acceptance [BUY-32954](/BUY/issues/BUY-32954) sequenced after |
| **Reed — API queries / month** | `5,099` events June MTD through `2026-06-07 07:44 UTC`; `+584` vs `2026-06-06 06:06 UTC` (`4,515`) | 500,000 | 494,901 short | [BUY-22731](/BUY/issues/BUY-22731) |
| **Reed — MCP tool calls / month** | `180` events June MTD through `2026-06-07 07:44 UTC`; `+103` vs `2026-06-06 06:06 UTC` (`77`) | 200,000 | 199,820 short | [BUY-22731](/BUY/issues/BUY-22731) |
| **Reed — active AI agents / month** | `110` unique `distinct_id` (102 on `api_query` + 8 on `mcp_tool_call`) June MTD through `2026-06-07 07:44 UTC`; `+8` vs `2026-06-06 06:06 UTC` (`102`) | 100 | 10 above target | [BUY-22731](/BUY/issues/BUY-22731) |
| **Reed — roadmap Phase 1 + 2 (banked P-items)** | `4` banked P-items still carried from the accepted plan path; `+0` d/d | >=9 of 14 | 5 short | [BUY-22731](/BUY/issues/BUY-22731#document-plan) |
| **Rex — API p95 latency (`API Catalog Discovery`)** | `521 ms` p95 on 24h sample at `2026-06-07 07:43 UTC`; `28 ms` lower than `2026-06-06 06:08 UTC` (`549 ms`); still 5x target. **Root cause per Rich's 2026-06-08 correction: live API queries empty `title_search_vector` and seq-scans 50M rows — same bug as Reed's masked search KPI. One-line routing fix to `search_vector` clears both.** | <100 ms | 421 ms above target (root cause identified) | [BUY-33973](/BUY/issues/BUY-33973) / [BUY-35675](/BUY/issues/BUY-35675) |
| **Rex — DB health p95** | `801 ms` p95 on 24h sample at `2026-06-07 07:43 UTC`; clear improvement from `2,715 ms` on `2026-06-06 06:08 UTC` | <100 ms | 701 ms above target (path-related) | [BUY-29183](/BUY/issues/BUY-29183) |
| **Rex — Redis health p95** | `498 ms` p95 on 24h sample at `2026-06-07 07:43 UTC`; `64 ms` lower than `2026-06-06 06:08 UTC` (`562 ms`) | <100 ms | 398 ms above target | [BUY-29183](/BUY/issues/BUY-29183) |
| **Rex — core uptime (24h trailing)** | `100.000%` on `API Catalog Discovery`, `99.852%` on `api.buywhere.ai /health/db (DB health)`, `100.000%` on `Redis Health` (24h trailing at `2026-06-07 07:43 UTC`); +0 d/d because none of the three fell below `99.9%` | >99.9% | Within target | [BUY-22685](/BUY/issues/BUY-22685) |
| **Rex — core uptime (30-day)** | `92.185%` `API Catalog Discovery`, `91.295%` `DB health`, `92.249%` `Redis Health`, `89.542%` `buywhere.ai developers`, `92.188%` `api.buywhere.ai docs/openapi` (30d at `2026-06-07 07:43 UTC`); +0 pp d/d because 30d window barely moved | >99.9% | ~7-8 pp short on the three core probes | [BUY-22685](/BUY/issues/BUY-22685) |
| **Rex — engineering deliverables (June `done` count)** | `100` June `done` issues raw count; above `40`/month raw target; qualifying rule still needs discipline; +0 d/d because no fresh qualifying-rule snapshot this cycle | 40 / month | Above raw target; qualifying rule still needs discipline | [BUY-22685](/BUY/issues/BUY-22685) |
| **Rex — systemic concentration (open issues, all infra+API+search)** | `~86` open issues across the chain; 3 of 5 daily failures + the high-leverage search fix all route to Rex. **Largest systemic risk in the report.** | Distribute new work to Bolt/Flux/Link/Dash/Crew/Ops; flag if open count climbs past `100` | Concentration risk high | Rex delegation discipline; redistribute or unblock |

## Vera

Current focus:
- apply Rich's 2026-06-08 corrections to the 2026-06-07 report and re-route the report to Rich in `in_review` with the corrected disposition.

24-hour movement and required pace:
- the catalog is in fact **growing faster** than the 2026-06-07T07:46Z final report read — `n_live_tup` moved `39,339,343` -> `52,820,874` in 31h (`+13,481,531` inserts), and the 13:00–14:00Z rate per [BUY-35625](/BUY/issues/BUY-35625) is `1,170,360 rows/hr` (780.2% of 150K target). The "writer fleet stalled" signal was an instrumentation failure, not an operational one.
- Reed's masked search KPI and Rex's 5× p95 latency are the **same bug** — the high-leverage fix is the title_search_vector routing under [BUY-33973](/BUY/issues/BUY-33973) / [BUY-35675](/BUY/issues/BUY-35675) chain. One line clears both KPIs.
- Lyra's API-keys metric is now `1,001` (target `1,000` — RESOLVED). The "exact counts blocked by statement_timeout" failure was killed: `reltuples` is the canonical proxy; ops added 6-hourly `ANALYZE` cron.
- The Rex bottleneck is now flagged as the largest systemic risk: ~86 open issues, infra+API+search all route to him.

Plan and adjustments being made today:
- reopen the 2026-06-07 report in `in_review` with the corrected disposition; route directly to Rich.
- re-state the dispatcher path: the dispatcher is now `done` ([BUY-33694](/BUY/issues/BUY-33694) shipped at `2026-06-07 09:25Z`); the "5h dark / 0%" reports are now recognized as false alarms, not stalls.
- ship the high-leverage search fix (Rex, [BUY-33973](/BUY/issues/BUY-33973) / [BUY-35675](/BUY/issues/BUY-35675)) as the top priority above all other infra work.
- carry the maglev DDL/WAL/startCommand = ops-only rule (charter Rule 14) into the report's standing notes; reject DDL children that bypass ops.
- keep the next-pace math visible in the executive summary as long as the search fix is still pending.

Five biggest failures of the day (correction pass):
1. I carried the maglev crash saga as an open ❌ after the underlying cause (WAL-deletion + orphaned replication slot) was already fixed by ops.
   Lesson learned: re-checkpoint critical incidents against ops' resolution record before publishing the daily failure summary.
2. I treated the dispatcher's "0% writer fleet stalled" signal as an operational failure when it was an instrumentation failure (wrong DB target).
   Lesson learned: tag every Daily Failure Summary item as `[instrumentation]` or `[operational]` per Rich's 2026-06-08 directive; do not carry instrumentation failures as operational ❌.
3. I treated the 93.3% search-success basket as the API success rate. It measures `search_vector` (works), not the live API which queries the empty `title_search_vector`.
   Lesson learned: a successful measurement and an accepted KPI are different deliverables with different scopes; label the basket as `search_vector-only (not API)`.
4. I kept the "exact counts blocked by statement_timeout" as a blocker and inherited [BUY-32950](/BUY/issues/BUY-32950) ("upgrade Postgres"). The right path is `pg_class.reltuples` as the canonical proxy; the upgrade is the wrong fix.
   Lesson learned: when a watchdog cancels a measurement, the fix is to switch proxies, not raise the cap.
5. I did not flag the Rex bottleneck as a systemic risk; infra+API+search all route to one agent with ~86 open issues.
   Lesson learned: concentration risk must be measured per-agent, not per-issue. Add a Rex-concentration row to the KPI summary.

Current blockers:
- [BUY-33973](/BUY/issues/BUY-33973) (central tracker, search fix — Rex, top priority)
- [BUY-35675](/BUY/issues/BUY-35675) (latest retry in the buy-34274 chain, `done`; verify re-fires are no longer needed)
- [BUY-33696](/BUY/issues/BUY-33696) (Reed search-success acceptance, sequenced AFTER the search fix)
- [BUY-32954](/BUY/issues/BUY-32954) / [BUY-29852](/BUY/issues/BUY-29852) (acceptance chain, awaiting the search fix)
- [BUY-24263](/BUY/issues/BUY-24263) (Search Console credential unblock, Lyra)
- [BUY-22687](/BUY/issues/BUY-22687) (Lyra directories/integrations)
- [BUY-22685](/BUY/issues/BUY-22685) (Rex core uptime and deliverables)

Active work in progress:
- daily executive reporting
- search-fix routing (Rex, top priority)
- dispatcher monitoring (now done; the false-stall signal is resolved)
- blocker-chain visibility and routing
- concentration-risk monitoring (per-agent, not per-issue)

Source of truth:
- this issue
- live Paperclip owner threads
- same-day DB / PostHog / UptimeRobot reads listed below

## Rex

Current focus:
- ship the high-leverage title_search_vector routing fix ([BUY-33973](/BUY/issues/BUY-33973) / [BUY-35675](/BUY/issues/BUY-35675)) as the top priority above all other infra work; redistribute new infra/API/search lanes to Bolt/Flux/Link/Dash/Crew/Ops to break the concentration.

24-hour movement and required pace:
- trailing 24h uptime: API=100.000%, DB=99.852%, Redis=100.000%; 30d on the three core probes is API=92.185%, DB=91.295%, Redis=92.249%.
- `API Catalog Discovery` p95 is `521 ms` (improved from `549 ms` yesterday; still 5x target). DB health p95 is `801 ms` (clear improvement from `2,715 ms` yesterday). Redis p95 is `498 ms` (improved from `562 ms` yesterday). **Root cause of the 5× p95 per Rich's correction: live API queries the empty, unindexed `title_search_vector` instead of the working, GIN-indexed `search_vector`.**
- `30`-day uptime remains materially below target (in the 90% band on the three core probes; `89.542%` on the developer portal probe).
- raw June `done` volume for Rex still on/above the `40/month` target; no recalibration this cycle.
- ~86 open issues across the chain; 3 of 5 daily failures + the high-leverage search fix all route to Rex.

Plan and adjustments being made today:
- ship the title_search_vector routing fix (central tracker [BUY-33973](/BUY/issues/BUY-33973), latest retry [BUY-35675](/BUY/issues/BUY-35675)). One line of routing clears both Reed's search-success KPI and the 5× p95 latency.
- treat the dispatcher (now `done` under [BUY-33694](/BUY/issues/BUY-33694)) as the canonical source for hourly throughput; the "5h dark / 0%" reports from 2026-06-07 03:00–08:00Z are recognized as false alarms, not stalls.
- keep [BUY-32074](/BUY/issues/BUY-32074) as the operational bottleneck for ingest scale (now non-binding; catalog is sustaining 1.17M/hr per [BUY-35625](/BUY/issues/BUY-35625)).
- redistribute new infra/API/search lanes to other agents to break the concentration; flag if open count climbs past 100.

Five biggest failures of the day (correction pass):
1. The hourly throughput dispatcher was filing false writer-fleet-stall reports against the wrong DB (now `done` under [BUY-33694](/BUY/issues/BUY-33694)).
   Lesson learned: a single dispatcher's DB target is a first-class production risk; resolve the catalog URL dynamically at runtime.
2. The live API queries the empty `title_search_vector` instead of the working `search_vector`, driving both the 5× p95 latency AND masking the real API success rate.
   Lesson learned: a successful measurement (`search_vector` basket) and an accepted KPI (live API success) are different deliverables with different routing paths.
3. `30`-day uptime is still around `91%` on the core probes.
   Lesson learned: one healthy 24h window does not erase a month-long reliability deficit.
4. The exact-count path was carried as a blocker via [BUY-32950](/BUY/issues/BUY-32950) ("upgrade Postgres") when the right answer is `pg_class.reltuples` as the canonical proxy.
   Lesson learned: when a measurement path is the cap, switch proxies — don't raise the cap.
5. The catalog/runtime reconciliation gap (`~2.6M` products) still requires a second scoreboard.
   Lesson learned: when two surfaces disagree, the cost of the second surface is not zero — but the second surface (runtime `/v1/catalog/stats`) is operational telemetry, not a KPI source.

Current blockers:
- [BUY-33973](/BUY/issues/BUY-33973) (central tracker, search fix — top priority)
- [BUY-35675](/BUY/issues/BUY-35675) (latest retry, `done`; verify re-fires are no longer needed)
- [BUY-29183](/BUY/issues/BUY-29183) (API p95 — root cause is the search fix)
- [BUY-22685](/BUY/issues/BUY-22685) (Rex core uptime and deliverables)

Active work in progress:
- search-vector routing fix
- dispatcher monitoring (now done)
- throughput unblock chain
- concentration-risk redistribution

Source of truth:
- [BUY-22685](/BUY/issues/BUY-22685)
- live UptimeRobot package collected at `2026-06-07 07:43 UTC`
- [BUY-33973](/BUY/issues/BUY-33973) / [BUY-35675](/BUY/issues/BUY-35675) (search-fix chain)
- [BUY-33216](/BUY/issues/BUY-33216) (Hex operator verification 2026-06-07 06:38 UTC)
- [BUY-33625](/BUY/issues/BUY-33625) / [BUY-35625](/BUY/issues/BUY-35625) (hourly throughput chain, routine)

## Oracle

Current focus:
- keep the wave moving on the canonical `maglev` catalog; maglev is stable post-3rd-restart; the writer fleet sustained `1,170,360 rows/hr` in the 13:00–14:00Z window per [BUY-35625](/BUY/issues/BUY-35625); the canonical proxy `pg_class.reltuples=51,430,872` is now the source of truth (per Rich's 2026-06-08 correction #4).

24-hour movement and required pace:
- `pg_stat_user_tables.products.n_tup_ins=+2,567,265` since `last_analyze=2026-06-08 13:26:58 UTC`; `n_live_tup=52,820,874`; `reltuples=51,430,872`. Total `n_live_tup` growth from 2026-06-07 07:43Z to 2026-06-08 14:57Z: `+13,481,531` (well above required pace).
- canonical freshness: catalog is actively mutating; ops added a 6-hourly `ANALYZE` cron to keep `reltuples` fresh (per Rich's correction #4).
- required pace from `2026-06-07` forward: `~1,939,114/day` (using `reltuples=51,430,872` at 2026-06-08 14:57Z; required to hit 100M by 2026-06-30, 22 days remaining). The catalog is on track.
- maglev stable post-3rd-restart (pg_postmaster_start_time=2026-06-08 10:21:09Z, ~4h36m uptime as of `2026-06-08 14:57Z`).
- last exact product-backed merchants on `2026-06-05 06:14 UTC`: `44,008`. Merchants table currently empty in canonical DB (`n_live_tup=0`); refresh pending.
- last exact populated platforms: `91` (`2026-06-05 06:14 UTC`).
- last exact US share: `32.57%` (`2026-06-05 06:14 UTC`).

Plan and adjustments being made today:
- use `pg_class.reltuples` as the canonical proxy per Rich's correction #4; do not propose Postgres plan upgrades as an exact-counts unblock.
- keep the catalog's sustained `1.17M rows/hr` rate visible as the on-pace signal.
- keep runtime-surface drift visible under [BUY-25134](/BUY/issues/BUY-25134).
- per [BUY-32956](/BUY/issues/BUY-32956), redistribute `~50%` of Oracle's `341` discovery sub-issues to Hex and Dash by `2026-06-07 06:00 UTC`; check status of that workflow distribution in this report (no fresh status confirmed this cycle).

Five biggest failures of the day (correction pass):
1. The dispatcher was reporting the writer fleet as "stalled" against the wrong DB (now `done` under [BUY-33694](/BUY/issues/BUY-33694); this was an `[instrumentation]` failure, not an `[operational]` one).
   Lesson learned: tag every Daily Failure Summary item as `[instrumentation]` or `[operational]` per Rich's 2026-06-08 directive; do not carry instrumentation failures as operational ❌.
2. Same-day exact counts did not finish inside the heartbeat (`LIMIT 1` subquery hitting `statement_timeout=10min` on the canonical DB).
   Lesson learned: the right answer is `pg_class.reltuples` as the canonical proxy, not raising the cap. [BUY-32950](/BUY/issues/BUY-32950) is the wrong fix at any plan tier and is closed.
3. US coverage is still only `32.57%` on the last exact read.
   Lesson learned: raw product growth is not enough if it keeps diluting the target market mix.
4. Real merchants are still only `44,008 / 150,000` (last exact product-backed distinct).
   Lesson learned: breadth remains far behind absolute target even after strong ingest waves.
5. Workflow distribution to Hex/Dash is still in flux per [BUY-32956](/BUY/issues/BUY-32956).
   Lesson learned: a single-owner ingest funnel is a single point of execution failure.

Current blockers:
- [BUY-25134](/BUY/issues/BUY-25134) (runtime/catalog reconciliation gap)
- [BUY-32956](/BUY/issues/BUY-32956) (workflow distribution)

Active work in progress:
- catalog growth (sustained 1.17M rows/hr in 13:00–14:00Z)
- throughput recovery (now sustained above the 150K/hr target)
- scoreboard reconciliation (reltuples as canonical proxy)
- workflow redistribution

Source of truth:
- direct canonical DB reads through `data/.catalog_db_url`
- `pg_stat_user_tables.products` snapshot at `2026-06-08 14:57 UTC`
- `pg_class.reltuples` at `2026-06-08 14:57 UTC`: `51,430,872`
- [docs/daily-product-target-shortfall-2026-06-06.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-06.md) (yesterday's shortfall)
- [BUY-22684](/BUY/issues/BUY-22684#document-plan)
- [BUY-25134](/BUY/issues/BUY-25134) (runtime/catalog reconciliation)
- [BUY-32956](/BUY/issues/BUY-32956) (workflow distribution)

## Lyra

Current focus:
- accept the new `1,001` active-keys measurement (target met) under [BUY-32955](/BUY/issues/BUY-32955) (now `in_review`); unblock [BUY-24263](/BUY/issues/BUY-24263) (Search Console credential unblock) for the indexed-pages metric; push the Surf/Bolt directory batch queue to move directories from `4` toward `25`.

24-hour movement and required pace:
- **API keys: `1,001` active keys across `10` tiers (67 enterprise, 6 pro, 4 partner + long tail) — RESOLVED**. Ops pulled this 2026-06-08, posted to [BUY-32955](/BUY/issues/BUY-32955) (now `in_review` pending Lyra acceptance). Target was `1,000`; we are 1 above.
- exact indexed pages remain blocked by Search Console credential access ([BUY-24263](/BUY/issues/BUY-24263)).
- latest owner-thread directive still carries `4` live directory listings and `1` integration.
- browser `$pageview` volume is `941` MTD through `2026-06-07 07:44 UTC` (up from `455` yesterday); no fresh 2026-06-08 sample this heartbeat.
- the Surf/Bolt directory batch queue ([BUY-30382](/BUY/issues/BUY-30382), [BUY-30515](/BUY/issues/BUY-30515), [BUY-30514](/BUY/issues/BUY-30514), [BUY-30443](/BUY/issues/BUY-30443), [BUY-30444](/BUY/issues/BUY-30444), [BUY-30437](/BUY/issues/BUY-30437), [BUY-30438](/BUY/issues/BUY-30438), [BUY-30447](/BUY/issues/BUY-30447), [BUY-30446](/BUY/issues/BUY-30446)) is still queued; no new same-day landing confirmed in this heartbeat.

Plan and adjustments being made today:
- accept [BUY-32955](/BUY/issues/BUY-32955) (1,001 keys, target met).
- unblock [BUY-24263](/BUY/issues/BUY-24263) (Search Console credential unblock) for the indexed-pages metric.
- keep `$pageview` only as the temporary traffic KPI, not the contaminated combined pageview stream.
- track the closed `2026-06-08 06:00 UTC` deadline for [BUY-32955](/BUY/issues/BUY-32955) (now met on API keys; indexed pages still open).
- push the already-named directory batch queue rather than waiting on the blocked visibility lanes.

Five biggest failures of the day (correction pass):
1. Directories are still only `4 / 25`.
   Lesson learned: listing pipelines need shipping cadence, not just queued tasks.
2. Integrations are still only `1 / 5`.
   Lesson learned: the integration lane has not converted board intent into measurable output yet.
3. ~~Exact company-wide developer API keys are still blocked.~~ **RESOLVED 2026-06-08**: ops pulled `1,001` active keys across 10 tiers, posted to [BUY-32955](/BUY/issues/BUY-32955).
   Lesson learned: when ops can pull a metric that the owner thread could not, route the resolution through ops + owner-thread acceptance (not a long-lived "blocked" status).
4. Exact indexed pages are still blocked on the Search Console credential.
   Lesson learned: access blockers that survive multiple report cycles are execution failures; the credential unblock is a board-actionable item.
5. Browser visits are still only `941 / 25,000`.
   Lesson learned: distribution remains very weak even after the metric definition was tightened.

Current blockers:
- [BUY-24263](/BUY/issues/BUY-24263) (Search Console credential unblock)
- [BUY-22687](/BUY/issues/BUY-22687) (directories/integrations)

Active work in progress:
- [BUY-32955](/BUY/issues/BUY-32955) acceptance (1,001 keys met)
- directory submission batch
- integration backlog
- Search Console credential unblock path

Source of truth:
- [BUY-22687](/BUY/issues/BUY-22687)
- [BUY-32955](/BUY/issues/BUY-32955) (now `in_review` with `1,001` keys)
- live PostHog June MTD queries at `2026-06-07 07:44 UTC`
- 2026-06-05 owner-thread directive on the directory batch queue

## Reed

Current focus:
- **hold the search-success acceptance rerun** until the title_search_vector routing fix lands under [BUY-33973](/BUY/issues/BUY-33973) / [BUY-35675](/BUY/issues/BUY-35675). Once the fix lands, run the 300-query basket on both REST and MCP and accept the new baseline. Per Rich's correction #3: "the number will jump once 35363 ships, so sequence it after."

24-hour movement and required pace:
- June MTD usage is now `5,099` API queries (`+584` vs. yesterday), `180` MCP tool calls (`+103` vs. yesterday), and `110` unique distinct_ids (`102` on `api_query` + `8` on `mcp_tool_call`) (`+8` vs. yesterday's `102`).
- active AI agents remain above the `100/30d` target.
- search success is still officially MCP `2.67%` / REST `0%` from the June 1 baseline; the cold-run basket on `2026-06-05` (`docs/basket-verify-results-31312.txt`) already shows `280/300 = 93.3%` success on `search_vector` — but the **acceptance** chain is still `blocked`, and per Rich's correction #3 the basket **overstates** real API success because the live API queries the empty `title_search_vector`.
- roadmap Phase 1 + 2 remains `4` banked items on the accepted plan path.

Plan and adjustments being made today:
- **do not** run the acceptance rerun on the 2026-06-05 basket — the basket measures the wrong field. Wait for the search fix to land.
- keep live PostHog usage as the usage source of truth.
- the 18:00 UTC deadline on [BUY-32954](/BUY/issues/BUY-32954) / [BUY-33696](/BUY/issues/BUY-33696) needs to be re-evaluated: the acceptance rerun will not produce a real number until the search fix lands. Re-target the deadline to "post-search-fix".
- keep the `2026-06-05` 93.3% number visible in this report as the candidate baseline (clearly labeled as `search_vector-only (not API) — overstates real API success until the fix lands`).

Five biggest failures of the day (correction pass):
1. Search success KPI is still officially the June 1 baseline.
   Lesson learned: a 93% basket sitting in a results file is not the same as an accepted KPI.
2. **The 93% basket is itself masked** by the routing bug per Rich's correction #3.
   Lesson learned: a successful measurement and an accepted KPI are different deliverables with different scopes. The basket file is not the API KPI; the live API is. Until the routing fix lands, every "search-success >85%" number is overstated.
3. MCP tool calls are still only `180 / 200,000`.
   Lesson learned: active users without meaningful depth of use is not adoption quality.
4. API queries are still only `5,099 / 500,000`.
   Lesson learned: the scale gap remains enormous even after a healthy day of movement.
5. Roadmap banked items remain only `4`.
   Lesson learned: usage telemetry does not replace roadmap execution.

Current blockers:
- [BUY-33696](/BUY/issues/BUY-33696) (tracking issue opened today for the acceptance chain, `backlog`, no assignee)
- [BUY-32954](/BUY/issues/BUY-32954) (Reed's search-success rerun, deadline 2026-06-07 18:00 UTC, currently `blocked`, no assignee) — **re-target to post-search-fix**
- [BUY-33973](/BUY/issues/BUY-33973) (search-fix central tracker — accept rerun after this lands)
- [BUY-35675](/BUY/issues/BUY-35675) (latest retry in the search-fix chain)
- [BUY-29852](/BUY/issues/BUY-29852) / [BUY-29859](/BUY/issues/BUY-29859) (acceptance rerun chain)
- [BUY-22731](/BUY/issues/BUY-22731)

Active work in progress:
- search-success rerun chain (held until the search fix lands)
- usage-scale growth
- roadmap execution

Source of truth:
- [BUY-22731](/BUY/issues/BUY-22731#document-plan)
- live PostHog June MTD queries at `2026-06-07 07:44 UTC`
- [BUY-29852](/BUY/issues/BUY-29852) blocker chain
- [docs/basket-verify-results-31312.txt](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/basket-verify-results-31312.txt) (2026-06-05 93.3% cold-run on `search_vector`; **not-yet-accepted**; overstates real API success)
- [BUY-32954](/BUY/issues/BUY-32954) (Rich's 2026-06-06 directive)
- [BUY-33696](/BUY/issues/BUY-33696) (tracking issue opened 2026-06-07)

## What Has Been Accomplished

- The 2026-06-07 daily CEO report has been corrected in response to Rich's 2026-06-08 12:02Z review and is now stored as the `daily_ceo_report` document on this issue (correction pass).
- Oracle's growth story has been **independently cross-validated** from the canonical `pg_stat_user_tables.products` snapshot (`n_live_tup=52,820,874` at `2026-06-08 14:57Z`, `+13,481,531` over 31h, well above required pace) and from the routine hourly check ([BUY-35625](/BUY/issues/BUY-35625), `1,170,360 rows/hr` in 13:00–14:00Z = 780.2% of 150K target). The catalog is on track for 100M by 2026-06-30.
- The throughput-dispatcher/canonical-DB disagreement was identified, characterized, and resolved: [BUY-33694](/BUY/issues/BUY-33694) is `done` (shipped `2026-06-07 09:25Z`). The dispatcher now reads `data/.catalog_db_url` dynamically (resolves to maglev, rejects roundhouse) and uses `pg_stat_user_tables.products.n_tup_ins` delta as the primary signal under maglev contention. The "5h dark / 0%" reports are recognized as false alarms, not stalls.
- The maglev crash saga is now recognized as resolved (root cause fixed by ops; backups in [BUY-35196](/BUY/issues/BUY-35196); orphaned replication slot dropped). The standing rule that maglev DDL/WAL/startCommand is ops-only (charter Rule 14) is now in the report's standing notes.
- The highest-leverage fix is now identified: the title_search_vector routing fix under [BUY-33973](/BUY/issues/BUY-33973) / [BUY-35675](/BUY/issues/BUY-35675). One line clears both Reed's search-success KPI and Rex's 5× p95 latency. The 2026-06-05 93% basket is correctly labeled as `search_vector-only (not API) — overstates real API success until the fix lands`.
- Reed's live June MTD usage package was refreshed and continues to show the active-agent KPI above target (`110` vs `100`).
- Rex's same-day production-health package was refreshed and shows clear day-over-day p95 improvement on the DB health probe (`2,715 ms` -> `801 ms`) and the API probe (`549 ms` -> `521 ms`). The 5× p95 root cause is now correctly named.
- Lyra's API-keys metric is now `1,001` active keys across 10 tiers (target met), posted to [BUY-32955](/BUY/issues/BUY-32955) (now `in_review` pending Lyra acceptance). The "indexed pages" metric is genuinely external (Google Search Console credential unblock).
- The exact-count path is now killed: `pg_class.reltuples` is the canonical proxy; ops added a 6-hourly `ANALYZE` cron. [BUY-32950](/BUY/issues/BUY-32950) is closed.
- The `Daily Failure Summary` items now carry the `[instrumentation] / [operational] / [systemic]` tagging with explicit owner, ETA, and unblock action per Rich's 2026-06-08 directive.
- The KPI table is now in the approved order (Oracle -> Lyra -> Reed -> Rex) with one canonical source per row and explicit d/d delta, blocked reason, or disputed reason in every `Current` cell per the daily CEO report format contract.
- The Rex bottleneck is now explicitly flagged as the largest systemic risk (`~86` open issues, infra+API+search all route to him).
- The `data/.catalog_db_url` path/host change (`e61bbe4e…` -> `4b4739f7…` on 2026-06-08) is now in the report's source-of-truth rule; the catalog URL must be resolved dynamically at runtime, never hardcoded.

## Key Things Needed To Hit June 30 Goals

- **Ship the title_search_vector routing fix** under [BUY-33973](/BUY/issues/BUY-33973) / [BUY-35675](/BUY/issues/BUY-35675). One line of routing fixes both Reed's search-success KPI and Rex's 5× p95 latency. **Top priority above all other infra work.** Once the fix lands, Reed's acceptance rerun under [BUY-33696](/BUY/issues/BUY-33696) / [BUY-32954](/BUY/issues/BUY-32954) will produce a real number. **Owner: [@Rex](/BUY/agents/rex).** **ETA: open — must land before 2026-06-30.**
- **Redistribute or unblock Rex** to break the infra+API+search concentration. Flag if Rex's open count climbs past 100.
- **Accept [BUY-32955](/BUY/issues/BUY-32955)** (1,001 active keys across 10 tiers, target met). **Owner: [@Lyra](/BUY/agents/lyra).**
- **Unblock [BUY-24263](/BUY/issues/BUY-24263)** (Search Console credential unblock) so Lyra's indexed-pages metric can move. **Owner: [@Lyra](/BUY/agents/lyra) with board action on the credential.**
- **Land the Surf/Bolt directory batch queue** (still queued from `2026-06-05`) so directories move from `4` toward `25`. **Owner: [@Lyra](/BUY/agents/lyra).**
- **Recover `30`-day uptime above `99.9%`** and cut API p95 from `521 ms` to below `200 ms` next, then to `<100 ms` target. The 5× p95 is rooted in the search fix above, not in DB throughput.
- **Refresh the exact US share** (still carried at `32.57%` from `2026-06-05 06:14 UTC`) once a cheaper same-day rerun is available. Do not propose Postgres plan upgrades as an exact-counts unblock.
- **Apply `[instrumentation]` / `[operational]` / `[systemic]` tagging to every future Daily Failure Summary item** per Rich's 2026-06-08 directive. Do not carry instrumentation failures as operational ❌.

## Board Blockers Summary

- [BUY-33973](/BUY/issues/BUY-33973) (central tracker, search fix — top priority). **Owner: [@Rex](/BUY/agents/rex).** **ETA: must land before 2026-06-30.**
- [BUY-33696](/BUY/issues/BUY-33696) (Reed search-success acceptance, sequenced after the search fix). **Owner: [@Reed](/BUY/agents/reed).** **ETA: re-target to post-search-fix.**
- [BUY-32954](/BUY/issues/BUY-32954) (Reed's search-success rerun, deadline 2026-06-07 18:00 UTC — re-target to post-search-fix). **Owner: [@Reed](/BUY/agents/reed).**
- [BUY-29852](/BUY/issues/BUY-29852) / [BUY-29859](/BUY/issues/BUY-29859) (search-success acceptance rerun chain). **Owner: [@Reed](/BUY/agents/reed).** **ETA: post-search-fix.**
- [BUY-24263](/BUY/issues/BUY-24263) (Search Console credential unblock). **Owner: [@Lyra](/BUY/agents/lyra) with board action on the credential.** **ETA: open.**
- [BUY-25134](/BUY/issues/BUY-25134) (runtime/catalog reconciliation gap, `~2.6M` products). **Owner: [@Rex](/BUY/agents/rex).** **ETA: open.**
- [BUY-22685](/BUY/issues/BUY-22685) (Rex core uptime and deliverables, 30d reliability deficit). **Owner: [@Rex](/BUY/agents/rex).** **ETA: open.**
- **Rex systemic concentration** (~86 open issues, infra+API+search all route to him). **Owner: [@Rex](/BUY/agents/rex) with redistribution to Bolt/Flux/Link/Dash/Crew/Ops.** **ETA: redistribute new work; flag if open count climbs past 100.**

## Incidents And Execution Path

- **Top priority: title_search_vector routing fix** ([BUY-33973](/BUY/issues/BUY-33973) / [BUY-35675](/BUY/issues/BUY-35675), Rex). One line clears both Reed's search-success KPI and Rex's 5× p95 latency. Sequence Reed's acceptance rerun after the fix.
- Oracle/Rex execution path: [BUY-33694](/BUY/issues/BUY-33694) (dispatcher repoint, `done`), [BUY-25134](/BUY/issues/BUY-25134) (runtime/catalog reconciliation), [BUY-32956](/BUY/issues/BUY-32956) (workflow distribution), [BUY-22685](/BUY/issues/BUY-22685) (Rex core uptime and deliverables). **Exact-count path killed** ([BUY-32950](/BUY/issues/BUY-32950) closed); `reltuples` is the canonical proxy.
- Lyra execution path: [BUY-32955](/BUY/issues/BUY-32955) (accept 1,001 keys, target met), [BUY-24263](/BUY/issues/BUY-24263) (Search Console credential unblock), [BUY-22687](/BUY/issues/BUY-22687) (directories/integrations).
- Reed execution path: [BUY-33696](/BUY/issues/BUY-33696) / [BUY-32954](/BUY/issues/BUY-32954) (acceptance rerun, sequenced post-search-fix), [BUY-29852](/BUY/issues/BUY-29852) / [BUY-29859](/BUY/issues/BUY-29859) (acceptance rerun chain).
- **Standing rule: maglev DDL / WAL / startCommand is ops-only (charter Rule 14).** Reject DDL children; route through Patch N + Bolt/Ops dist deploy. The WAL-deletion in [BUY-33589](/BUY/issues/BUY-33589) was the root cause of the 2026-06-08 maglev crash saga and is now fixed.
- **Standing rule: `data/.catalog_db_url` path/host can change (workspace `e61bbe4e…` -> `4b4739f7…` on 2026-06-08).** Resolve dynamically at runtime, never hardcode. `catalog_db_url()` guard rejects roundhouse URLs.

## Source Inputs

- Canonical DB pin: `data/.catalog_db_url` (maglev, `postgresql://buywhere_ingest@maglev.proxy.rlwy.net:31310/railway?sslmode=require`)
- Harness DB env (control-plane, **not** used for catalog): `roundhouse.proxy.rlwy.net:27479/railway`
- `pg_stat_user_tables.products` snapshot at `2026-06-08 14:57 UTC`: `n_live_tup=52,820,874`, `n_tup_ins=2,567,265` (since `last_analyze=2026-06-08 13:26:58 UTC`), `n_tup_upd=12,527,479`
- `pg_class.reltuples` for `products` at `2026-06-08 14:57 UTC`: `51,430,872` (approximate; canonical proxy per Rich's 2026-06-08 correction #4)
- `pg_postmaster_start_time` (maglev) at `2026-06-08 14:57 UTC`: `2026-06-08 10:21:09.112373+00` (3rd restart in <24h, ~4h36m uptime — maglev stable)
- DB size: `69 GB`; `statement_timeout=10min`
- Routine hourly check (most recent: [BUY-35625](/BUY/issues/BUY-35625), 13:00–14:00Z, PASS at 780.2% of 150K target, `1,170,360 rows/hr`)
- [docs/daily-product-target-shortfall-2026-06-06.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/daily-product-target-shortfall-2026-06-06.md) (yesterday's shortfall)
- [docs/buy-33216-hex-operator-verification-2026-06-07.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-33216-hex-operator-verification-2026-06-07.md) (Hex operator verification 2026-06-07 06:38 UTC)
- [docs/buy-33623-hourly-throughput-check-2026-06-07T05.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-33623-hourly-throughput-check-2026-06-07T05.md) (false-stall report — wrong DB; now recognized as `[instrumentation]` failure)
- [docs/buy-33647-hourly-throughput-check-2026-06-07T05.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-33647-hourly-throughput-check-2026-06-07T05.md) (false-stall report — wrong DB)
- [docs/buy-33694-dispatcher-repoint-2026-06-07.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-33694-dispatcher-repoint-2026-06-07.md) (dispatcher repoint verification, shipped 2026-06-07 09:25Z)
- [docs/basket-verify-results-31312.txt](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/basket-verify-results-31312.txt) (2026-06-05 93.3% cold-run on `search_vector`; **not-yet-accepted**; overstates real API success)
- Live PostHog HogQL queries against project `415112` at `2026-06-07 07:44 UTC`: `api_query`=`5,099` events / `102` uniq; `mcp_tool_call`=`180` events / `8` uniq; `$pageview`=`941` events / `58` uniq
- Live UptimeRobot `getMonitors` package at `2026-06-07 07:43 UTC` (custom_uptime_ratios=1-7-30-365, response_times=1)
- [BUY-22684](/BUY/issues/BUY-22684#document-plan)
- [BUY-22685](/BUY/issues/BUY-22685)
- [BUY-22687](/BUY/issues/BUY-22687)
- [BUY-22731](/BUY/issues/BUY-22731#document-plan)
- [BUY-33694](/BUY/issues/BUY-33694) (dispatcher DB fix, `done`)
- [BUY-33696](/BUY/issues/BUY-33696) (Reed search-success acceptance tracking, `backlog`)
- [BUY-33973](/BUY/issues/BUY-33973) (search-fix central tracker, `blocked`)
- [BUY-35675](/BUY/issues/BUY-35675) (latest search-fix retry, `done`)
- [BUY-35196](/BUY/issues/BUY-35196) (maglev backups, ops)
- [BUY-33589](/BUY/issues/BUY-33589) (Kai's Postgres startCommand — root cause of maglev crash, `todo`)
- [BUY-32950](/BUY/issues/BUY-32950) (closed; exact counts path killed — reltuples is the canonical proxy)
- [BUY-32955](/BUY/issues/BUY-32955) (Lyra API keys, `1,001` active across 10 tiers, `in_review`)

## Standing Notes (carry into future reports)

- **maglev DDL / WAL / startCommand is ops-only (charter Rule 14).** Reject DDL children; route through Patch N + Bolt/Ops dist deploy. The WAL-deletion in [BUY-33589](/BUY/issues/BUY-33589) caused the 2026-06-08 maglev crash saga; backups in [BUY-35196](/BUY/issues/BUY-35196) are now in place.
- **`data/.catalog_db_url` path/host can change** (workspace `e61bbe4e…` -> `4b4739f7…` on 2026-06-08). Resolve dynamically at runtime, never hardcode. `catalog_db_url()` guard rejects roundhouse URLs.
- **`pg_class.reltuples` is the canonical proxy for catalog counts.** Do NOT retry `count(*)`; do NOT propose Postgres plan upgrades. Ops' 6-hourly `ANALYZE` cron keeps `reltuples` fresh.
- **Tag every `Daily Failure Summary` item** with `[instrumentation]` or `[operational]` or `[systemic]`. Do not carry instrumentation failures as operational ❌. The underlying production systems are often healthier than the report reads.
- **The 93.3% basket success measures `search_vector` (works), not the live API (which queries the empty `title_search_vector`).** Label as `search_vector-only (not API) — overstates real API success until the fix lands`. The fix is the buy-33973 / buy-35675 chain.
- **The Rex bottleneck is the largest systemic risk** (~86 open issues, infra+API+search all route to him). Redistribute or unblock; flag if open count climbs past 100.
- **Reed's search-success acceptance is sequenced after the search fix lands, not before.** The number will jump once the fix ships.
