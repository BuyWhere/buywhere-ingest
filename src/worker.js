import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';
import http from 'http';
import { scrapeShopifyStore, scrapeShopifyStorePages } from './shopifyScraper.js';
import { scrapeWooCommerceStore } from './woocommerceScraper.js';
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

// BUY-33060 / BUY-34833: two queues, same shape.
// - scrape.shopify:       page 1 (XML sitemap → first ~250 products), as before.
// - scrape.shopify.deep:  pages 7-80 via Shopify /products.json?page=N&limit=250.
//   Enqueued by the page-1 handler after completion (success OR 0-results),
//   so a single cron tick fans out to one deep job per scraped domain.
const PAGE1_QUEUE = 'scrape.shopify';
const DEEP_QUEUE = 'scrape.shopify.deep';
const DEEP_START_PAGE = parseInt(process.env.DEEP_START_PAGE || '7', 10);
const DEEP_END_PAGE = parseInt(process.env.DEEP_END_PAGE || '80', 10);
const DEEP_LIMIT = parseInt(process.env.DEEP_LIMIT || '250', 10);
const DEEP_SINGLETON_HOURS = parseInt(process.env.DEEP_SINGLETON_HOURS || '23', 10);

// BUY-34834: WooCommerce deep-page queue. The WC Store API
// (https://<domain>/wp-json/wc/store/products?per_page=100&page=N) returns the
// whole catalog in one shape, so we don't split into page-1 + deep — a single
// job per merchant does the whole deep-page. Producer (npm run producer:wc)
// finds merchants with source='woocommerce' and onboarding_stage in
// ('discovered','interested') and enqueues one job per merchant.
const WC_DEEP_QUEUE = 'scrape.woocommerce.deep';
const WC_DEEP_START_PAGE = parseInt(process.env.WC_DEEP_START_PAGE || '1', 10);
const WC_DEEP_END_PAGE = parseInt(process.env.WC_DEEP_END_PAGE || '80', 10);
const WC_DEEP_PER_PAGE = parseInt(process.env.WC_DEEP_PER_PAGE || '100', 10);
const WC_DEEP_PAGE_TIMEOUT_MS = parseInt(process.env.WC_DEEP_PAGE_TIMEOUT_MS || '8000', 10);
const WC_DEEP_PAGE_CONCURRENCY = parseInt(process.env.WC_DEEP_PAGE_CONCURRENCY || '8', 10);
const WC_DEEP_SINGLETON_HOURS = parseInt(process.env.WC_DEEP_SINGLETON_HOURS || '23', 10);

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

