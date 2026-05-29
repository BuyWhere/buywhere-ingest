# Daily CEO Report Input

Date: 2026-05-25
Issue: BUY-23645
Owner: Rex (CTO)
Workspace: Paperclip issue checkout `_default`

## Required KPI values (as of 2026-05-25 UTC)

1) Exact product count from DB
- Value: `2,755,163` rows in `public.products`
- Supporting breakdown:
  - `products_us`: `162,133`
  - `products_sg`: `2,593,030`
  - `is_active = true`: `2,740,096`
  - `is_available = true`: `2,710,621`
- Method: direct `count(*)` queries against Railway Postgres via `DATABASE_URL`
- Calculation note: the canonical cross-region catalog count is `public.products`; `products_us` and `products_sg` roll up to the same total.

2) Platform uptime %
- Value: `100.000%` over the last 24 hours for the core production monitor set
- Included monitors:
  - `API Catalog Discovery` (`https://api.buywhere.ai/.well-known/api-catalog`)
  - `api.buywhere.ai /health/db (DB health)` (`https://api.buywhere.ai/health/db`)
  - `Redis Health` (`https://api.buywhere.ai/health/redis`)
- Method: UptimeRobot `getMonitors` with `custom_uptime_ratios=1`
- Calculation note: all three core monitors were `up` at collection time and each reported `100.000` for the trailing 1-day window.

3) API p95 latency
- Value: `637 ms` p95 over the last 24 hours for the production API probe
- Source probe: `API Catalog Discovery` monitor on `https://api.buywhere.ai/.well-known/api-catalog`
- Supporting probe values:
  - DB health p95: `621 ms`
  - Redis health p95: `586 ms`
  - Combined p95 across the three core probe sample sets: `613 ms`
- Method: UptimeRobot response-time samples from the same 24-hour window, p95 calculated from returned `response_times`
- Calculation note: application query-log data is stale in this environment after `2026-05-22 18:44:16 UTC`, and the legacy PostHog insight endpoint denied access for this token, so the exact current p95 here is probe-based rather than end-user request-log based.

4) Current infra issues
- No active core API/DB/Redis outage is visible in the monitor set at collection time.
- Open operational/infrastructure issues still in flight:
  - `BUY-23639` (`critical`, `in_progress`): `Frontend UI health check — buywhere.ai`
  - `BUY-23641` (`high`, `in_progress`): `MCP authenticated endpoint health check`
  - `BUY-23642` (`high`, `in_progress`): `Frontend routine watchdog — alert on consecutive dispatch failures`
  - `BUY-23605` (`high`, `blocked`): `Recurring ingestion pipeline health check`
  - `BUY-23633` (`high`, `blocked`): `Close stale buywhere.ai UI-down incident BUY-22837 after confirmed recovery`
- Monitoring gap to note:
  - `api.buywhere.ai catalog stats (keyword: total_products)` is currently `paused` in UptimeRobot (`status = 9`), so that endpoint is not contributing to uptime coverage.
- Recent core-service flap history:
  - last observed API catalog `502`: `2026-05-19 22:17:44 UTC`
  - last observed DB health `502`: `2026-05-19 22:17:43 UTC`
  - last observed Redis health `502`: `2026-05-19 22:17:23 UTC`

## Source commands used

- Postgres:
  - `select count(*) from products;`
  - `select 'products_us', count(*) from products_us union all select 'products_sg', count(*) from products_sg;`
  - `select count(*) filter (where is_active), count(*) filter (where is_available) from products;`
  - issue-state lookups from `public.issues`
- UptimeRobot:
  - `POST https://api.uptimerobot.com/v2/getMonitors` with `custom_uptime_ratios=1`, `response_times=1`, `logs=1`
