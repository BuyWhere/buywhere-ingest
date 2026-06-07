import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';
import http from 'http';
import { scrapeShopifyStore } from './shopifyScraper.js';
import { getIngestionStats, getRecentJobs, getQueueStats } from './health.js';

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
}, async (jobs) => {
  // pg-boss v10 passes an array of jobs even with batchSize: 1
  const job = Array.isArray(jobs) ? jobs[0] : jobs;
  const id = job.id;
  const payload = job.data;
  const { merchantId, domain } = payload;
  const source = (payload.source && payload.source !== 'shopify')
    ? payload.source
    : `shopify_${domain.replace(/[^a-z0-9]/gi, '').toLowerCase()}`;
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

// Tiny /healthz HTTP server so Railway can healthcheck the long-running
// worker.  Returns the same shape as src/server.js's /health so the
// BUY-33060 acceptance gate's "recentJobs visible at /healthz" item works.
const healthPort = parseInt(process.env.PORT || '3000', 10);
const healthServer = http.createServer(async (req, res) => {
  if (req.url !== '/health' && req.url !== '/healthz') {
    res.statusCode = 404;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'not found' }));
    return;
  }
  try {
    const [stats, recentJobs, queueStats] = await Promise.all([
      getIngestionStats(),
      getRecentJobs(),
      getQueueStats(),
    ]);
    let status = 'healthy';
    if (!stats) status = 'degraded';
    else if (stats.failed_runs > 0 && stats.completed_runs === 0) status = 'unhealthy';
    else if (stats.running_runs > 5) status = 'busy';

    res.statusCode = status === 'healthy' ? 200 : 503;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({
      status,
      timestamp: new Date().toISOString(),
      service: 'buywhere-ingest-worker',
      stats: stats || {},
      queue: queueStats || {},
      recent_jobs: recentJobs,
    }, null, 2));
  } catch (err) {
    res.statusCode = 503;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: err.message,
    }));
  }
});
healthServer.listen(healthPort, () => {
  console.log(`[worker] healthz server listening on port ${healthPort}`);
});