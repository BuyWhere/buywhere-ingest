# Daily Product Target Shortfall Report

Date: 2026-06-09 UTC
Issue: BUY-36452
Owner: Oracle
Collected at: 2026-06-09 00:12:47 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-09` through `2026-06-30`, which is `22` calendar days.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url`
- URL used: `postgresql://buywhere_ingest@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- Catalog target sanity (`scripts/catalog_target_report.py`): `active_database_host = maglev.proxy.rlwy.net:31310/railway`, `surfaces_diverge = true` (control-plane DB correctly NOT in use)
- Exact freshness check: `SELECT now() AT TIME ZONE 'utc', updated_at AT TIME ZONE 'utc' FROM public.products WHERE is_active = true ORDER BY updated_at DESC LIMIT 1;`
- Exact freshness result: query time `2026-06-09 00:12:47.646746 UTC`, latest active-row update `2026-06-09 00:11:09.053951 UTC`
- Live count note: exact full-table `COUNT(*)` scans on `public.products` again exceeded heartbeat-friendly runtime on the canonical DB. For today's live totals, this artifact uses the current `pg_stat_user_tables.n_live_tup` estimate plus the latest analyzed `pg_stats` frequency for `is_active`.
- Approximate live count queries used:

```sql
select schemaname, relname, n_live_tup, n_mod_since_analyze, last_analyze, last_autoanalyze
from pg_stat_user_tables
where relname = 'products';

select attname, null_frac, n_distinct, most_common_vals, most_common_freqs
from pg_stats
where tablename = 'products' and attname = 'is_active';
```

- Approximation basis:
  - `n_live_tup = 56,086,878`
  - latest analyzed `is_active=true` frequency = `0.9873`
  - approximate current active products = `round(56,086,878 * 0.9873) = 55,374,575`
- Closed-day proof basis for `2026-06-08` UTC: dated hourly throughput artifacts on the canonical DB, especially:
  - [docs/buy-35306-hourly-throughput-check-2026-06-08T06.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-35306-hourly-throughput-check-2026-06-08T06.md)
  - [docs/buy-35353-hourly-throughput-check-2026-06-08T07.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-35353-hourly-throughput-check-2026-06-08T07.md)
  - [docs/buy-35625-hourly-throughput-check-2026-06-08T13.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-35625-hourly-throughput-check-2026-06-08T13.md)
  - [docs/buy-35730-hourly-throughput-check-2026-06-08T17.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-35730-hourly-throughput-check-2026-06-08T17.md)
  - [docs/buy-35777-hourly-throughput-check-2026-06-08T18.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-35777-hourly-throughput-check-2026-06-08T18.md)
  - [docs/buy-35887-hourly-throughput-check-2026-06-08T19.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-35887-hourly-throughput-check-2026-06-08T19.md)
  - [docs/buy-36008-hourly-throughput-check-2026-06-08T20.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-36008-hourly-throughput-check-2026-06-08T20.md)
  - [docs/buy-36146-hourly-throughput-check-2026-06-08T21.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-36146-hourly-throughput-check-2026-06-08T21.md)
  - [docs/buy-36280-hourly-throughput-check-2026-06-08T22.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-36280-hourly-throughput-check-2026-06-08T22.md)
  - [docs/buy-36417-hourly-throughput-check-2026-06-08T23.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-36417-hourly-throughput-check-2026-06-08T23.md)
- Guard note: older workspace shortfall artifacts dated before the `2026-05-31` DB-target correction used the wrong control-plane DB and are not valid baselines for this report.

## Daily Result

- Approximate current active products: `55,374,575`
- Approximate current real products (`n_live_tup`): `56,086,878`
- Exact latest observable active-row update on the canonical DB: `2026-06-09 00:11:09.053951 UTC`
- Remaining active products to target: `44,625,425`
- Approximate required products per day from `2026-06-09` forward: `2,028,429`
- Prior published daily required pace from the `2026-06-06` report: `2,755,024`
- Conservative lower bound for closed-day `2026-06-08` inserted rows, reconstructed from hourly DB-proof artifacts: `12,900,511`

Clarification:

- The live active/real totals above are approximations, not exact `COUNT(*)` values. They are based on canonical Postgres table statistics, not the control-plane DB, and are good enough to size today's remaining pace while the exact whole-table scan remains expensive.
- The closed-day decision for `2026-06-08` does not depend on the approximation. The hourly artifact series already proves a conservative lower bound of `12.9M` inserted rows on the canonical DB, which is materially above any plausible daily requirement in this reporting window and far above the last published required pace (`2,755,024/day`).
- The canonical DB is actively mutating as of `2026-06-09 00:11 UTC`, so this is not a frozen-table day.

## Why `2026-06-08` Was Not A Miss

1. Even the deliberately conservative hourly lower-bound series for `2026-06-08` sums to `12,900,511` inserted rows on the canonical DB.
2. The strongest windows were broad, not isolated: `13:00–14:00Z` alone proved `~1,170,360` inserts, `17:00–18:00Z` proved `~3,646,104`, and `18:00–19:00Z` proved `~4,095,954`.
3. Although some hours missed the hourly `150,000/hr` threshold and generated their own failure children (`20:00–21:00Z`, `21:00–22:00Z`, `22:00–23:00Z`), the full UTC day still cleared daily pace by a wide margin.
4. Maglev restarts and the invalid `products_created_at_idx` forced the hourly system onto `n_tup_ins`-delta proofs for much of the day, but those proofs were still sufficient to reject a daily-shortfall conclusion.

## Failure Days In The Reporting Window

The "failure report on any missed day" rule applies to closed UTC days where active-product growth fell below the required pace at the start of that day.

- `2026-06-08` UTC (closed day measured by this report): **NOT A MISS** on the evidence available in this heartbeat. The conservative lower-bound insert proof (`12,900,511`) is far above the prior published required pace and far above the remaining daily pace implied by today's live catalog size.
- No new daily-failure report is filed for `2026-06-08`.

Prior misses already documented in this series (for context, not re-filed here):

- `2026-06-03` — documented in `docs/daily-product-target-shortfall-2026-06-04.md`.
- `2026-06-02` — documented in `docs/daily-product-target-shortfall-2026-06-03.md`.
- `2026-05-31` — documented in `docs/daily-product-target-shortfall-2026-06-02.md`.
- `2026-05-30` — documented in `docs/daily-product-target-shortfall-2026-05-31.md`.

## Interpretation

1. The DB routing in this workspace is still correct: the report used `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`, not the harness control-plane DB.
2. The catalog appears to have crossed into the mid-`55M` active-product range, cutting the remaining target gap to roughly `44.6M` and reducing the forward required daily run rate to about `2.03M/day`.
3. The dominant reporting risk is still measurement cost and maglev instability, not obvious daily inactivity. Exact whole-table counts remain expensive, and `products_created_at_idx` is still invalid, so daily reports currently depend on a mix of exact freshness probes and conservative throughput proofs.

## Corrective Assignments In Place

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently gated recovery.

## Conclusion

`2026-06-08` does not support a new daily shortfall failure report. The canonical catalog DB is correctly pinned,
was still mutating at `2026-06-09 00:11 UTC`, and the closed-day hourly proof set already establishes at least
`12,900,511` inserted rows on `2026-06-08`. Using the current canonical table statistics, the catalog is now
approximately `55.4M` active products, leaving roughly `44.6M` active products to reach `100M` and an approximate
forward pace requirement of `2,028,429` active products per day for the remaining `22` calendar days through
`2026-06-30`.
