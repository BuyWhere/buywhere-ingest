# BUY-27394 Runtime Surface Row-Family Ledger

Captured at `2026-05-30 06:03 UTC` from:
- live runtime endpoint: `GET https://api.buywhere.ai/v1/catalog/stats`
- production Railway Postgres via `DATABASE_URL`

## Executive result

The live runtime surface currently reports:

```json
{
  "data": {
    "total_products": 16815356,
    "total_merchants": 64812,
    "active_products": 16815356
  },
  "meta": {
    "approximate": true,
    "source": "pg_class_fallback",
    "ts": "2026-05-30T06:03:35.891Z"
  }
}
```

The exact canonical catalog at the same time is:

- `public.products`: `2,767,644` real rows
- `count(distinct public.products.merchant_id)`: `15,077` catalog-backed merchants

That leaves a visible product gap of:

`16,815,356 - 2,767,644 = 14,047,712`

## Row-family ledger

| Family | Exact count | Share of runtime surface | Classification | Action |
| --- | ---: | ---: | --- | --- |
| Canonical indexed catalog in `public.products` | `2,767,644` | `16.46%` | Canonical | Keep as source of truth |
| Archived product backup `public.products_buy22322_backup` | `689,537` | `4.10%` | Non-canonical backup family | Review for selective backfill or permanent retirement |
| Archived product backup `public.products_buy22322_phase2b_backup` | `1,516,396` | `9.02%` | Non-canonical backup family | Split into backfill candidates vs excluded/archive-only rows |
| Residual runtime-only estimate not backed by any visible exact product family | `11,841,779` | `70.42%` | Stale estimator / fallback contamination | Remove from runtime counter; cannot be treated as products |

The exact visible product-shaped families accessible from this runner sum to:

`2,767,644 + 689,537 + 1,516,396 = 4,973,577`

Inference:
- Because the runtime endpoint still reports `source = pg_class_fallback`
- and because all visible exact product-shaped tables total only `4,973,577`
- the remaining `11,841,779` cannot be defended as real visible product rows in this database snapshot
- the residual must therefore be treated as estimator contamination unless the runtime owner can produce another exact row family outside this workspace

## Family details

### 1. Canonical indexed catalog

`public.products` exact counts:

- total rows: `2,767,644`
- active rows: `2,752,385`
- inactive rows: `15,259`
- regions: `products_us = 163,167`, `products_sg = 2,604,477`
- distinct merchants: `15,077`
- distinct sources: `54`

This is the only family that should drive executive and exact runtime product counts today.

### 2. Archived backup family: `products_buy22322_backup`

Exact counts:

- total rows: `689,537`
- active rows: `579,537`
- inactive rows: `110,000`
- distinct merchants: `3,648`
- distinct sources: `28`
- region split: `sg = 401,780`, `us = 287,757`

Overlap signals:

- rows on merchants already present in `public.products`: `0`
- rows on merchants absent from `public.products`: `689,537`
- rows whose `source` already exists in `public.products`: `397,757`
- rows whose `source` does not exist in `public.products`: `291,780`
- overlapping sources with catalog: `2`
- novel sources versus catalog: `26`

Interpretation:
- this is not a duplicate copy of the current indexed merchant set
- it contains a mixed family of old/archive rows from mostly non-canonical merchant/source paths
- it should not be counted live

Recommended action:
- evaluate it as a backlog/retirement family
- backfill only rows that pass current ingestion/indexing policy
- otherwise keep it excluded from runtime and executive totals

### 3. Archived backup family: `products_buy22322_phase2b_backup`

Exact counts:

- total rows: `1,516,396`
- active rows: `1,516,394`
- inactive rows: `2`
- distinct merchants: `5,874`
- distinct sources: `1,383`
- region split: `us = 1,231,610`, `sg = 134,507`, `SG = 75,488`, `US = 74,637`, `global = 150`, `th = 4`

Overlap signals:

- rows on merchants already present in `public.products`: `572,293`
- rows on merchants absent from `public.products`: `944,103`
- rows whose `source` already exists in `public.products`: `0`
- rows whose `source` does not exist in `public.products`: `1,516,396`
- overlapping sources with catalog: `0`
- novel sources versus catalog: `1,383`

Interpretation:
- this family is largely outside the current indexed source set
- part of it touches already-indexed merchants, so it likely contains duplicate/alternative-source inventory for merchants already in the catalog
- the rest looks like unindexed backlog from novel sources

