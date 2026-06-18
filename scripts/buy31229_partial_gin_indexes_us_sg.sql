-- BUY-31229: Partial GIN indexes for US/SG search to reduce bitmap scan time
-- Target: Railway maglev proxy catalog DB
-- IMPORTANT: Requires postgres superuser or CREATE privilege on products table
-- Run with: psql "<admin_url>" -f scripts/buy31229_partial_gin_indexes_us_sg.sql
--
-- Context:
-- - Existing idx_products_search_country (2370MB) on (search_vector, country_code)
--   scans entire index for any query regardless of country filter
-- - Partial GIN indexes reduce index size dramatically for country-specific queries
-- - Use CONCURRENTLY to avoid table locks during index build

-- Enable trigram extension (if not already enabled)
-- Note: Required for gin_trgm_ops on text columns; not needed for tsvector GIN
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================================================
-- US Region Partial GIN Index
-- Active US products only (~7.5M rows estimate)
-- =============================================================================
CREATE INDEX CONCURRENTLY idx_products_search_us_active
    ON public.products USING gin (search_vector)
    WHERE country_code = 'US' AND is_active = true;

-- =============================================================================
-- SG Region Partial GIN Index
-- Active SG products only
-- =============================================================================
CREATE INDEX CONCURRENTLY idx_products_search_sg_active
    ON public.products USING gin (search_vector)
    WHERE country_code = 'SG' AND is_active = true;

-- =============================================================================
-- Verification (run after index creation)
-- =============================================================================
-- Check index existence:
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'products' AND indexname LIKE '%_active';

-- Check index sizes (after populated):
-- SELECT pg_size_pretty(pg_relation_size('idx_products_search_us_active'));
-- SELECT pg_size_pretty(pg_relation_size('idx_products_search_sg_active'));

-- Force stats refresh for query planner:
-- ANALYZE public.products;

-- =============================================================================
-- Example queries that will use these indexes
-- =============================================================================
-- SELECT * FROM public.products WHERE country_code = 'US' AND is_active = true AND search_vector @@ to_tsquery('english', 'laptop') LIMIT 100;
-- SELECT * FROM public.products WHERE country_code = 'SG' AND is_active = true AND search_vector @@ to_tsquery('english', 'wireless') LIMIT 100;
