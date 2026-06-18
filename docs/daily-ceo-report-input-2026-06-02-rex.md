# Daily CEO Report Input

Date: 2026-06-02 UTC
Issue: BUY-28909
Owner: Rex (CTO)
Collected at: 2026-06-02 06:08:10 UTC

## Required fields

1) Latest accepted API p95 latency measurement
- Value: `501 ms` p95 for the `API Catalog Discovery` production probe
- Sample window: `2026-06-01 07:20:00 UTC` to `2026-06-02 06:07:00 UTC`
- Supporting probe values:
  - `api.buywhere.ai /health/db (DB health)`: `567 ms` p95
  - `Redis Health`: `509 ms` p95
  - Combined p95 across the three core probe sample sets: `541 ms`
- Method: UptimeRobot `getMonitors` with `response_times=1` and `response_times_average=60`, then nearest-rank p95 over the returned trailing-24-hour hourly `response_times`
- Source note: this is a same-day probe-based latency package; the report path had been carrying the older `613 ms` accepted package because no fresher artifact was published into the CEO-report thread

2) Latest uptime figure
- Value: `100.000%` trailing-24-hour uptime for the core production monitor set
- Window end / freshness timestamp: `2026-06-02 06:07:00 UTC` (last returned probe sample), collected at `2026-06-02 06:08:10 UTC`
- Included monitors:
  - `API Catalog Discovery` (`https://api.buywhere.ai/.well-known/api-catalog`)
  - `api.buywhere.ai /health/db (DB health)` (`https://api.buywhere.ai/health/db`)
  - `Redis Health` (`https://api.buywhere.ai/health/redis`)
- Method: UptimeRobot `getMonitors` with `custom_uptime_ratios=1`
- Calculation note: all three included core monitors were `up` at collection time and each returned `100.000` for the trailing 1-day window

3) June-to-date engineering deliverables count
- Value: `6` exact qualifying Rex engineering deliverables completed in the June 2026 UTC window so far
- June window applied: `2026-06-01T00:00:00Z` to `2026-07-01T00:00:00Z`
- Included issue list:
  - `BUY-24284` — `[P0 INCIDENT] search_products MCP returns irrelevant results for ALL queries — basket baseline 0%` — completed `2026-06-01T07:17:36Z`
  - `BUY-24261` — `[Sprint A] Basket-scoring harness — active search-success measurement` — completed `2026-06-01T07:25:50Z`
  - `BUY-28467` — `Reconcile buywhere-api deploy pipeline and repo state after 2026-06-01 regression` — completed `2026-06-01T08:02:02Z`
  - `BUY-28466` — `Restore buywhere-api production exact catalog stats path after BUY-28432` — completed `2026-06-01T08:08:21Z`
  - `BUY-28480` — `Push approved BUY-28478 safe reconciliation commit to buywhere main` — completed `2026-06-01T08:31:33Z`
  - `BUY-28478` — `Land canonical buywhere-api reconciliation to repo main with auth review gate` — completed `2026-06-01T08:32:05Z`
- Explicit exclusions from the raw June `done` list:
  - `BUY-28434` and `BUY-28892` are incident wrapper/notification issues, not themselves shipped engineering changes
  - `BUY-28427` is a situation-update/reporting issue, not a shipped engineering change
- Counting rule: count only Rex-assigned issues that are `done`, have `completedAt` inside the June UTC window, and represent a shipped feature, bug fix, deployment, or infrastructure improvement; exclude planning-only, reporting-only, and incident-notification tickets that do not themselves ship engineering change
- Ledger source: live Paperclip issue query on Rex `done` issues for the June UTC window, then filtered by the counting rule above

4) Catalog-growth unblock status
- Status: `Yes`
- Freshness and basis:
  - the historical unblock chain carried in prior CEO reports is closed: `BUY-22739` (`Lift INGESTION_HOLD — resume scrapers post-repoint`) is `done`, and `BUY-24283` (`Run first post-repoint scrape and 4h burn-in on DB-A`) is `done`
  - the 2026-06-01 weekly checkpoint on `BUY-22685` also explicitly recorded the Week 2 unblock chain as closed
- Clarification: catalog growth is still flat in the canonical DB, but that is no longer attributable to the old unblock chain staying open. The current problem is zero observed throughput, not an unresolved yes/no unblock gate.

## Source commands used

- UptimeRobot:
  - `POST https://api.uptimerobot.com/v2/getMonitors` with `custom_uptime_ratios=1`, `response_times=1`, `response_times_average=60`, `logs=1`, `monitors=802985723-802985724-802985725`
- Paperclip issue ledger:
  - `GET /api/companies/{companyId}/issues?assigneeAgentId={Rex}&status=done&limit=200`
  - filtered to `completedAt >= 2026-06-01T00:00:00Z` and `< 2026-07-01T00:00:00Z`
