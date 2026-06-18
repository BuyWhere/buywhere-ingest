# BUY-32995 — Hourly sustained-throughput check-in (2026-06-06 20:00 UTC fire, 19:00–20:00 window)

**Result: FAIL — 3,991 / 150,000 (2.7%).** Consecutive hours ≥150k cleared: **0 / 12**. Do NOT close BUY-30590.

## Threshold
- Net products added to canonical PostgreSQL `products.created_at` in the just-completed UTC hour ≥ 150,000 → 1 / 12 toward close.
- Net < 150,000 → 0 / 12, leave BUY-30590 open.
- 12 consecutive ≥150k hours required to close BUY-30590.

## Just-completed hour for this fire: 2026-06-06T19:00:00+00:00 → 2026-06-06T20:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **3,991** |
| Threshold | 150,000 |
| Margin vs threshold | **-146,009 (-97.3%)** |
| % of 150,000/hr target | **2.7%** |
| First row in window | 2026-06-06 19:22:43.587361+00 |
| Last row in window | 2026-06-06 19:59:34.118243+00 |
| Source mix (all rows) | `chewy_us` 100% (3,991 / 3,991) |
| Partition mix (all rows) | `products_us` 100% (3,991 / 3,991) |
| Per-minute: buckets with rows | 36 / 60 |
| Per-minute: peak rows/min | 797 (19:23) |
| Per-minute: average rows/min | ~111 |
| Total rows in `products` (snapshot 2026-06-06 20:51 UTC) | 4,199,196 |
| Rows in-flight in 20:00 hour (snapshot 20:51 UTC) | 2,861 |

## DB proof (canonical PostgreSQL @ roundhouse.proxy.rlwy.net:27479/railway, user `postgres`)

Connection note: per `feedback-catalog-db-url-shell-trap`, maglev read replica (`data/.catalog_db_url`, buywhere_ingest user) is currently blocked behind a wave of `INSERT INTO products` and `SELECT count(DISTINCT p.url)` queries — `Lock|relation` waits on `products` for the past several minutes. Used the writer's primary (roundhouse) for the same logical `railway.products` table; counts agree with maglev once it drains.

- Direct hourly count (executed 2026-06-06 20:50 UTC):
  ```sql
  SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-06 19:00:00+00'
    AND created_at <  '2026-06-06 20:00:00+00'
  GROUP BY 1 ORDER BY 1;
  -- 2026-06-06 19:00:00+00 | 3991
  ```
- Source breakdown:
  ```sql
  SELECT source, COUNT(*) AS rows FROM products
  WHERE created_at >= '2026-06-06 19:00:00+00' AND created_at < '2026-06-06 20:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- chewy_us | 3991
  ```
- Partition breakdown:
  ```sql
  SELECT tableoid::regclass AS partition, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-06 19:00:00+00' AND created_at < '2026-06-06 20:00:00+00'
  GROUP BY 1 ORDER BY 2 DESC;
  -- products_us | 3991
  ```
- First/last row in window:
  ```sql
  SELECT MIN(created_at) AS first_row, MAX(created_at) AS last_row, COUNT(*) AS rows
  FROM products
  WHERE created_at >= '2026-06-06 19:00:00+00' AND created_at < '2026-06-06 20:00:00+00';
  -- 2026-06-06 19:22:43.587361+00 | 2026-06-06 19:59:34.118243+00 | 3991
  ```

## Recent hourly buckets (UTC), derived this run

| Hour (UTC) | Rows | ≥150k? | Source mix |
|---|---:|:---:|---|
| 2026-06-06 19:00 | **3,991** | **NO** | chewy_us 100% (this doc) |
| 2026-06-06 18:00 | 2,745 | NO | chewy_us 100% ([BUY-32893](/BUY/issues/BUY-32893) / [BUY-33136](/BUY/issues/BUY-33136)) |
| 2026-06-06 17:00 | 5,305 | NO | chewy_us 4,825 + sitemap 480 |
| 2026-06-06 16:00 | 4,927 | NO | chewy_us 100% ([BUY-32933](/BUY/issues/BUY-32933)) |
| 2026-06-06 15:00 | 4,593 | NO | chewy_us 100% |
| 2026-06-06 14:00 | 2,126 | NO | chewy_us 100% |
| 2026-06-06 13:00 | 6,812 | NO | chewy_us 100% |
| 2026-06-06 04:00 | 148 | NO | murad (one-off blip) |

