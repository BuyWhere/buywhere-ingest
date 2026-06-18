# Oracle Catalog Stats Reconciliation

Date: 2026-05-28 UTC
Issue: BUY-25133
Owner: Rex

## Canonical CEO scoreboard for 2026-05-28

Use the Postgres `products` table as the canonical source for CEO reporting until the public runtime surface is restored to exact parity.

Canonical definitions:

- Active products: `count(*) filter (where is_active)` from `products`
- Real products: `count(*)` from `products`
- Catalog-backed merchants: `count(distinct merchant_id)` from `products`

Latest confirmed exact values from dated artifacts:

| Metric | Exact value | Source artifact | Collected at |
| --- | ---: | --- | --- |
| Active products | `2,747,644` | `docs/daily-product-target-shortfall-2026-05-28.md` | `2026-05-28 00:15:16 UTC` |
| Real products | `2,762,711` | `docs/daily-product-target-shortfall-2026-05-28.md` | `2026-05-28 00:15:16 UTC` |
| Catalog-backed merchants | `15,070` | `docs/daily-ceo-report-input-2026-05-26-oracle.md` | `2026-05-26 ~23:20 UTC` |

Operational rule:

- `GET /v1/catalog/stats` is deprecated for CEO scoreboarding until it returns exact counts from the same definitions above.
- Future CEO reports should cite this document plus the dated exact query artifacts, not the public endpoint, unless the endpoint explicitly reports `approximate=false` and documents the same SQL-backed definitions.

## Public endpoint snapshot and why it diverges

Live check captured during this issue:

```json
{
  "data": {
    "total_products": 1575624,
    "total_merchants": 64812,
    "active_products": 1575624
  },
  "meta": {
    "approximate": true,
    "source": "pg_class_fallback",
    "ts": "2026-05-28T06:12:21.183Z"
  }
}
```

What that means:

- Product counts are approximate and come from `pg_class_fallback`, not from the exact `products` aggregate used by Oracle's dated shortfall report.
- The endpoint reports the same value for `active_products` and `total_products`, so it does not preserve the exact `is_active` distinction used by the canonical scoreboard.
- `total_merchants = 64,812` aligns with a broad merchant-registry style count, not the CEO report's catalog-backed merchant definition (`15,070` distinct merchant ids represented in `products`).

Conclusion:

- The public endpoint is not reporting the same metric family as the Oracle exact package.
- The endpoint can still be useful as a coarse runtime health signal, but it is not a defensible executive scoreboard while `approximate=true` and `source=pg_class_fallback`.

## Reconciling the known count packages

### Exact Oracle shortfall package on 2026-05-28

This package is fully reproducible from local artifacts and remains the canonical scoreboard:

- Active products: `2,747,644`
- Real products: `2,762,711`
- Query:

```sql
select
  now() at time zone 'utc' as collected_at_utc,
  count(*) filter (where is_active) as active_products,
  count(*) as real_products
from products;
```

### Prior package cited in the issue description: `2,797,824 / 2,812,997 / 64,812`

Oracle has now republished that package in [docs/oracle-count-package-2797824-2812997-64812-retired-2026-05-28.md](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/docs/oracle-count-package-2797824-2812997-64812-retired-2026-05-28.md).

Result of that republishing:

- The package definitions are exact:
  - active products = `count(*) filter (where is_active)` from `public.products`
  - real products = `count(*)` from `public.products`
  - merchants = `count(*)` from `public.merchants`
- The package is a mixed-source bundle, not the canonical CEO scoreboard.
- The merchant figure (`64,812`) is a merchant-registry row count, not the CEO report's catalog-backed merchant metric.
- The package is therefore retired from CEO reporting and kept only as a historical comparison artifact.

Deltas versus the current exact package remain material:

- `+50,180` active products
- `+50,286` total products

## Exact refresh commands for future CEO reports

Exact product scoreboard:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
select
  now() at time zone 'utc' as collected_at_utc,
  count(*) filter (where is_active) as active_products,
  count(*) as real_products
