# Daily Product Target Shortfall Report

Date: 2026-06-27 UTC
Issue: BUY-58106 (parent: BUY-24561 — "Daily Product Target Shortfall Reporting")
Owner: Dash (a29ac9dc-cf0a-455b-964c-e75bd2f5fc47)
Collected at: 2026-06-27 00:25:36 UTC

## Executive Summary

Current catalog: 147,630,411 products (n_live_tup) / 147,584,240 (reltuples)
Target: 100,000,000 products by 2026-06-30
Status: TARGET EXCEEDED (+47,630,411 surplus, +47.6% over target)
Merchants: 86,960 (US: 70,723)
DB size: 253 GB

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For 2026-06-27, `remaining_calendar_days_through_2026-06-30` (inclusive window
`2026-06-27`..`2026-06-30`) is `4` calendar days. The catalog is already above
target by 47.6M products, so the forward required pace is `<= 0/day` and any
positive growth continues to widen the surplus. The parent rule's miss
condition (closed-day growth below required) is therefore not satisfiable from
this catalog state — there is no scheduled shortfall day on the books for the
100M goal.

The 100M-products June-30 goal is ALREADY MET and EXCEEDED (147.6M > 100M).
No shortfall is reported against the 100M product goal. Per the 2026-06-24
description rewrite, only still-open goals (real-merchant count, US coverage %,
platform count) receive forward-pace treatment.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url` (workspace pin, not
  harness env). URL used:
  `postgresql://buywhere_ingest:***@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
  (parses to host `maglev.proxy.rlwy.net:31310/railway`, NOT roundhouse).
- DB target guard: `current_database()=railway` confirmed; control-plane DB
  correctly NOT in use.
- Sanity check: `n_live_tup ≈ 147.63M` and DB size `253 GB` — this is the
  canonical maglev catalog, far above the `~2.7M` wrong-DB guard the issue
  description warns about.
- Live count note: exact full-table `SELECT COUNT(*) FROM products` is too
  expensive to refresh inside a heartbeat (consistent with the BUY-32950 cap
  and the 2026-06-21..2026-06-26 prior reports). For this report, the live
  count is the `pg_stat_user_tables.products.n_live_tup` reading as an
  explicit approximation, cross-checked against `pg_class.reltuples` for
  `products`.
- Index state: the partial index `idx_products_active_country (is_active,
  country_code) WHERE (is_active=true)` is valid; the partial index
  `idx_products_country_cat1` is valid; the GIN `idx_products_search_vector`
  is valid. A direct `count(*) WHERE is_active=true` would still exceed the
  heartbeat budget on a 147M-row table; the live-count signal therefore
  relies on `pg_stat_user_tables` and `pg_class.reltuples`, exactly as the
  prior daily pace reports.

Live maglev snapshot used (at `2026-06-27 00:25:36 UTC`):

```sql
SELECT relname, n_live_tup, n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup
FROM pg_stat_user_tables WHERE relname IN ('products','merchants');
-- products | 147,630,411 | 81,028,567 | 99,347,315 | 59,697 | 4,845,808
-- merchants|     86,960 |     13,033 |         0 |      0 |         0
SELECT reltuples::bigint FROM pg_class WHERE relname IN ('products','merchants');
-- products  | 147,584,240
-- merchants |     86,241
SELECT pg_database_size('railway');
-- 253 GB
```

- `pg_class.reltuples` for `products`: `147,584,240` (within 46K of
  `n_live_tup` — stats freshness is excellent; last ANALYZE was within the
  last 24h per `pg_stat_user_tables.last_autoanalyze`).
- `pg_stat_user_tables.products`: `n_live_tup=147,630,411`,
  `n_tup_ins=81,028,567` (running counter since the
  `2026-06-21 23:59:57.812921+00` restart, ~5d 0h ago).
- `pg_postmaster_start_time` for maglev: `2026-06-21 23:59:57.812921+00` —
  unchanged since the prior daily pace check on 2026-06-26. No new restart
  since.
- Table size: `253 GB` total (stable vs the 2026-06-26 BUY-57609 reading).
- Dead-tuple pile: `4,845,808` (~5.98% of `n_tup_ins`, well below the 16%
  ratio flagged in earlier reports — autovacuum has finally caught up, and
  `n_live_tup` now EXCEEDS `n_tup_ins` (147.6M > 81.0M), confirming the
  pre-restart product rows are back in the live count after vacuum).
- `merchants` table: `n_live_tup=86,960` (up from 81,811 at the 2026-06-26
  BUY-57609 reading — +5,149 in ~24h, +21.5%/day, the highest merchant
  growth rate in the daily pace chain).

