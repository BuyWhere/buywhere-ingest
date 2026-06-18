/* BUY-52086 category normalization verification
 * Run against Railway PostgreSQL catalog.
 * NOTE: products_created_at_idx is INVALID — queries on 95M-row products table
 * will time out without index. Use TABLESAMPLE or wait for Ops REINDEX.
 *
 * Until REINDEX lands, run with: SET statement_timeout = '30s';
 */

/* --- Baseline (pre-fix) category distribution sample --- */
-- TABLESAMPLE is the only viable path with INVALID idx
-- Run at 0.001% to stay within 30s timeout on 236GB table

SET statement_timeout = '30s';

-- Top-30 categories by frequency (sample)
SELECT
    category,
    COUNT(*) AS sample_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_sample
FROM products TABLESAMPLE BERNOULLI(0.001) REPEATABLE(42)
WHERE is_active = true
GROUP BY category
ORDER BY sample_count DESC
LIMIT 30;

/* Expected noise buckets to shrink or disappear:
 *   "Bundle Builder"
 *   "Interest Check"
 *   "In Stock"
 *   "End"
 *   "Add-ons"
 *   "In Production"
 *   "60% assembled keyboard" / "* DIY KIT"
 *   "Greeting Card"
 */

/* --- Blank-category check --- */
-- NOTE: Without a valid index, COUNT(*) WHERE category IS NULL will timeout.
-- The n_tup_ins delta (BUY-33694 dispatcher) is the only viable live signal.
-- Expected: reltuples via pg_class, not a filtered COUNT.

SELECT
    relname,
    reltuples::bigint AS estimated_active_products,
    (SELECT COUNT(*) FROM pg_stat_user_tables WHERE relname = 'products') AS stat_read_ok
FROM pg_class
WHERE relname = 'products';

/* --- Per-source category quality (sample) --- */
SELECT
    source,
    COUNT(*) AS sample_count,
    COUNT(*) FILTER (WHERE category IS NULL OR category = '') AS blank_sample,
    ROUND(COUNT(*) FILTER (WHERE category IS NULL OR category = '') * 100.0 / NULLIF(COUNT(*) FILTER (WHERE category IS NOT NULL AND category <> ''), 0), 1) AS blank_pct
FROM products TABLESAMPLE BERNOULLI(0.001) REPEATABLE(42)
WHERE is_active = true
GROUP BY source
HAVING COUNT(*) > 10
ORDER BY sample_count DESC
LIMIT 20;

/* --- Expected post-fix behavior --- */
-- 1. Re-ingested Shopify/WooCommerce rows with noisy product_type will have
--    category = NULL (dropped) and category_path = NULL or real sub-category
-- 2. New ingest of fentybeauty/kbdfans/nzxt/maidenhome from retailer-direct/
--    will classify correctly:
--    fentybeauty: "Foundations & Concealers" not "Bundle Builder"
--    kbdfans: "Keycaps" not "Interest Check" or "In Stock"
--    nzxt: "Cases"/"Fans"/"Coolers" not "In Stock"
--    maidenhome: "Ottoman"/"Chair"/"Sofa" preserved (already clean)
-- 3. Ettitude's full-delimiter path "Home & Garden > Linens & Bedding > ..."
--    will split into clean segments, not be treated as a single noisy string