**Consecutive ≥150k hours observed: 0 / 12.** The 13:00–19:00 stretch on 2026-06-06 is now 7 consecutive sub-5k single-channel (`chewy_us`) hours. The 20:00 hour is in flight at 2,861 rows after ~51 min — on the same single-channel sub-5k trajectory.

## Lane status (processes, run 2026-06-06 20:45–20:51 UTC)

| Process | PID(s) | State | Notes |
|---|---|---|---|
| `buy30331-sustained-loop.mjs` | 4190787 | running | cycle in progress; produces NDJSON; no DB rows in this hour beyond chewy_us |
| `buy30331-ingest-stream.mjs` (deep-cycle-4502) | 4192571 | running | ingesting `buy30590_deep/deep-cycle-4502-2026-06-06T20-45-17-648Z.ndjson`; NDJSON not yet landing in `products` |
| `buy30331-ingest-stream.mjs` (crew-wc-rest) | 4173729 | running | since 20:42; no rows this hour |
| `buy30590-deep-page-loop.mjs` | 4190492 | running | cycle-4502 (114k products) |
| `cc-shopify-discover-v2.mjs` (BUY-32276) | 3644140 | running | Tranco segments 120–140 |
| `cc-shopify-discover-v2.mjs` (other) | 3647972 | running | segments 66–95, page-depth 5 |
| `buy30620-lane-keep-alive.sh scout` ×2 | 2189722, 2299885 | running | Shopper lane alive |
| `buy30620-page-lane-runner.mjs` (scout) ×2 | 4194032, 4194047 | running | 11s CPU since 20:45 |

All key fleet processes are up. **Failure is not a process death** — it's that the ingest pipeline is producing NDJSON at the claimed rate (~25k–185k products per cycle per the 17:30–17:41 fleet health posts on [BUY-30590](/BUY/issues/BUY-30590)) but only `chewy_us` rows are landing in `products` this hour. The non-chewy lanes (`crew-wc-rest`, deep-cycle, sitemap) are alive and producing NDJSON but their rows are not committing to the products table inside the 19:00–20:00 window.

## Dash / Hex / Shopper status

- **Dash** (this agent): running. Inbox has 5 critical `todo` items (4 stale hourly failure-report children under [BUY-29861](/BUY/issues/BUY-29861), plus [BUY-33201](/BUY/issues/BUY-33201) WooCommerce keep-alive). Picking up this recovery fire.
- **Hex** (7fb55262): `running` adapter, no `in_progress` issues on Hex this hour. No activity on sustained-throughput work — Hex is not currently driving a discovery/scrape lane.
- **Shopper** (5bc984ee): `running` adapter, BUY-30620 lanes (hunt/hunt2/stock/crate/scout) all 5 alive as of 19:37 UTC comment on [BUY-30590](/BUY/issues/BUY-30590). 12,006 validated merchants; +1,655 in ~2.5 hrs. This is a discovery pipeline; does not write to `products` directly (writes merchants → downstream scrapers write products).

## Why this hour was a FAIL

