/**
 * Enqueues re-scrape jobs for all domains with unscoped source='shopify' rows
 * that have null image_url. Uses per-domain shopify_<domain> source labels.
 *
 * Run: node scripts/enqueue-shopify-rescrape.js [--dry-run] [--limit N]
 */
import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';

dotenv.config();

const isDryRun = process.argv.includes('--dry-run');
const limitArg = process.argv.indexOf('--limit');
const limit = limitArg !== -1 ? parseInt(process.argv[limitArg + 1], 10) : null;

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
if (!catalogDbUrl) throw new Error('Missing CATALOG_DB_URL or DATABASE_URL');

const db = new pg.Pool({ connectionString: catalogDbUrl });
const pgBoss = new PgBoss({ connectionString: catalogDbUrl, schema: 'pgboss' });

pgBoss.on('error', (err) => console.error('[pg-boss] error', err));

function normalizeDomain(domain) {
  return domain.replace(/[^a-z0-9]/gi, '').toLowerCase();
}

async function main() {
  console.log(`[rescrape] Starting${isDryRun ? ' (DRY RUN)' : ''}...`);

  const query = `
    SELECT
      regexp_replace(url, '^https?://([^/]+).*', '\\1') as domain,
      COUNT(*) as total,
      COUNT(*) FILTER (WHERE image_url IS NULL) as null_images
    FROM products
    WHERE source = 'shopify' AND country_code = 'US' AND image_url IS NULL
    GROUP BY 1
    ORDER BY COUNT(*) DESC
    ${limit ? `LIMIT ${limit}` : ''}
  `;

  const result = await db.query(query);
  const domains = result.rows;

  console.log(`[rescrape] Found ${domains.length} domains with null-image shopify rows`);

  if (!isDryRun) {
    await pgBoss.start();
  }

  let enqueued = 0;
  let skipped = 0;

  for (const row of domains) {
    const { domain, total, null_images } = row;
    const normalizedSource = `shopify_${normalizeDomain(domain)}`;

    if (isDryRun) {
      console.log(`[dry-run] Would enqueue: domain=${domain} source=${normalizedSource} null_images=${null_images}/${total}`);
      enqueued++;
      continue;
    }

    try {
      await pgBoss.send('scrape.shopify', {
        domain,
        source: normalizedSource,
        enqueuedAt: new Date().toISOString(),
        rescrapeReason: 'BUY-30510_unscoped_shopify_deprecation',
      });
      enqueued++;
      console.log(`[rescrape] Enqueued ${domain} as ${normalizedSource} (${null_images} null-image rows)`);
    } catch (err) {
      console.error(`[rescrape] Failed to enqueue ${domain}:`, err.message);
      skipped++;
    }
  }

  console.log(`[rescrape] Done. Enqueued: ${enqueued}, Skipped: ${skipped}`);

  if (!isDryRun) {
    await pgBoss.stop();
  }
  await db.end();
}

main().catch((err) => {
  console.error('[rescrape] Fatal error:', err);
  process.exit(1);
});
