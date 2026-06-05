/**
 * Deletes unscoped source='shopify' rows after per-domain re-scrape is complete.
 * Only deletes rows where a matching shopify_<domain> row now exists (safe removal).
 * Unmatched rows are reported but not deleted.
 *
 * Run: node scripts/cleanup-unscoped-shopify.js [--dry-run]
 */
import dotenv from 'dotenv';
import pg from 'pg';

dotenv.config();

const isDryRun = process.argv.includes('--dry-run');
const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
if (!catalogDbUrl) throw new Error('Missing CATALOG_DB_URL or DATABASE_URL');

const db = new pg.Pool({ connectionString: catalogDbUrl });

async function main() {
  console.log(`[cleanup] Starting${isDryRun ? ' (DRY RUN)' : ''}...`);

  // Count total unscoped rows
  const totalResult = await db.query(
    `SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE image_url IS NULL) as null_images
     FROM products WHERE source = 'shopify' AND country_code = 'US'`
  );
  const { total, null_images } = totalResult.rows[0];
  console.log(`[cleanup] Unscoped shopify rows: ${total} total, ${null_images} with null image_url`);

  // Find domains that now have per-domain rows
  const coveredResult = await db.query(`
    SELECT DISTINCT regexp_replace(p.url, '^https?://([^/]+).*', '\\1') as domain
    FROM products p
    WHERE p.source = 'shopify' AND p.country_code = 'US'
      AND EXISTS (
        SELECT 1 FROM products p2
        WHERE p2.source LIKE 'shopify_%'
          AND p2.url LIKE (regexp_replace(p.url, '^https?://([^/]+).*', 'https://\\1') || '%')
          AND p2.image_url IS NOT NULL
      )
  `);
  const coveredDomains = coveredResult.rows.map(r => r.domain);
  console.log(`[cleanup] Domains with successful per-domain re-scrape: ${coveredDomains.length}`);

  if (coveredDomains.length === 0) {
    console.log('[cleanup] No domains have per-domain rows yet — run enqueue-shopify-rescrape.js first');
    await db.end();
    return;
  }

  // Build domain pattern conditions
  const conditions = coveredDomains.map(d => `url LIKE 'https://${d}/%' OR url LIKE 'http://${d}/%'`).join(' OR ');

  const countResult = await db.query(
    `SELECT COUNT(*) as rows_to_delete FROM products WHERE source = 'shopify' AND country_code = 'US' AND (${conditions})`
  );
  console.log(`[cleanup] Rows safe to delete: ${countResult.rows[0].rows_to_delete}`);

  if (!isDryRun) {
    const deleteResult = await db.query(
      `DELETE FROM products WHERE source = 'shopify' AND country_code = 'US' AND (${conditions})`
    );
    console.log(`[cleanup] Deleted ${deleteResult.rowCount} rows`);
  } else {
    console.log(`[cleanup] DRY RUN — would delete ${countResult.rows[0].rows_to_delete} rows`);
  }

  // Final count
  const finalResult = await db.query(
    `SELECT COUNT(*) as remaining FROM products WHERE source = 'shopify' AND country_code = 'US'`
  );
  console.log(`[cleanup] Remaining unscoped shopify rows: ${finalResult.rows[0].remaining}`);

  await db.end();
}

main().catch((err) => {
  console.error('[cleanup] Fatal error:', err);
  process.exit(1);
});