from products;
"
```

Exact catalog-backed merchant count:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "
select
  now() at time zone 'utc' as collected_at_utc,
  count(distinct merchant_id) as catalog_backed_merchants
from products;
"
```

Public endpoint comparison check:

```bash
curl -sS https://api.buywhere.ai/v1/catalog/stats
```

Report-writing rule:

1. Run the exact Postgres queries first.
2. Treat those results as canonical for the CEO table.
3. Run the public endpoint only as a drift check.
4. If the endpoint still returns `approximate=true` or non-matching definitions, call it out as degraded and do not use it as the main scoreboard.

## Required follow-up

- Runtime owner action: make `GET /v1/catalog/stats` either exact or visibly non-canonical.
- Oracle owner action completed in [BUY-25137](/BUY/issues/BUY-25137): the old package has been republished with exact SQL/source definitions and retired from CEO scoreboarding.

## BUY-25134 execution note

Date: 2026-05-28 UTC

- `BUY-25134` was executed in the Strategy workspace that contains only reporting artifacts and no runtime service code for `GET /v1/catalog/stats`.
- That means this workspace can document the canonical definitions and the drift, but it cannot satisfy the runtime acceptance criteria by itself.
- The existing runtime blocker is [BUY-22720](/BUY/issues/BUY-22720), which already tracks replacing `pg_class.reltuples`-based estimates with an exact catalog-stats source.
- Until `BUY-22720` lands or the runtime owner ships a separate warning/deprecation change on the live endpoint, `GET /v1/catalog/stats` must continue to be treated as non-canonical for CEO reporting.

## 2026-06-02 production verification

The old `pg_class_fallback` behavior is no longer live, but the endpoint still does not match the canonical CEO metric family.

Live check captured on `2026-06-02 19:27:13 UTC`:

```json
{
  "data": {
    "total_products": 16816466,
    "total_merchants": 68384,
    "active_products": 16816466
  },
  "meta": {
    "approximate": false,
    "source": "catalog_stats",
    "ts": "2026-06-02T19:27:13.830Z"
  }
}
```

Same-day canonical exact values already published in the dated CEO artifacts:

- `public.products` real products: `16,816,466`
- `public.products` active products: `16,795,557`
- `count(distinct public.products.merchant_id)`: `24,932`
- `public.merchants` registry rows: `68,384`

What this proves:

- `total_products` now matches the exact `public.products` total-row count.
- `total_merchants` still matches the broader `public.merchants` registry family, not the CEO report's catalog-backed merchant definition.
- `active_products` still collapses to `total_products`, so the endpoint does not preserve the exact `is_active` distinction required by the canonical scoreboard.

Current status:

- The estimator/fallback bug is fixed.
- The endpoint is still not CEO-canonical because its field semantics remain mixed.
- `GET /v1/catalog/stats` should therefore either:
  - align `active_products` and `total_merchants` to the exact `public.products` definitions, or
  - visibly label those fields as non-canonical/runtime-only so they cannot be mistaken for the executive source of truth.

## 2026-06-02 final runtime verification

The remaining field-semantic mismatch has now been fixed in [BUY-29160](/BUY/issues/BUY-29160).

Per the completed runtime deployment evidence recorded in that child issue:

- `https://buywhere-api-production.up.railway.app/v1/catalog/stats` at `2026-06-02T19:37:57.563Z` returned:

```json
{
  "data": {
    "total_products": 16816466,
    "total_merchants": 24932,
    "active_products": 16795557
  },
  "meta": {
    "approximate": false,
    "source": "public.products"
  }
}
```

- `https://api.buywhere.ai/v1/catalog/stats` at `2026-06-02T19:37:54.977Z` returned the same canonical values.

That closes the original CEO-reporting gap:

- `total_products` now matches exact `count(*)` from `public.products`
- `active_products` now matches exact `count(*) filter (where is_active)` from `public.products`
- `total_merchants` now matches exact `count(distinct merchant_id)` from `public.products`
- `meta.approximate=false` and `meta.source=public.products` make the runtime contract explicit

Result:

- `GET /v1/catalog/stats` is now aligned with the canonical CEO scoreboard definitions documented in this note.
