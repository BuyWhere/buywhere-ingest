# DAILY CATALOG PACE CHECK & SHORTFALL REPORT — 2026-07-17

Report date: 2026-07-17 UTC
Agent: Oracle | Issue: BUY-59359 | Parent: BUY-24561
Calendar days remaining to June 30: **0** (deadline passed)
DB target: `data/.catalog_db_url` pinned maglev URL (`maglev.proxy.rlwy.net:31310`)

## Live Maglev Measurements (2026-07-17)

| Metric | Value | Source |
|---|---|---|
| Products (planner estimate `reltuples`) | **288,934,688** | `pg_class.reltuples` |
| Products (live `n_live_tup`) | **288,989,986** | `pg_stat_user_tables` |
| Cumulative inserts (`n_tup_ins`) | **228,106,899** | `pg_stat_user_tables` |
| Merchants (total rows) | **158,061** | `COUNT(*) FROM merchants` |
| Merchants with products (`products_count>0`) | **71,890** | `COUNT(*) FILTER` |
| Planner-estimated distinct `products.merchant_id` | **29,949** | `pg_stats.n_distinct` |
| Planner-estimated distinct `products.platform` | **28** | `pg_stats.n_distinct` |
| Planner-estimated US share of products | **~9.85%** | `pg_stats.most_common_freqs[0]` (country_code=`US`) |

`pg_stat_user_tables` last analyze timestamps:
- `merchants`: last_analyze 2026-06-22 19:42Z; last_autoanalyze 2026-07-08 03:07Z
- `products`: last_analyze 2026-07-17 04:30Z; last_autoanalyze 2026-07-03 17:56Z

## 24h Growth (vs 2026-07-16 — prior pace report)

| Metric | 2026-07-16 | 2026-07-17 | Δ |
|---|---|---|---|
| Products (reltuples) | 288,024,448 | 288,934,688 | +910,240 |
| Products (n_live_tup) | 288,060,457 | 288,989,986 | +929,529 |
| Cumulative inserts | 227,025,660 | 228,106,899 | +1,081,239 |
| Merchants (total) | 158,050 | 158,061 | +11 |
| Merchants with products | 71,890 | 71,890 | 0 |
| Distinct sources | 4,159 | timed out | — |
## Status vs June 30 Goals (Deadline: Passed)

### Goal 1: 100M real products — ACHIEVED

| Field | Value |
|---|---|
| Target | 100,000,000 |
| Today (planner `reltuples`) | 288,934,688 |
| Today (live `n_live_tup`) | 288,989,986 |
| Status | **✅ MET** (~289% of target) |

### Goal 2: 150,000 distinct real merchants — SHORTFALL

| Field | Value |
|---|---|
| Target | 150,000 |
| Today (merchants total / with products) | 158,061 / 71,890 |
| Live product-backed measure (planner `n_distinct`) | 29,949 distinct `products.merchant_id` |
| Gap to 150K product-backed | −120,051 (live planner estimate) |
| 24h change | 0 merchants with products (flat vs 71,890); −306 on product-backed-measure estimate (30,255→29,949 — minor planner variance, not a regression) |
| Status | **MISSED** (deadline passed; merchant diversity flat at 71,890 — no net merchant wins in ~48h) |

### Goal 3: 50% US product coverage — NOT MET

| Field | Value |
|---|---|
| Target | 50% |
| Planner-estimated US share of products | **~9.85%** (sample MC frequency, `country_code='US'`) |
| Status | **PLANNER SIGNAL ~9.9% vs 50% target — far below target; live COUNT verification blocked by timeout on 289M rows. Flagged as MISSED on planner evidence.** |

### Goal 4: 35 e-commerce platforms — SHORTFALL

| Field | Value |
|---|---|
| Target | 35 |
| Today (planner `n_distinct`) | **28** distinct platforms |
| Top observed countries (most_common_vals) | US, SG, UK, ID, DE, MY (directional) |
| Gap | −7 (−20.0%) |
| 24h change | +2 (26→28 — continued slow improvement, now 80% of target) |
| Status | **MISSED** (deadline passed; 28/35 = 80% of target, improving gradually) |

## Summary

- **✅ 100M Products**: Achieved and growing (~289M, ~289% of target); +910K reltuples / +929K n_live_tup over ~24h — **significantly below the ~3.8M/day cadence of prior periods, reflecting the weak 2.2M row day on 2026-07-15 and continued low throughput into 2026-07-16 (20Z hour FAIL at 23.6% of target).**
- **❌ 150K Merchants**: Missed (71,890 merchants with products; planner-estimated 29,949 product-backed merchants). Zero net merchant wins in ~48h — merchant acquisition flatlined.
- **❌ 50% US Coverage**: Missed on planner evidence (sample US share ~9.85%, far below 50%; live COUNT verification blocked by timeout on 289M rows).
- **❌ 35 Platforms**: Missed but slowly improving (28 distinct platforms, 80% of target — up from 26).

No failure child for the 100M-product goal (already MET). The other three goals remain genuine shortfalls versus the June-30 ambition; deadline passed (2026-06-30) and no corrective assignment is auto-created. **Notable: product ingestion pace has dropped sharply** in the last 48h (from ~3.8M/day to ~0.9M/day) — this warrants monitoring but does not constitute a new shortfall against any June-30 goal since the deadline has already passed.
## Evidence Queries

```sql
-- products planner estimate (no COUNT(*) -- that times out at 289M+ rows)
SELECT reltuples::bigint FROM pg_class WHERE relname='products';        -- 288934688
-- live table statistics
SELECT n_live_tup::bigint, n_tup_ins::bigint FROM pg_stat_user_tables WHERE relname='products';  -- 288989986, 228106899
-- merchants total + product-backed
SELECT (SELECT count(*) FROM merchants) AS merchants_total,
       (SELECT count(*) FROM merchants WHERE products_count > 0) AS merchants_with_products; -- 158061 / 71890
-- planner estimates for dimensions (avoid live COUNT on products)
SELECT attname, n_distinct FROM pg_stats WHERE schemaname='public' AND tablename='products'
 AND attname IN ('platform','source','merchant_id');                    -- platform 28, source 1616, merchant_id 29949
-- planner US share via most_common_freqs on country_code
SELECT most_common_vals, most_common_freqs FROM pg_stats
 WHERE schemaname='public' AND tablename='products' AND attname='country_code';
--  -> {US,SG,UK,ID,DE,MY} ; {0.09853333, 0.050666668, 0.0011, 0.001, 0.00083333335, 0.0006}
```

## Disposition

- Issue status: done (no failure child against the 100M-product goal -- that goal is MET; remaining shortfalls on merchants / US coverage / platforms documented above against the already-passed deadline).
- **Notable observation**: 24h product growth slowed to ~0.91M from the prior ~3.8M/day cadence. Per 2026-07-16 CEO report, 2026-07-15 hourly throughput was 2.2M rows (0.64x plan) with only 4/24 PASS hours. This pace slowdown is a monitoring signal but does not create a new failure child since the June-30 deadline has already passed and the 100M product goal is well exceeded.
- Continuation path: next daily catalog pace check runs again on the routine schedule.