function deriveSource(domain, payload) {
  return (payload && payload.source && payload.source !== 'shopify')
    ? payload.source
    : `shopify_${domain.replace(/[^a-z0-9]/gi, '').toLowerCase()}`;
}

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
      products,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Ingest API returned ${response.status}: ${errorText}`);
  }

  return await response.json();
}

// BUY-34833: page-1 worker enqueues a follow-up deep job after completion
// (success OR 0-results). Singleton dedupe is per-domain for DEEP_SINGLETON_HOURS
// so the same domain doesn't get re-deep-paged within a cycle.
async function enqueueDeepJob(payload, jobId) {
  const { domain, source } = payload;
  if (!domain || typeof domain !== 'string' || !domain.includes('.')) {
    console.warn(`[worker] skip deep enqueue: invalid domain=${domain}`);
    return;
  }
  try {
    const deepJobId = await pgBoss.send(DEEP_QUEUE, {
      ...payload,
      deep: true,
      enqueuedAt: new Date().toISOString(),
      fanoutFromJobId: jobId,
    }, {
      singletonKey: domain,
      singletonHours: DEEP_SINGLETON_HOURS,
      retryLimit: 1,
      expireInHours: DEEP_SINGLETON_HOURS + 1,
    });
    console.log(`[worker] enqueued ${DEEP_QUEUE} job ${deepJobId || '<accepted>'} for ${domain} (fanout from ${PAGE1_QUEUE} job ${jobId})`);
  } catch (err) {
    // Singleton dedupe rejects re-enqueues that are within the singleton window.
    // That's the expected case for repeated page-1 completions within DEEP_SINGLETON_HOURS.
    const msg = String(err && err.message || err);
    if (/singleton/i.test(msg) || /already.*active/i.test(msg)) {
      console.log(`[worker] deep enqueue for ${domain} skipped (singleton dedupe within ${DEEP_SINGLETON_HOURS}h)`);
    } else {
      console.error(`[worker] failed to enqueue deep job for ${domain}:`, msg);
    }
  }
}

// ---------------------------------------------------------------------------
// Page-1 worker (existing behavior + BUY-34833 deep fan-out)
// ---------------------------------------------------------------------------
await pgBoss.work(PAGE1_QUEUE, {
  batchSize: 1,
  teamConcurrency: 1,
}, async (jobs) => {
  // pg-boss v10 passes an array of jobs even with batchSize: 1
  const job = Array.isArray(jobs) ? jobs[0] : jobs;
  const id = job.id;
  const payload = job.data;
  const { domain } = payload;
  const source = deriveSource(domain, payload);
  const createdAt = new Date().toISOString();

  console.log(`[worker] ${PAGE1_QUEUE} job received at ${createdAt}`, { id, payload });

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
      console.log(`[worker] No products found for ${domain}, marking as completed (and still fanning out to deep)`);
      await updateIngestionRun(runId, 'completed', 0, 0, 0);
      await enqueueDeepJob({ ...payload, source }, id);
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
  } finally {
    // BUY-34833: fan out to deep queue regardless of page-1 status. The deep
    // worker is independent of the page-1 result — the live deep loop also
    // re-pages domains with truncated page-1, so this is consistent.
    await enqueueDeepJob({ ...payload, source }, id);
  }
});

console.log(`[worker] listening on queue ${PAGE1_QUEUE}`);

// ---------------------------------------------------------------------------
// Deep worker (BUY-34833) — pages 7-80 via /products.json?page=N&limit=250
// ---------------------------------------------------------------------------
await pgBoss.work(DEEP_QUEUE, {
  batchSize: 1,
  teamConcurrency: 1,
}, async (jobs) => {
  const job = Array.isArray(jobs) ? jobs[0] : jobs;
  const id = job.id;
  const payload = job.data;
  const { domain } = payload;
  const source = deriveSource(domain, payload);
  const createdAt = new Date().toISOString();

  console.log(`[worker] ${DEEP_QUEUE} job received at ${createdAt}`, { id, payload });

  const runId = await createIngestionRun(source, {
    ...payload,
    queue: DEEP_QUEUE,
    deep: true,
  });
  if (!runId) {
    console.error(`[worker] Failed to create ingestion run for ${DEEP_QUEUE} job, skipping`);
    return;
  }

  try {
    console.log(`[worker] Starting deep-page scrape for ${domain} (pages ${DEEP_START_PAGE}-${DEEP_END_PAGE})`);
    const products = await scrapeShopifyStorePages(domain, DEEP_START_PAGE, DEEP_END_PAGE, DEEP_LIMIT);
    console.log(`[worker] Deep-scraped ${products.length} products from ${domain}`);

    if (products.length === 0) {
      console.log(`[worker] No deep products for ${domain} (catalog shorter than page ${DEEP_START_PAGE})`);
      await updateIngestionRun(runId, 'completed', 0, 0, 0);
      return;
    }

    console.log(`[worker] Ingesting ${products.length} deep products to catalog`);
    const ingestResult = await ingestProductsToCatalog(products, source);
    console.log(`[worker] Deep ingest result:`, ingestResult);

    const rowsInserted = ingestResult.rows_inserted || 0;
    const rowsUpdated = ingestResult.rows_updated || 0;
    const rowsFailed = ingestResult.rows_failed || 0;
    const status = rowsFailed === 0 ? 'completed' : 'completed_with_errors';

    await updateIngestionRun(runId, status, rowsInserted, rowsUpdated, rowsFailed);
    console.log(`[worker] ${DEEP_QUEUE} job completed: ${status}`, { rowsInserted, rowsUpdated, rowsFailed });
  } catch (err) {
    const errorMessage = err.message || String(err);
    console.error(`[worker] ${DEEP_QUEUE} job failed:`, errorMessage);
    await updateIngestionRun(runId, 'failed', 0, 0, 0, errorMessage);
  }
});

console.log(`[worker] listening on queue ${DEEP_QUEUE}`);

// ---------------------------------------------------------------------------
// WooCommerce deep worker (BUY-34834) — pages 1..80 via
// /wp-json/wc/store/products?per_page=100&page=N. Source uses
// `woocommerce_<domain>` so the per-domain SKU namespace is distinct from
// the legacy `woocommerce` source (81k rows on the existing data).
// ---------------------------------------------------------------------------
// The /v1/ingest/products endpoint caps at 1000 products per request
// (see api/src/routes/ingest.ts:205). A full 80-page WC deep can produce
// up to 8000 products, so we chunk.
const INGEST_BATCH_LIMIT = 1000;

function chunkArray(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

function deriveWcSource(domain, payload) {
  if (payload && typeof payload.source === 'string' && payload.source.startsWith('woocommerce')) {
    return payload.source;
  }
  return `woocommerce_${domain.replace(/[^a-z0-9]/gi, '').toLowerCase()}`;
}

async function markMerchantIngested(merchantId) {
  if (!merchantId || typeof merchantId !== 'string') return;
  try {
    await db.query(
      `UPDATE merchants
          SET onboarding_stage = 'ingested',
              last_scraped_at = NOW(),
              updated_at = NOW()
        WHERE id = $1
          AND onboarding_stage IN ('discovered', 'interested')`,
      [merchantId]
    );
  } catch (err) {
    console.warn(`[worker] could not mark merchant ${merchantId} as ingested: ${err.message}`);
  }
}

await pgBoss.work(WC_DEEP_QUEUE, {
  batchSize: 1,
  teamConcurrency: 1,
}, async (jobs) => {
  const job = Array.isArray(jobs) ? jobs[0] : jobs;
  const id = job.id;
  const payload = job.data || {};
  const domain = payload.domain;
  const merchantId = payload.merchant_id || payload.merchantId || domain;
  const pageStart = parseInt(payload.page_start || WC_DEEP_START_PAGE, 10) || 1;
  const pageEnd = parseInt(payload.page_end || WC_DEEP_END_PAGE, 10) || 80;
  const source = deriveWcSource(domain, payload);
  const createdAt = new Date().toISOString();

  console.log(`[worker] ${WC_DEEP_QUEUE} job received at ${createdAt}`, { id, payload });

  if (!domain || typeof domain !== 'string' || !domain.includes('.')) {
    console.warn(`[worker] ${WC_DEEP_QUEUE} skipping: invalid domain=${domain}`);
    return;
  }

  const runId = await createIngestionRun(source, {
    ...payload,
    queue: WC_DEEP_QUEUE,
    merchant_id: merchantId,
  });
  if (!runId) {
    console.error(`[worker] Failed to create ingestion run for ${WC_DEEP_QUEUE} job, skipping`);
    return;
  }

  try {
    console.log(`[worker] Starting WC deep-page scrape for ${domain} (pages ${pageStart}-${pageEnd})`);
    const products = await scrapeWooCommerceStore(domain, {
      pageStart,
      pageEnd,
      perPage: WC_DEEP_PER_PAGE,
      pageTimeoutMs: WC_DEEP_PAGE_TIMEOUT_MS,
      pageConcurrency: WC_DEEP_PAGE_CONCURRENCY,
    });
    console.log(`[worker] WC deep-scraped ${products.length} products from ${domain}`);

    if (products.length === 0) {
      console.log(`[worker] No WC products for ${domain} (catalog shorter than page ${pageStart})`);
      await updateIngestionRun(runId, 'completed', 0, 0, 0);
      await markMerchantIngested(merchantId);
      return;
    }

    let totalInserted = 0;
    let totalUpdated = 0;
    let totalFailed = 0;
    const chunks = chunkArray(products, INGEST_BATCH_LIMIT);
    for (let ci = 0; ci < chunks.length; ci++) {
      const chunk = chunks[ci];
      console.log(`[worker] Ingesting WC chunk ${ci + 1}/${chunks.length} (${chunk.length} products) for ${domain}`);
      try {
        const r = await ingestProductsToCatalog(chunk, source);
        totalInserted += r.rows_inserted || 0;
        totalUpdated += r.rows_updated || 0;
        totalFailed += r.rows_failed || 0;
        console.log(`[worker] WC chunk ${ci + 1}/${chunks.length} result:`, {
          inserted: r.rows_inserted,
          updated: r.rows_updated,
          failed: r.rows_failed,
        });
      } catch (chunkErr) {
        // One chunk's failure does not fail the run — record the
        // chunk as failed rows and continue.
        const msg = chunkErr?.message || String(chunkErr);
        console.error(`[worker] WC chunk ${ci + 1}/${chunks.length} failed for ${domain}: ${msg}`);
        totalFailed += chunk.length;
      }
    }

    const status = totalFailed === 0 ? 'completed' : 'completed_with_errors';
    await updateIngestionRun(runId, status, totalInserted, totalUpdated, totalFailed);
    console.log(`[worker] ${WC_DEEP_QUEUE} job completed: ${status}`, {
      domain,
      merchantId,
      inserted: totalInserted,
      updated: totalUpdated,
      failed: totalFailed,
    });

    // Mark merchant as 'ingested' so the daily producer doesn't re-enqueue
    // it on the next cron tick. If the merchant id looks like a domain
    // (no spaces, contains a dot), the UPDATE matches; otherwise the
    // UPDATE is a no-op (logged in the catch).
    await markMerchantIngested(merchantId);
  } catch (err) {
    const errorMessage = err.message || String(err);
    console.error(`[worker] ${WC_DEEP_QUEUE} job failed:`, errorMessage);
    await updateIngestionRun(runId, 'failed', 0, 0, 0, errorMessage);
  }
});

console.log(`[worker] listening on queue ${WC_DEEP_QUEUE}`);

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
      queues: [PAGE1_QUEUE, DEEP_QUEUE, WC_DEEP_QUEUE],
      deep_config: {
        start_page: DEEP_START_PAGE,
        end_page: DEEP_END_PAGE,
        limit: DEEP_LIMIT,
        singleton_hours: DEEP_SINGLETON_HOURS,
      },
      wc_deep_config: {
        start_page: WC_DEEP_START_PAGE,
        end_page: WC_DEEP_END_PAGE,
        per_page: WC_DEEP_PER_PAGE,
        page_timeout_ms: WC_DEEP_PAGE_TIMEOUT_MS,
        page_concurrency: WC_DEEP_PAGE_CONCURRENCY,
        singleton_hours: WC_DEEP_SINGLETON_HOURS,
      },
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