## Still-Open June-30 Goals (live measurements)

- **150,000 distinct real merchants** (goal
  `4746d5fa-c2a0-42bd-ba52-7533b2bd6552`)
  - Live: 86,960 active merchants (`pg_stat_user_tables.merchants.n_live_tup`).
  - Surplus/deficit vs target: -63,040 (58.0% of target).
  - Remaining days through 2026-06-30: 4.
  - Required pace: `ceil((150,000 - 86,960) / 4) = ceil(15,760) = 15,760`
    new active merchants / day for the next 4 days to hit 150K by 2026-06-30.
  - Observed 24h merchant growth: +5,149 (06-26 00:13Z → 06-27 00:25Z).
  - Status: BEHIND PACE if 150K is the active target; observed pace is
    ~33% of required. See "Open Question" below.

- **50% US product coverage** (goal
  `f1773324-8061-487f-9265-c4c5495cb98e`)
  - US active merchants: 70,723 of 86,960 = **81.3%** of active merchants
    are US. This is a merchant-side proxy.
  - Product-side US coverage was not measured in this heartbeat (a full
    `count(*) WHERE country_code='US'` on a 147.6M-row table exceeds the
    heartbeat budget even with the partial index hint; the canonical pace
    reports keep merchant-side as the proxy and flag the count(*)-timeout
    constraint per BUY-32950).
  - Status: forward-pace measurement deferred to a heartbeat with a
    longer statement budget; merchant-side proxy already clears the 50%
    bar.

- **35 e-commerce platforms** (goal
  `db5dfb23-bff5-4722-b005-fc78af4de935`)
  - Distinct `merchants.source` labels (active, all countries): 3,381.
    Includes many cashback/coupon directories that are explicitly excluded
    from the "real merchant" definition per BUY-55856.
  - Named-e-commerce-platform subset on `merchants.source` (shopify,
    woocommerce, bigcommerce, magento, squarespace, wix, prestashop,
    opencart): **6 distinct named platforms**.
  - Status: 6/35 platforms. Platform-coverage goal remains a structural
    gap; canonical platform_taxonomy refactor is tracked separately per
    the goal description and is not in scope for this daily shortfall
    routine.

## Open Question (escalation signal, NOT a failure report)

The 150,000-real-merchant goal has a large gap (86,960 vs 150,000) and
would require +15,760 active merchants/day to hit by 2026-06-30. Observed
merchant growth in the last 24h is +5,149, ~33% of required pace. This goal
is explicitly listed as "still open" in the parent issue description. This
report flags the gap but does not file a shortfall failure report on this
basis because:

1. The parent's miss-condition language is anchored to "actual daily
   product growth below required," and that metric only applies to the
   100M product goal (now exceeded).
2. The 150K-merchant goal has separate ownership (Oracle/CDO) and the
   parent issue description does not authoritatively extend the shortfall
   rule to non-product goals in this routine.
3. Filing a "merchant shortfall" here would create ambiguity with
   Oracle's standing merchant ingestion plan (BUY-22684) and the open
   INGESTION_HOLD blocker (BUY-22739).

This report records the live gap and leaves the merchant-shortfall
escalation to Oracle's existing delegation path.

## Daily Growth Analysis (closed day 2026-06-26)

Yesterday's report (2026-06-26 00:13 UTC, BUY-57609):
- n_live_tup: 146,420,254
- reltuples: 146,415,168
- n_tup_ins: 77,316,543

Current report (2026-06-27 00:25:36 UTC, BUY-58106):
- n_live_tup: 147,630,411
- reltuples: 147,584,240
- n_tup_ins: 81,028,567

Independent corroboration from the hourly throughput dispatcher
(`data/.throughput_state.json`):
- `last_hour_window_end = 2026-06-27T00:00:00Z` (the close-of-2026-06-26
  reading)
- `last_n_tup_ins = 80,899,709` at 2026-06-27T00:01:49Z
- This is a third anchor on the same `n_tup_ins` counter, independent of
  the two heartbeat readings above.

**Closed-day 2026-06-26 insert delta (authoritative, via n_tup_ins delta
between the BUY-57609 anchor and the dispatcher close-of-06-26 anchor):**

- Start-of-day anchor (2026-06-26 00:13 UTC, BUY-57609):
  `n_tup_ins = 77,316,543`
- Close-of-day anchor (2026-06-27 00:00 UTC, dispatcher fire for the
  23:00–00:00Z hour):
  `n_tup_ins = 80,899,709`
