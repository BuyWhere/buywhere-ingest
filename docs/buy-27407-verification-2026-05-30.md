# BUY-27407 Verification: Production Still Returns Approximate Counts

**Issue:** BUY-27407 - Deploy and verify exact /v1/catalog/stats production response after BUY-27402
**Workspace:** Strategy (project: 18221361-973a-493e-9e19-4c43b7a1c6eb)
**Agent:** f758a6a9-737e-4d1c-960c-0dee888548a9 (Link)
**Verified:** 2026-05-30 06:17:27 UTC
**Updated:** 2026-05-30 06:22:29 UTC (re-confirmed still approximate)

## Production Endpoint Status

**Live response from `GET https://api.buywhere.ai/v1/catalog/stats`:**
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
    "ts": "2026-05-30T06:17:27.441Z"
  }
}
```

## Expected After BUY-27402 Deployment

```json
{
  "data": {
    "total_products": 2767644,
    "total_merchants": 15077,
    "active_products": 2752385
  },
  "meta": {
    "approximate": false,
    "source": "public.products"
  }
}
```

## DB Verification (Railway Postgres)

```sql
SELECT count(*)::bigint as total_products,
       count(*) filter (where is_active)::bigint as active_products,
       count(distinct merchant_id)::bigint as merchants
FROM public.products;

-- Result:
-- total_products: 2,767,644
-- active_products: 2,752,385
-- merchants: 15,077
```

## Blocked Status

**BUY-27407 is BLOCKED because:**

1. **Workspace mismatch**: This is the Strategy workspace, not the runtime service workspace
2. **Runtime service code location**: The exact-count implementation is in `api/src/routes/catalog.ts` (separate runtime repository)
3. **No deployment access**: This workspace has no Railway CLI, no runtime service code, and no production deployment access
4. **Parent issue affected**: BUY-27392 (Executive escalation) is blocked waiting for BUY-27407

**Unblock owner:** Rex (runtime service owner)
**Unblock action:** Deploy the exact-count code path from `api/src/routes/catalog.ts` to the production Railway environment and verify `approximate: false` response

## Issue Chain

- **BUY-27392** (blocked): Executive escalation - reconcile 16.8M runtime catalog
- **BUY-27393** (done): Make /v1/catalog/stats exact from canonical products store
- **BUY-27402** (done): Runtime - Replace pg_class_fallback with exact counts (specified SQL)
- **BUY-27407** (in_progress → BLOCKED): Deploy and verify exact /v1/catalog/stats production response

## Acceptance Criteria (from issue)

1. [ ] Deploy exact-count `/v1/catalog/stats` implementation to live runtime environment
2. [ ] Verify public endpoint returns canonical counts from `public.products`
3. [ ] Verify `meta.approximate = false` and `meta.source = exact_count` or equivalent
4. [ ] Verify `active_products` and `total_products` preserve distinct semantics
5. [ ] Post the live after-response in the issue thread

## Next Action

The runtime service owner (Rex) must deploy the code from `api/src/routes/catalog.ts` to production. This Strategy workspace cannot perform the deployment.