Recommended action:
- split this table into two operational decisions:
- rows on indexed merchants: inspect for duplication, alternative-source contamination, or replacement precedence
- rows on non-indexed merchants and novel sources: treat as explicit backfill candidates if they meet current product-quality policy

### 4. Merchant-family mismatch

The runtime surface reports `total_merchants = 64,812`, while the exact indexed catalog has `15,077` merchants.

Visible exact merchant families:

- `public.merchants`: `64,858`
- `count(distinct public.products.merchant_id)`: `15,077`
- delta between runtime merchant scale and catalog-backed merchant scale: `49,735`

Interpretation:
- the runtime endpoint is already mixing merchant-registry scale with catalog-product scale
- that supports the conclusion that the fallback path is not using one canonical catalog definition

## Reproducible SQL

Canonical runtime-vs-catalog check:

```sql
select count(*)::bigint as total_products,
       count(*) filter (where is_active)::bigint as active_products,
       count(distinct merchant_id)::bigint as catalog_backed_merchants
from public.products;
```

Region split of canonical catalog:

```sql
select 'products_us' as table_name, count(*)::bigint from public.products_us
union all
select 'products_sg', count(*)::bigint from public.products_sg;
```

Backup family counts:

```sql
select 'products_buy22322_backup' as table_name,
       count(*)::bigint as total_rows,
       count(*) filter (where is_active)::bigint as active_rows,
       count(*) filter (where not is_active)::bigint as inactive_rows,
       count(distinct merchant_id)::bigint as merchants,
       count(distinct source)::bigint as sources
from public.products_buy22322_backup
union all
select 'products_buy22322_phase2b_backup',
       count(*)::bigint,
       count(*) filter (where is_active)::bigint,
       count(*) filter (where not is_active)::bigint,
       count(distinct merchant_id)::bigint,
       count(distinct source)::bigint
from public.products_buy22322_phase2b_backup;
```

Backup family overlap against the canonical catalog:

```sql
with p_merchants as (
  select distinct merchant_id from public.products
),
p_sources as (
  select distinct source from public.products
)
select 'backup1_rows_with_catalog_merchant' as metric, count(*)::bigint as rows
from public.products_buy22322_backup b
where exists (select 1 from p_merchants p where p.merchant_id = b.merchant_id)
union all
select 'backup1_rows_without_catalog_merchant', count(*)::bigint
from public.products_buy22322_backup b
where not exists (select 1 from p_merchants p where p.merchant_id = b.merchant_id)
union all
select 'backup1_rows_with_catalog_source', count(*)::bigint
from public.products_buy22322_backup b
where exists (select 1 from p_sources p where p.source = b.source)
union all
select 'backup1_rows_without_catalog_source', count(*)::bigint
from public.products_buy22322_backup b
where not exists (select 1 from p_sources p where p.source = b.source)
union all
select 'backup2_rows_with_catalog_merchant', count(*)::bigint
from public.products_buy22322_phase2b_backup b
where exists (select 1 from p_merchants p where p.merchant_id = b.merchant_id)
union all
select 'backup2_rows_without_catalog_merchant', count(*)::bigint
from public.products_buy22322_phase2b_backup b
where not exists (select 1 from p_merchants p where p.merchant_id = b.merchant_id)
union all
select 'backup2_rows_with_catalog_source', count(*)::bigint
from public.products_buy22322_phase2b_backup b
where exists (select 1 from p_sources p where p.source = b.source)
union all
select 'backup2_rows_without_catalog_source', count(*)::bigint
from public.products_buy22322_phase2b_backup b
where not exists (select 1 from p_sources p where p.source = b.source);
```

Merchant-family mismatch:

```sql
select count(*)::bigint as runtime_scale_merchants from public.merchants;

select count(distinct merchant_id)::bigint as catalog_backed_merchants
from public.products;
```

## Decision

What should be backfilled into `public.products`:

- qualifying rows from `products_buy22322_phase2b_backup` that are on non-indexed merchants and novel sources, after applying current ingestion and quality rules
- any rows from `products_buy22322_backup` that pass the same policy and are still desired product inventory

What should remain excluded:

- all runtime-only `pg_class_fallback` residual above the exact visible families
- any backup rows that are duplicate, superseded, retired, or fail current quality/indexing rules
- merchant-registry rows that do not correspond to indexed products

What this issue proves:

- the public runtime number is not a harmless rounding variant of `public.products`
- at least `11,841,779` of the reported `16,815,356` product surface is unsupported by any exact visible product-row family in the production database snapshot used here
- therefore the current runtime surface must remain explicitly non-canonical until the fallback path is retired