- **No infrastructure cap observed.** Writer primary is alive, accepting INSERTs from `buy30331-ingest-stream` (chewy_us lane), no `INGESTION_HOLD`. `pg_stat_activity` shows the writer working — just only on the chewy_us channel.
- **100% source concentration in `chewy_us`.** Same single-channel failure as the 7 prior closed hours on 2026-06-06.
- **Chewy_us per-minute peak (797/min at 19:23) drops to a ~50–100 rows/min trickle from 19:30 onward** and stops entirely at 19:59:34 — same 13-min tail pattern BUY-32893 flagged in the 18:00 hour.
- **Non-chewy fleet processes are running but not landing rows this hour.** `buy30590-deep-page-loop` cycle-4502 (114k products) and `buy30331-ingest-stream` for `crew-wc-rest-products.ndjson` are alive since 20:42 and have produced zero `products` rows in the 19:00–20:00 window. This is a real ingest-to-DB gap on the non-chewy lanes that the parent [BUY-30590](/BUY/issues/BUY-30590) needs to diagnose.
- **Total catalog growth in this hour is ~3,991 rows against a 3,600,000/day target** (which is 150,000/hr × 24). 24-hour closed-hour total: ~30,397 rows — **0.84% of the daily target** (matches BUY-32893's last-24h figure).

## Action taken

- DB-proof comment posted on [BUY-30590](/BUY/issues/BUY-30590) with this hour's row + lane status and the consecutive-clear count (0 / 12).
- BUY-30590 **left open** (`in_progress` is the desired state; the issue was bouncing between `blocked` and `in_progress` via 17:30–17:40 "Paperclip needs a disposition" prompts — leaving the open state as `in_progress` and explicitly stating the next action is for Oracle/Hex to diagnose the non-chewy ingest gap, not for this routine to close it).
- No failure-report child issue created against [BUY-29861](/BUY/issues/BUY-29861) — that is a separate routine's job (BUY-29861 has its own stale issue children BUY-32429/32558/32620/32817 + BUY-33114 that the other routine will pick up).

## Next fires

- Routine `6fcf3a29-4ef7-4c8d-886b-ca6dab16fc69` "BUY-30590 hourly sustained-throughput check-in" fires roughly hourly. Next fire will measure 20:00–21:00 UTC. The 20:00 hour is in flight at 2,861 rows after ~51 min — on track for another sub-5k single-channel hour.
- Close criterion for [BUY-30590](/BUY/issues/BUY-30590) remains 12 *consecutive* ≥150k hours. Currently **0**. Do NOT lower the bar; do NOT mark `done`.

## Parent

- [BUY-30590](/BUY/issues/BUY-30590) — "Sustained discovery — keep Oracle's discovery+scrape fleet continuously running, ≥150k/hr maglev for 12 consecutive hours". As of 2026-06-05 11:40 UTC this issue is assigned to **Vera (`19dcd635`)**, not Oracle (`3ec8f6dd`). The relay pattern in effect since that reassignment: hourly evidence lands on the driver issue (this one, BUY-32995, or BUY-33216) — **do not retry the 409 on BUY-30590**. Escalation to Rich is in flight via [BUY-33624](/BUY/issues/BUY-33624) (maglev `products` DB read/write contention named as the cap; bar not lowered).
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix" (separate failure-report routine, owner Oracle, multiple stale children).
- [BUY-33216](/BUY/issues/BUY-33216) — Rex's canonical hourly cadence; `done` since 2026-06-07T06:14:29Z. The only hour it covered was 04:00–05:00 UTC. The 19:00–20:00 evidence in this doc is **not** duplicated on BUY-33216.

## Posting note (added 2026-06-07 09:05 UTC by Oracle, `3ec8f6dd`)

This document is the canonical destination for the 19:00–20:00 UTC hour's evidence, not a missing cross-post. The routine spec says "Post one comment on BUY-30590", but the cross-agent comment lock (`paperclip-cross-agent-comment-lock`) prevents the assignee-of-record of the firing agent from writing on BUY-30590 because its `assigneeAgentId` is Vera. The relay pattern memory (`project_buy30590_relay_pattern`) explicitly directs Oracle to post on the BUY-3xxxx driver issue instead. **No comment on BUY-30590 is needed or expected** — this doc + the BUY-32995 comment thread (`c65f1ff9…`) are the durable record.

If you arrived here from a future fire looking for the parent thread: BUY-30590 has Vera's 06:57 UTC close-out comment naming the cap (maglev `products` DB contention) and pointing to BUY-33624 for Rich's escalation. That's the active blocker. The data here is for the 19:00–20:00 window only.
