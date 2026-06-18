# Daily Product Target Shortfall Report

Date: 2026-06-06 UTC
Issue: BUY-31912
Owner: Oracle
Collected at: 2026-06-06 02:17:58 UTC

## Rule Applied

Required products per day =
`ceil((100,000,000 - current_active_products) / remaining_calendar_days_through_2026-06-30)`

For this report, `remaining_calendar_days_through_2026-06-30` is the inclusive window from
`2026-06-06` through `2026-06-30`, which is `25` calendar days.

## Source of Truth

- Canonical catalog Postgres via `data/.catalog_db_url`
- URL used: `postgresql://buywhere_ingest@maglev.proxy.rlwy.net:31310/railway?sslmode=require`
- Catalog target sanity (`scripts/catalog_target_report.py`): `active_database_host = maglev.proxy.rlwy.net:31310/railway`, `surfaces_diverge = true` (control-plane DB correctly NOT in use)
- Exact freshness check: `SELECT now() AT TIME ZONE 'utc', updated_at AT TIME ZONE 'utc' FROM public.products WHERE is_active = true ORDER BY updated_at DESC LIMIT 1;`
- Exact freshness result: query time `2026-06-06 02:17:58.304389 UTC`, latest active-row update `2026-06-06 02:08:06.246935 UTC`
- Live count note: exact full-table `COUNT(*)` scans on `public.products` were started against the canonical DB with `statement_timeout=0`, but they did not finish within this heartbeat budget. For today's live active/real totals, this artifact uses the current `pg_class.reltuples` values from the canonical DB as explicit approximations instead of publishing a guessed exact number.
- Approximate live count query used:

```sql
select relname, reltuples::bigint, relpages
from pg_class
where relname in ('products', 'idx_products_is_active', 'idx_products_active_true');
```

- Conservative closed-day proof basis:
  - [docs/buy-31038-hourly-throughput-check-2026-06-05T11.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-31038-hourly-throughput-check-2026-06-05T11.md) for `2026-06-05 00:00` through `11:00` UTC row inserts
  - [docs/buy-31732-hourly-throughput-check-2026-06-05T21.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/buy-31732-hourly-throughput-check-2026-06-05T21.md) for `2026-06-05 08:00` through `21:00` UTC row inserts
- Guard note: older workspace shortfall artifacts dated before the `2026-05-31` DB-target correction used the wrong control-plane DB and are not valid baselines for this report.

## Daily Result

- Approximate current active products (`idx_products_active_true.reltuples`): `31,124,416`
- Approximate current real products (`products.reltuples`): `31,181,580`
- Exact latest observable active-row update on the canonical DB: `2026-06-06 02:08:06.246935 UTC`
- Remaining active products to target: `68,875,584`
- Required products per day from `2026-06-06` forward: `2,755,024`
- Prior day's exact required pace from the `2026-06-05` shortfall report: `2,977,266`
- Conservative lower bound for closed-day `2026-06-05` row inserts, reconstructed from dated hourly DB-proof artifacts: `8,605,393`

Clarification:

- The live active/real totals above are approximate `reltuples` values, not exact `COUNT(*)` results. They are suitable for same-day pace monitoring but should be superseded by an exact scan once the database load allows it.
- Even with that approximation caveat on the live totals, the closed-day `2026-06-05` pace decision is still clear: the conservative lower bound of `8,605,393` created rows is far above the prior day's required pace of `2,977,266`.
- The canonical DB is actively mutating as of `2026-06-06 02:08 UTC`, so this is not another frozen-table day.

## Failure Days In The Reporting Window

The "failure report on any missed day" rule applies to closed UTC days where active-product growth fell below the required pace at the start of that day.

- `2026-06-05` UTC (closed day measured by this report): **NOT A MISS** on the evidence available in this heartbeat. The conservative lower-bound row creation proof (`8,605,393`) materially exceeds the prior required pace (`2,977,266`).
- No new failure report is filed for `2026-06-05`.

Prior misses already documented in this series (for context, not re-filed here):

- `2026-06-03` — documented in `docs/daily-product-target-shortfall-2026-06-04.md`.
- `2026-06-02` — documented in `docs/daily-product-target-shortfall-2026-06-03.md`.
- `2026-05-31` — documented in `docs/daily-product-target-shortfall-2026-06-02.md`.
- `2026-05-30` — documented in `docs/daily-product-target-shortfall-2026-05-31.md`.

## Interpretation

1. The canonical DB routing is correct in this workspace: the live target is `maglev.proxy.rlwy.net:31310/railway`, not the Paperclip control-plane DB.
2. The catalog is currently live again. An exact freshness check shows active-row updates continuing through `2026-06-06 02:08 UTC`.
3. The strongest same-day risk is measurement cost, not obvious ingest idleness: exact whole-table counts on `public.products` are now expensive enough that they can outlive a normal heartbeat. That is a tooling/reporting constraint, not direct evidence of a pace miss.

## Corrective Assignments In Place

- [BUY-22684](/BUY/issues/BUY-22684): Oracle's standing plan for discovery, ingestion, and source-of-truth recovery.
- [BUY-22739](/BUY/issues/BUY-22739): unblock `INGESTION_HOLD` so catalog growth can resume.
- [BUY-24283](/BUY/issues/BUY-24283): complete the post-repoint scrape and burn-in path that currently gated recovery.

## Conclusion

`2026-06-05` does not support a new shortfall failure report. The canonical DB is correctly pinned, is still mutating
on `2026-06-06`, and the conservative closed-day insert proof already clears the prior required pace by a wide margin.
Using the live canonical reltuple snapshot, the catalog is now approximately `31.1M` active products, leaving roughly
`68.9M` active products to reach `100M` and an approximate forward pace requirement of `2,755,024` active products per
day for the remaining `25` calendar days through `2026-06-30`.
