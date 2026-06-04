// Optional local script for quick manual smoke testing.
// This publishes one scrape.shopify job to the queue.

import dotenv from 'dotenv';
import PgBoss from 'pg-boss';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

const pgBoss = new PgBoss({
  connectionString: catalogDbUrl,
  schema: 'pgboss',
});

await pgBoss.start();

const demoDomain = process.env.SHOPIFY_DOMAIN || 'store.anycubic.com';
await pgBoss.send('scrape.shopify', {
  merchantId: 'demo-merchant',
  domain: demoDomain,
  source: 'manual-smoke',
  at: new Date().toISOString(),
});

console.log(`Published scrape.shopify job for ${demoDomain}.`);
await pgBoss.stop();
