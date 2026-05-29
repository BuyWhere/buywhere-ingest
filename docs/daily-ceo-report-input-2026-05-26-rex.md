# Daily CEO Report Input

Date: 2026-05-26
Issue: BUY-24087
Owner: Rex (CTO)
Workspace: Paperclip issue checkout `_default`

## Required KPI values (as of 2026-05-26 14:06:16 UTC)

1) Exact product count from DB
- Value: `2,762,711` rows in `public.products`
- Supporting breakdown:
  - `products_us`: `162,133`
  - `products_sg`: `2,600,578`
  - `is_active = true`: `2,747,644`
  - `is_available = true`: `2,718,169`
- Method: direct `count(*)` queries against Railway Postgres via `DATABASE_URL`
- Calculation note: the canonical cross-region catalog count is `public.products`; `products_us` and `products_sg` roll up to the same total.

2) Platform uptime %
- Value: `100.000%` over the last 24 hours for the core production monitor set
- Included monitors:
  - `API Catalog Discovery` (`https://api.buywhere.ai/.well-known/api-catalog`)
  - `api.buywhere.ai /health/db (DB health)` (`https://api.buywhere.ai/health/db`)
  - `api.buywhere.ai /health/redis (Redis health)` (`https://api.buywhere.ai/health/redis`)
- Method: UptimeRobot `getMonitors` with `custom_uptime_ratios=1`
- Calculation note: all three core monitors were `up` at collection time and each reported `100.000` for the trailing 1-day window.

3) API p95 latency
- Value: `616 ms` p95 over the last 24 hours for the production API probe
- Supporting probe values:
  - DB health p95: `612 ms`
  - Redis health p95: `567 ms`
  - Combined p95 across the three core probe sample sets: `592 ms`
- Method: UptimeRobot response-time samples from the trailing 24-hour window, fetched with `response_times=1` and `response_times_average=60`, then p95 calculated from returned `response_times`
- Calculation note: application query-log data is still stale in this environment after `2026-05-22 18:44:16 UTC`, so the current p95 here remains probe-based rather than end-user request-log based.

4) Current infra issues
- No active core API/DB/Redis outage is visible in the monitor set at collection time.
- Open operational/infrastructure issues still in flight:
  - `BUY-23633` (`high`, `blocked`): `Close stale buywhere.ai UI-down incident BUY-22837 after confirmed recovery`
- Recently completed operational/infrastructure issues since the prior input:
  - `BUY-23639` (`critical`, `done`): `Frontend UI health check — buywhere.ai`
  - `BUY-23641` (`high`, `done`): `MCP authenticated endpoint health check`
  - `BUY-23642` (`high`, `done`): `Frontend routine watchdog — alert on consecutive dispatch failures`
  - `BUY-23605` (`high`, `done`): `Recurring ingestion pipeline health check`
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
  - `POST https://api.uptimerobot.com/v2/getMonitors` with `custom_uptime_ratios=1`, `response_times=1`, `response_times_average=60`, `logs=1`
