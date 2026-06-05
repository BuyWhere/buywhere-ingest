import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;

if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

const pgBoss = new PgBoss({
  connectionString: catalogDbUrl,
  schema: 'pgboss',
});

const db = new pg.Pool({
  connectionString: catalogDbUrl,
});

async function getActiveMerchants() {
  try {
    const result = await db.query(
      `SELECT id, domain, source 
       FROM merchants 
       WHERE is_active = true 
         AND platform = 'shopify'
       LIMIT 10`
    );
    return result.rows;
  } catch (err) {
    console.error('[producer] Error fetching merchants:', err);
    return [];
  }
}

async function enqueueShopifyJobs(merchants) {
  let enqueued = 0;
  for (const merchant of merchants) {
    try {
      const merchantSource = (merchant.source && merchant.source !== 'shopify')
        ? merchant.source
        : `shopify_${merchant.domain.replace(/[^a-z0-9]/gi, '').toLowerCase()}`;
      await pgBoss.send('scrape.shopify', {
        merchantId: merchant.id,
        domain: merchant.domain,
        source: merchantSource,
        enqueuedAt: new Date().toISOString(),
      });
      enqueued++;
      console.log(`[producer] Enqueued scrape job for ${merchant.domain}`);
    } catch (err) {
      console.error(`[producer] Failed to enqueue job for ${merchant.domain}:`, err);
    }
  }
  return enqueued;
}

async function main() {
  console.log('[producer] Starting Shopify scrape job producer...');
  
  await pgBoss.start();
  
  const merchants = await getActiveMerchants();
  console.log(`[producer] Found ${merchants.length} active Shopify merchants`);
  
  if (merchants.length === 0) {
    console.log('[producer] No active merchants found, exiting');
    await pgBoss.stop();
    return;
  }
  
  const enqueued = await enqueueShopifyJobs(merchants);
  console.log(`[producer] Enqueued ${enqueued} scrape jobs`);
  
  await pgBoss.stop();
  console.log('[producer] Producer completed');
}

main().catch(err => {
  console.error('[producer] Fatal error:', err);
  process.exit(1);
});