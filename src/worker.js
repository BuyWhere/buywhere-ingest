import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';
import { scrapeShopifyStore } from './shopifyScraper.js';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
const ingestApiKey = process.env.BUYWHERE_API_KEY;

if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

if (!ingestApiKey) {
  throw new Error('Missing BUYWHERE_API_KEY environment variable.');
}

const queueName = 'scrape.shopify';

const pgBoss = new PgBoss({
  connectionString: catalogDbUrl,
  schema: 'pgboss',
});

const db = new pg.Pool({
  connectionString: catalogDbUrl,
});

pgBoss.on('error', (err) => {
  console.error('[pg-boss] error', err);
});

await pgBoss.start();

async function createIngestionRun(source, payload) {
  try {
    const result = await db.query(
      `INSERT INTO ingestion_runs (source, status) VALUES ($1, 'running') RETURNING id`,
      [source]
    );
    return result.rows[0].id;
  } catch (err) {
    console.error('[worker] Failed to create ingestion run:', err);
    return null;
  }
}

async function updateIngestionRun(runId, status, rowsInserted, rowsUpdated, rowsFailed, errorMessage = null) {
  try {
    await db.query(
      `UPDATE ingestion_runs 
       SET status = $1, rows_inserted = $2, rows_updated = $3, rows_failed = $4, 
           error_message = $5, finished_at = NOW() 
       WHERE id = $6`,
      [status, rowsInserted, rowsUpdated, rowsFailed, errorMessage, runId]
    );
  } catch (err) {
    console.error('[worker] Failed to update ingestion run:', err);
  }
}

async function ingestProductsToCatalog(products, source) {
  const apiBaseUrl = process.env.BUYWHERE_API_URL || 'https://api.buywhere.ai';
  const response = await fetch(`${apiBaseUrl}/v1/ingest/products`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `ApiKey ${ingestApiKey}`,
    },
    body: JSON.stringify({
      source,
      products: products,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Ingest API returned ${response.status}: ${errorText}`);
  }

  return await response.json();
}

await pgBoss.work(queueName, {
  batchSize: 1,
  teamConcurrency: 1,
}, async (job) => {
  const id = job.id;
  const payload = job.data;
  const { merchantId, domain, source = 'shopify' } = payload;
  const createdAt = new Date().toISOString();

  console.log(`[worker] scrape.shopify job received at ${createdAt}`, {
    id,
    payload,
  });

  const runId = await createIngestionRun(source, payload);
  if (!runId) {
    console.error('[worker] Failed to create ingestion run, skipping job');
    return;
  }

  console.log(`[worker] Created ingestion run ${runId} for ${domain}`);

  try {
    console.log(`[worker] Starting Shopify scrape for ${domain}`);
    const products = await scrapeShopifyStore(domain);
    console.log(`[worker] Scraped ${products.length} products from ${domain}`);

    if (products.length === 0) {
      console.log(`[worker] No products found for ${domain}, marking as completed`);
      await updateIngestionRun(runId, 'completed', 0, 0, 0);
      return;
    }

    console.log(`[worker] Ingesting ${products.length} products to catalog`);
    const ingestResult = await ingestProductsToCatalog(products, source);
    console.log(`[worker] Ingest result:`, ingestResult);

    const rowsInserted = ingestResult.rows_inserted || 0;
    const rowsUpdated = ingestResult.rows_updated || 0;
    const rowsFailed = ingestResult.rows_failed || 0;
    const status = rowsFailed === 0 ? 'completed' : 'completed_with_errors';

    await updateIngestionRun(runId, status, rowsInserted, rowsUpdated, rowsFailed);
    console.log(`[worker] Job completed: ${status}`, { rowsInserted, rowsUpdated, rowsFailed });
  } catch (err) {
    const errorMessage = err.message || String(err);
    console.error(`[worker] Job failed:`, errorMessage);
    await updateIngestionRun(runId, 'failed', 0, 0, 0, errorMessage);
  }
});

console.log(`[worker] listening on queue ${queueName}`);