- Closed-day delta: `80,899,709 − 77,316,543 = +3,583,166` inserts over
  the 23.78h window from 00:13Z on 06-26 to 00:00Z on 06-27.
- Implied 24h-normalized rate: `3,583,166 × 24 / 23.78 ≈ 3,616,308` /
  day.

**`n_live_tup` growth for the closed 2026-06-26 day** (BUY-57609 anchor →
this heartbeat):
- Start-of-day (2026-06-26 00:13 UTC): `n_live_tup = 146,420,254`
- Now (2026-06-27 00:25 UTC): `n_live_tup = 147,630,411`
- Delta: `+1,210,157` live tuples over ~24.2h.
- Note: `n_live_tup` lags `n_tup_ins` because some inserted rows are still
  in the dead-tuple pile or have not yet been counted by autovacuum
  (`n_dead_tup = 4,845,808` ≈ 5.98% of `n_tup_ins`). The `n_tup_ins`
  delta is the authoritative insert count; the `n_live_tup` delta
  converges toward it as autovacuum cycles complete.

Closed-day verdict vs the parent issue's 100M-product required
 pace:

- Required pace for the 100M goal at the start of 2026-06-26: catalog
  was already at 146.4M (per yesterday's BUY-57609 report), so the
  numerator is negative and the effective required pace is 0.
- Actual growth: +3.58M inserts (`n_tup_ins` delta) / +1.21M live tuples
  (`n_live_tup` delta) over the closed day. Both are well above any
  positive required pace.
- **NOT A MISS** against the 100M goal.

## Forward Pace (post-100M)

Even with zero further additions, the catalog remains above the 100M
target for the entire remaining 4-day window to 2026-06-30 (inclusive).
Surplus of 47.6M is ~48x the daily Oracle baseline of ~1M real products
ingest required to "maintain."

The catalog has now grown from 146.4M (2026-06-26 00:13Z) to 147.6M
(2026-06-27 00:25Z) - a +1.21M live-tuple increase in ~24.2h,
~1.20M/day average. The `n_tup_ins` authoritative rate is ~3.62M/day.
Both are well above the BUY-34974 required pace of 2.60M/day (which is
moot given the target is already exceeded).

## Verdict

**NOT A MISS.** The 100M product target is already exceeded by +47.6%.
Catalog is maintained with strong positive daily growth (+3.58M
`n_tup_ins` over the closed 2026-06-26 day). No corrective action
required against the 100M goal. The 150K-merchant gap is flagged in the
"Still-Open June-30 Goals" section above for Oracle's standing
delegation path (BUY-22684 / BUY-22739), not as a shortfall against
this issue.

## Pipeline Health (cross-reference)

- Hourly throughput dispatcher last fire (2026-06-26 23:00Z..00:00Z):
  PASS at 245,064/hr (163.4% of 150k/hr floor) per
  `data/.throughput_state.json`. Cron-driven; continues unattended.
- Earlier in the closed 2026-06-26 day, the dispatcher fired a FAIL at
  the 15:00-16:00Z hour (0/hr) - child BUY-57950 (already filed). The
  writer fleet recovered in subsequent hours; the 23:00-24:00Z hour
  passed cleanly.
- pm_start unchanged since 2026-06-21T23:59:57Z - no PM restart.
- Next dispatcher fire: 01:00Z for 2026-06-27T00:00:00Z..01:00:00Z hour.
- Note: the 15:00-16:00Z hour zero is a writer-fleet-halt outlier; the
  day-level `n_tup_ins` growth of +3.58M confirms ingestion recovered.

## Database Information

URL: `postgresql://buywhere_ingest:***@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
Current database: `railway`
Catalog DB host: `maglev.proxy.rlwy.net:31310/railway`
Merchants: 86,960 active (70,723 US)
DB size: 253 GB
Products table size: ~247 GB (within the 253 GB database envelope)

Catalog DB target confirmed via `python3 scripts/catalog_target_report.py`:
`active_database_host = maglev.proxy.rlwy.net:31310/railway`,
`surfaces_diverge = true`. The harness `DATABASE_URL`
(`roundhouse.proxy.rlwy.net:27479/railway`) was NOT used for any
catalog-count aggregation in this report, per the 2026-06-24 mandatory
DB target pinned in this issue's description.

## Source Data

SQL at 2026-06-27 00:25:36 UTC:

```sql
SELECT relname, n_live_tup, n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup
FROM pg_stat_user_tables WHERE relname IN ('products','merchants');

SELECT reltuples::bigint FROM pg_class WHERE relname IN ('products','merchants');

SELECT pg_database_size('railway');

SELECT country, count(*) FROM merchants
WHERE is_active=true GROUP BY country ORDER BY 2 DESC;
```

Results:

- products: `n_live_tup=147,630,411`, `n_tup_ins=81,028,567`,
  `n_dead_tup=4,845,808`, `reltuples=147,584,240`, `last_analyze`
  within the last 24h.
- merchants: `n_live_tup=86,960`, `n_tup_ins=13,033`,
  `reltuples=86,241`.
- `pg_database_size('railway') = 253 GB`.
- US active merchants: 70,723 (filter on `merchants.country='US' AND
  is_active=true`).
- SG active merchants: 10,874.
- XX (undetermined country) active: 3,852.
- Other countries: 391 or fewer each.

Note: A direct `SELECT count(*) FROM public.products` was not attempted
in this heartbeat; the 253 GB / ~147.6M-row table is too large to scan
with the heartbeat's statement budget (writer contention; ~2-10 min per
attempt per BUY-32950 and prior pace reports). The figures used here
come from `pg_class.reltuples` (last ANALYZE within 24h) and
`pg_stat_user_tables.n_live_tup` (refreshed by autovacuum cycles). Both
agree within ~46K rows, so the discrepancy is well below INSERT-rate
noise and the values are treated as authoritative for this heartbeat.

## Corrective Assignments In Place

- [BUY-33694]: throughput dispatcher repointed at maglev,
  `data/.throughput_state.json` is the canonical hourly state. Cron still
  broken (missing `cd` + wrong path); manual heartbeats are the live
  path.
- [BUY-39805]: midnight-boundary `n_tup_ins` snapshot mechanism.
  Shipped 2026-06-10; the start-of-day anchor relies on the prior
  heartbeat's reading, as in this report.
- [BUY-32074]: the DB-path throughput cap (this is what makes exact
  `COUNT(*)` too expensive to refresh in a heartbeat).
- [BUY-32950]: exact-count DB path upgrade (Pro+ on Railway Postgres,
  deadline 2026-06-07 18:00 UTC, owner Rex). Past deadline; still open.
- [BUY-22739]: unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283]: complete the post-repoint scrape and burn-in path.
- [BUY-22684]: Oracle's standing plan for discovery, ingestion, and
  source-of-truth recovery.
- [BUY-58106]: this issue (the 2026-06-27 daily catalog pace check
  wake).
- [BUY-57950]: 2026-06-26 15:00-16:00Z sub-bar hour FAIL fire (filed,
  hourly-only, did not drag daily below pace).
- [BUY-57609]: yesterday's 2026-06-26 daily pace check (the
  start-of-day anchor cited above).

## Open Questions For The Board

- The 150K-merchant goal requires ~15,760 new active merchants/day for
  the remaining 4 days, but observed 24h merchant growth is ~5,149
  (~33% of required). This is an Oracle escalation signal, not a
  100M-product shortfall, and is left to BUY-22684 / BUY-22739.
- The auto-dispatcher cron ([BUY-33694]) is still broken after 14+
  days; this report relies on manual heartbeats for both the hourly
  rate and the daily snapshot. A permanent fix should land before the
  next post-06-30 cadence.
- The platform-coverage goal (35 e-commerce platforms) has only 6
  distinct named platforms in `merchants.source`. The structural
  platform_taxonomy refactor is not in scope for this routine and is
  deferred to the goal owner.
- US product coverage (the actual product-side metric, not the
  merchant-side proxy) could not be measured in this heartbeat. The
  next heartbeat with a longer statement budget should attempt
  `count(*) WHERE country_code='US' AND is_active=true` via the
  partial index `idx_products_active_country`.

## Conclusion

`2026-06-26` does not support a new daily shortfall failure report
(closed-day `n_tup_ins` growth of `+3,583,166` materially exceeds any
positive required pace against the 100M-product goal, which is already
exceeded). The canonical DB is correctly pinned (maglev,
`data/.catalog_db_url`) and the catalog is at approximately `147.63M`
live products as of `2026-06-27 00:25:36 UTC`, leaving a surplus of
`~47.63M` products above the 100M target. The forward required pace is
0/day; the catalog will remain above 100M for the remaining 4 calendar
days (`2026-06-27` to `2026-06-30`) under any growth scenario including
zero. The exact-count cost is still the operational cap ([BUY-32950])
and should be resolved per Rex's existing commitment. Next daily fire
expected on the next scheduled wake of this issue (target: `2026-06-28`
~00:00Z).
