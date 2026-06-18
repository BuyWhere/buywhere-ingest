-- BUY-31223: Grant catalog_stats / catalog_stats_mv refresh rights to the data workspace
-- Target DB: maglev.proxy.rlwy.net:31310/railway (Railway Postgres 18.4)
-- Owner of the objects: postgres (the runtime / buywhere-api connection)
-- Run as: postgres (superuser / object owner) via the runtime's DATABASE_URL
--
-- Run context: this script must be executed by the OWNER of catalog_stats /
-- catalog_stats_mv, which is the `postgres` role on the catalog DB. The data
-- workspace's `buywhere_ingest` role lacks BYPASSRLS and is not a member of
-- postgres, so it cannot self-grant. Only the runtime's connection (which
-- connects as `postgres`) can apply these grants.
--
-- Pre-flight (run with buywhere_ingest to confirm the gap before the grant):
--   SELECT has_table_privilege('buywhere_ingest','public.catalog_stats','INSERT,UPDATE,DELETE');
--   -- expected: f
--   SELECT has_table_privilege('buywhere_ingest','public.catalog_stats_mv','MAINTAIN');
--   -- expected: f
--   REFRESH MATERIALIZED VIEW CONCURRENTLY public.catalog_stats_mv;
--   -- expected: ERROR: permission denied for materialized view catalog_stats_mv
--
-- Verification (run as buywhere_ingest AFTER the grant):
--   SELECT has_table_privilege('buywhere_ingest','public.catalog_stats','INSERT,UPDATE,DELETE');
--   -- expected: t
--   SELECT has_table_privilege('buywhere_ingest','public.catalog_stats_mv','MAINTAIN');
--   -- expected: t
--   REFRESH MATERIALIZED VIEW CONCURRENTLY public.catalog_stats_mv;
--   -- expected: REFRESH MATERIALIZED VIEW (no error)
--   SELECT count(*) FROM public.catalog_stats_mv;
--   -- expected: returns the count without error

BEGIN;

-- 1) Allow the data workspace to push fresh aggregate rows into the cache table.
--    catalog_stats is a small (~6.4k rows) aggregates cache. We grant the full
--    write set (INSERT/UPDATE/DELETE) so the data layer can rebuild it freely,
--    and we grant USAGE/SELECT on its sequence for the SERIAL id column.
GRANT INSERT, UPDATE, DELETE ON public.catalog_stats TO buywhere_ingest;
GRANT USAGE, SELECT ON SEQUENCE public.catalog_stats_id_seq TO buywhere_ingest;

-- 2) Allow the data workspace to REFRESH the materialized view.
--    On Postgres 14+ (we are on 18.4) the `MAINTAIN` privilege on a
--    materialized view is exactly the right for REFRESH MATERIALIZED VIEW
--    (and ANALYZE / VACUUM / REINDEX). It does not require ownership
--    transfer, so the runtime keeps full control of the object.
GRANT MAINTAIN ON public.catalog_stats_mv TO buywhere_ingest;

-- 3) Future-proofing: ingest_rw is the existing write role on the table
--    (already has arwdDxtm). Granting MAINTAIN on the MV lets it refresh
--    too, so the data workspace has a clean upgrade path if it ever
--    migrates from buywhere_ingest to ingest_rw.
GRANT MAINTAIN ON public.catalog_stats_mv TO ingest_rw;

COMMIT;
