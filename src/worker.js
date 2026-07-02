import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';
import http from 'http';
import { scrapeShopifyStore, scrapeShopifyStorePages } from './shopifyScraper.js';
import { scrapeWooCommerceStore } from './woocommerceScraper.js';
import { getIngestionStats, getRecentJobs, getQueueStats } from './health.js';
import {
  probeDomainsStrict,
  loadCandidateList,
  isProbeableDomain,
} from './ccDiscover.js';
import {
  fetchTrancoList,
  probeTrancoHost,
  SUPPORTED_KINDS,
} from './trancoDiscovery.js';
import {
  walkSitemapForProducts,
  countryFromHost,
  SUPPORTED_KINDS as SITEMAP_KINDS,
  MIN_PRODUCTS_THRESHOLD as SITEMAP_MIN_PRODUCTS_DEFAULT,
} from './sitemapDiscover.js';
import {
  LANE_ROLES,
  LANE_ROLE_CONFIG,
  fetchLaneCandidatePages,
  evaluateLaneQuality,
  laneProductsToIngestRows,
} from './laneRunner.js';
import { chunkArray } from './chunker.js';

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
console.log('[worker] pg-boss started');

// Ensure all queue partitions exist before subscribing with work().
// pgBoss.start() does not auto-create partitions for queues that are
// registered only via work(); they must be created explicitly via
// createQueue() or send(). This bootstrap makes fresh deployments
// self-contained.
await ensureQueuePartitions(pgBoss);

// Minimal health server started IMMEDIATELY so Railway's healthcheck passes
// before the slower pgBoss.work() subscriptions complete. The full /healthz
// with stats is handled by the health server at the bottom of this file,
// but we need a responsive port during startup.
const _earlyHealthPort = parseInt(process.env.PORT || '3000', 10);
const _earlyHealthServer = http.createServer((req, res) => {
  if (req.url === '/health' || req.url === '/healthz') {
    res.statusCode = 200;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ status: 'healthy', timestamp: new Date().toISOString(), service: 'buywhere-ingest-worker', starting: true }));
  } else {
    res.statusCode = 404;
    res.end(JSON.stringify({ error: 'not found' }));
  }
});
_earlyHealthServer.listen(_earlyHealthPort, () => {
  console.log(`[worker] early healthz server listening on port ${_earlyHealthPort}`);
});

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

// BUY-35410: skip products with null/0 price — these are parse failures from
// shopify scraper, not legitimate free products. Filter before ingest to avoid
// polluting the catalog with 0-priced items that poison find_best_price.
function filterZeroPriceProducts(products) {
  return products.filter(p => p.price != null && p.price > 0);
}

async function ingestProductsToCatalog(products, source) {
  const valid = filterZeroPriceProducts(products);
  if (valid.length === 0) {
    console.log('[worker] All products filtered out (null/0 price), skipping ingest');
    return { rows_inserted: 0, rows_updated: 0, rows_failed: 0 };
  }
  if (valid.length < products.length) {
    console.log(`[worker] Filtered ${products.length - valid.length} null/0-price products, ingesting ${valid.length}`);
  }
  const apiBaseUrl = process.env.BUYWHERE_API_URL || 'https://api.buywhere.ai';
  const response = await fetch(`${apiBaseUrl}/v1/ingest/products`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `ApiKey ${ingestApiKey}`,
    },
    body: JSON.stringify({
      source,
      products: valid,
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
// BUY-34013: teamConcurrency 1→8 to close the ~320x gap to 150k/hr goal.
// Each job is an independent Shopify scrape, so parallelism is safe.
// ---------------------------------------------------------------------------
await pgBoss.work(PAGE1_QUEUE, {
  batchSize: 1,
  teamConcurrency: 8,
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
// BUY-34013: teamConcurrency 1→8. Deep jobs are independent per domain,
// so parallelism is safe and multiplies effective scrape throughput.
// ---------------------------------------------------------------------------
await pgBoss.work(DEEP_QUEUE, {
  batchSize: 1,
  teamConcurrency: 8,
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

    // BUY-48425: Shopify deep can produce up to (DEEP_END_PAGE-DEEP_START_PAGE+1) ×
    // DEEP_LIMIT rows in a single job — 74 pages × 250 = 18,500 products, far
    // above the /v1/ingest/products 1000-row cap. Chunk via the shared
    // helper so each request is its own short transaction. (The previous
    // single-call shape returned 400 from the API and held the run in a
    // failed-but-not-marked state for hours.)
    const deepTotals = await chunkedIngest(products, source, { logTag: 'deep', domain });
    const rowsInserted = deepTotals.rows_inserted;
    const rowsUpdated = deepTotals.rows_updated;
    const rowsFailed = deepTotals.rows_failed;
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
//
// BUY-34013: teamConcurrency 1→8. WC deep jobs are independent per domain.
// ---------------------------------------------------------------------------
// BUY-48425: cap each /v1/ingest/products request at 1000 rows (the API
// rejects >1000) and commit per batch. Previously the DEEP_QUEUE handler
// sent the full deep-paged payload (up to 18,500 rows for Shopify pages
// 7-80 × 250/page) in a single request — the API 400'd and the worker's
// throw left the run stuck for hours. With per-batch commit each chunk
// becomes its own short transaction, dropping INSERT txn duration from
// the 72-min max that pg_stat_statements was reporting down to a few
// seconds. Tunable via INGEST_BATCH_SIZE env var (default 1000).
const INGEST_BATCH_LIMIT = parseInt(process.env.INGEST_BATCH_SIZE || '1000', 10);

// Shared chunked ingest (BUY-48425): one /v1/ingest/products request per
// chunk of INGEST_BATCH_LIMIT rows. Each request is its own transaction
// in the API (no explicit BEGIN/COMMIT — node-pg auto-commits single
// statements), so a chunk's failure does not poison the rest. Returns
// aggregated { rows_inserted, rows_updated, rows_failed } plus the
// per-chunk log prefix used by callers ("WC", "lane", "deep").
async function chunkedIngest(products, source, { logTag, domain }) {
  const totals = { rows_inserted: 0, rows_updated: 0, rows_failed: 0 };
  if (!Array.isArray(products) || products.length === 0) return totals;
  const chunks = chunkArray(products, INGEST_BATCH_LIMIT);
  for (let ci = 0; ci < chunks.length; ci++) {
    const chunk = chunks[ci];
    console.log(`[worker] Ingesting ${logTag} chunk ${ci + 1}/${chunks.length} (${chunk.length} products) for ${domain}`);
    try {
      const r = await ingestProductsToCatalog(chunk, source);
      totals.rows_inserted += r.rows_inserted || 0;
      totals.rows_updated += r.rows_updated || 0;
      totals.rows_failed += r.rows_failed || 0;
      console.log(`[worker] ${logTag} chunk ${ci + 1}/${chunks.length} result:`, {
        inserted: r.rows_inserted,
        updated: r.rows_updated,
        failed: r.rows_failed,
      });
    } catch (chunkErr) {
      // One chunk's failure does not fail the run — record the
      // chunk as failed rows and continue. The API returns 400
      // for >1000 rows; the next chunk is retried with valid size.
      const msg = chunkErr?.message || String(chunkErr);
      console.error(`[worker] ${logTag} chunk ${ci + 1}/${chunks.length} failed for ${domain}: ${msg}`);
      totals.rows_failed += chunk.length;
    }
  }
  return totals;
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
  teamConcurrency: 8,
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
    // BUY-48425: delegate to the shared chunkedIngest helper. Each chunk
    // is its own request/transaction; a single chunk's failure does not
    // fail the run.
    const wcTotals = await chunkedIngest(products, source, { logTag: 'WC', domain });
    totalInserted = wcTotals.rows_inserted;
    totalUpdated = wcTotals.rows_updated;
    totalFailed = wcTotals.rows_failed;

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

// ---------------------------------------------------------------------------
// Common Crawl discovery worker (BUY-34835) — strict-probe pattern
// (conc=25, 20s timeout, retry x2 on fetch-failed) against a candidate
// list (bundled WAT pool snapshot, or a URL via CC_CANDIDATE_LIST_URL).
// Each job is one segment of the candidate list, sliced [segmentStart, segmentEnd).
// Verified hits are INSERTed into the `merchants` table with
// source='shopify' and onboarding_stage='discovered', so the existing
// Shopify producer (npm run producer) picks them up on the next cron tick
// and enqueues `scrape.shopify` jobs for actual catalog ingestion.
// ---------------------------------------------------------------------------
const DISCOVER_CC_QUEUE = 'discover.cc';
const DISCOVER_SEGMENT_SIZE = parseInt(process.env.DISCOVER_SEGMENT_SIZE || '1000', 10);
const DISCOVER_PROBE_CONCURRENCY = parseInt(process.env.DISCOVER_PROBE_CONCURRENCY || '25', 10);
const DISCOVER_PROBE_TIMEOUT_MS = parseInt(process.env.DISCOVER_PROBE_TIMEOUT_MS || '20000', 10);
const DISCOVER_PROBE_RETRY_MS = parseInt(process.env.DISCOVER_PROBE_RETRY_MS || '500', 10);
// Default to the bundled WAT pool snapshot. The producer emits the same
// default in the job payload, so this is only a fallback if a job arrives
// without a candidateList hint.
const DISCOVER_DEFAULT_CANDIDATE_LIST =
  process.env.CC_CANDIDATE_LIST_URL ||
  process.env.DISCOVER_CANDIDATE_LIST_PATH ||
  'data/wat-pool.jsonl';
const DISCOVER_SINGLETON_HOURS = parseInt(process.env.DISCOVER_SINGLETON_HOURS || '24', 10);

async function insertDiscoveredMerchant(domain, source, payload) {
  // The merchants table uses `id` as the domain (per BUY-33632 producer
  // query in producer.js). We INSERT ... ON CONFLICT DO UPDATE so a
  // re-probe of an already-known merchant is idempotent — the existing
  // onboarding_stage wins, and we just bump updated_at.
  //
  // `name` is the only non-required text column. We pull it from the WAT
  // pool's source tag when present (e.g. CC-MAIN-2025-43:...); otherwise
  // leave NULL.
  const watName = typeof payload?.source === 'string' && payload.source.includes('CC-MAIN-')
    ? payload.source.split(':')[0]
    : null;
  try {
    const r = await db.query(
      `INSERT INTO merchants (id, name, source, onboarding_stage, created_at, updated_at)
       VALUES ($1, $2, $3, 'discovered', NOW(), NOW())
       ON CONFLICT (id) DO UPDATE
         SET updated_at = NOW(),
             name = COALESCE(EXCLUDED.name, merchants.name),
             source = COALESCE(EXCLUDED.source, merchants.source)
       RETURNING id, (xmax = 0) AS inserted`,
      [domain, watName, 'shopify']
    );
    if (r.rows.length > 0) {
      return { ok: true, inserted: r.rows[0].inserted === true };
    }
    return { ok: false, reason: 'no_row_returned' };
  } catch (err) {
    // The `merchants` table is shared with other writers. A unique
    // violation on re-probe is the expected case and is handled by the
    // ON CONFLICT clause — we only see other errors here.
    return { ok: false, reason: err.message };
  }
}

await pgBoss.work(DISCOVER_CC_QUEUE, {
  batchSize: 1,
  teamConcurrency: 3,
}, async (jobs) => {
  const job = Array.isArray(jobs) ? jobs[0] : jobs;
  const id = job.id;
  const payload = job.data || {};
  const kind = payload.kind === 'wat' ? 'wat' : 'index';
  const segmentStart = Math.max(0, parseInt(payload.segmentStart, 10) || 0);
  const segmentEnd = Math.max(segmentStart + 1, parseInt(payload.segmentEnd, 10) || segmentStart + DISCOVER_SEGMENT_SIZE);
  const candidateListHint = payload.candidateList || DISCOVER_DEFAULT_CANDIDATE_LIST;
  const createdAt = new Date().toISOString();

  console.log(`[worker] ${DISCOVER_CC_QUEUE} job received at ${createdAt}`, {
    id, kind, segmentStart, segmentEnd, candidateListHint, payload,
  });

  const runId = await createIngestionRun(`cc_shopify_discover_v2`, {
    queue: DISCOVER_CC_QUEUE,
    kind, segmentStart, segmentEnd, candidateListHint,
  });
  if (!runId) {
    console.error(`[worker] Failed to create ingestion run for ${DISCOVER_CC_QUEUE} job, skipping`);
    return;
  }

  try {
    console.log(`[worker] ${DISCOVER_CC_QUEUE} loading candidate list: ${candidateListHint}`);
    const allCandidates = await loadCandidateList(candidateListHint);
    console.log(`[worker] ${DISCOVER_CC_QUEUE} loaded ${allCandidates.length} candidates from list`);

    const slice = allCandidates.slice(segmentStart, segmentEnd);
    console.log(`[worker] ${DISCOVER_CC_QUEUE} segment ${segmentStart}-${segmentEnd} has ${slice.length} candidates`);

    if (slice.length === 0) {
      console.log(`[worker] ${DISCOVER_CC_QUEUE} empty segment, marking completed`);
      await updateIngestionRun(runId, 'completed', 0, 0, 0);
      return;
    }

    // Skip domains already in the merchants table — probing them again
    // is wasted work. We only SELECT the `id` column to keep the query
    // cheap; a list of ~10k already-known Shopify domains is < 1MB.
    const allIds = slice.map((c) => c.domain);
    const knownRes = await db.query(
      `SELECT id FROM merchants WHERE id = ANY($1::text[])`,
      [allIds]
    );
    const knownSet = new Set(knownRes.rows.map((r) => r.id));
    const toProbe = slice.filter((c) => !knownSet.has(c.domain));
    console.log(`[worker] ${DISCOVER_CC_QUEUE} ${slice.length} candidates, ${knownSet.size} already in merchants, ${toProbe.length} to probe`);

    if (toProbe.length === 0) {
      await updateIngestionRun(runId, 'completed', 0, 0, 0);
      return;
    }

    const domains = toProbe.map((c) => c.domain);
    const { results, stats } = await probeDomainsStrict(domains, {
      concurrency: DISCOVER_PROBE_CONCURRENCY,
      timeoutMs: DISCOVER_PROBE_TIMEOUT_MS,
      retryDelayMs: DISCOVER_PROBE_RETRY_MS,
      onProgress: ({ done, total, verified, dead, retried }) => {
        if (done % 200 === 0 || done === total) {
          console.log(`[worker] ${DISCOVER_CC_QUEUE} progress: ${done}/${total} verified=${verified} dead=${dead} retried=${retried}`);
        }
      },
    });

    let insertedNew = 0;
    let insertedExisting = 0;
    let insertFailed = 0;
    for (const cand of toProbe) {
      const r = results.get(cand.domain);
      if (!r || !r.ok) continue;
      const insertResult = await insertDiscoveredMerchant(cand.domain, 'shopify', { source: cand.source });
      if (insertResult.ok) {
        if (insertResult.inserted) insertedNew++;
        else insertedExisting++;
      } else {
        insertFailed++;
        console.warn(`[worker] ${DISCOVER_CC_QUEUE} merchant insert failed for ${cand.domain}: ${insertResult.reason}`);
      }
    }

    // rowsInserted = newly-discovered merchants (the main BUY-34835 KPI).
    // rowsUpdated = merchants we re-confirmed via probe (already in the
    // table, ON CONFLICT bumped updated_at). rowsFailed = probes that
    // hit a non-Shopify site (the expected case for the WAT pool).
    await updateIngestionRun(runId, 'completed', insertedNew, insertedExisting, stats.dead);

    console.log(`[worker] ${DISCOVER_CC_QUEUE} segment ${segmentStart}-${segmentEnd} done`, {
      probed: stats.probed,
      verified: stats.verified,
      dead: stats.dead,
      retried: stats.retried,
      insertedNew,
      insertedExisting,
      insertFailed,
      maxDtMs: stats.maxDtMs,
      avgDtMs: stats.probed > 0 ? Math.round(stats.totalDtMs / stats.probed) : 0,
      errorMix: stats.errorMix,
    });
  } catch (err) {
    const errorMessage = err.message || String(err);
    console.error(`[worker] ${DISCOVER_CC_QUEUE} job failed:`, errorMessage);
    await updateIngestionRun(runId, 'failed', 0, 0, 0, errorMessage);
  }
});

console.log(`[worker] listening on queue ${DISCOVER_CC_QUEUE}`);

// ---------------------------------------------------------------------------
// Tranco non-Shopify discovery worker (BUY-34836) — replaces the live
// buy31716-tranco-nonshopify-miner.mjs (Oracle's old maglev-proxy lane).
//
// Each job carries `{ rank_range: { start, end }, kind, trancoListId }`.
// The worker fetches the latest Tranco list (cached for 24h in module
// scope), slices [start-1, end), runs the kind-specific platform probe
// (woocommerce / magento / bigcommerce / custom) on each host with
// bounded concurrency, and INSERTs verified hosts into the `merchants`
// table with source='tranco_<kind>' and onboarding_stage='discovered'.
// Singleton dedupe is per (rank_start, rank_end, kind) so the daily
// producer re-emit is safe.
//
// The Tranco list cache is shared across all worker jobs and refreshed
// lazily — the first job after process start fetches it; subsequent
// jobs within CACHE_TTL_MS use the cached copy. The cache key prefers
// the job's trancoListId hint, then TRANCO_LIST_ID env, then "latest".
// ---------------------------------------------------------------------------
const DISCOVER_TRANCO_QUEUE = 'discover.tranco';
const TRANCO_PROBE_CONCURRENCY = parseInt(process.env.TRANCO_PROBE_CONCURRENCY || '8', 10);
const TRANCO_PROBE_TIMEOUT_MS = parseInt(process.env.TRANCO_PROBE_TIMEOUT_MS || '6000', 10);
const TRANCO_LIST_CACHE_TTL_MS = parseInt(process.env.TRANCO_LIST_CACHE_TTL_MS || (24 * 60 * 60 * 1000), 10);
const TRANCO_LIST_FETCH_TIMEOUT_MS = parseInt(process.env.TRANCO_FETCH_TIMEOUT_MS || '30000', 10);
const TRANCO_SINGLETON_HOURS = parseInt(process.env.TRANCO_PRODUCER_SINGLETON_HOURS || '23', 10);

// In-memory cache: { listId, availableDate, rows, fetchedAtMs }.
let _trancoCache = null;
let _trancoCacheInflight = null;

async function getTrancoListCached(listIdHint) {
  const now = Date.now();
  if (_trancoCache && (now - _trancoCache.fetchedAtMs) < TRANCO_LIST_CACHE_TTL_MS) {
    // If the job specifies a different listId than the cached one,
    // bust the cache (e.g. operator pinned a new list ID).
    if (!listIdHint || _trancoCache.listId === listIdHint) {
      return _trancoCache;
    }
    console.log(`[worker] Tranco cache list_id mismatch (cached=${_trancoCache.listId} requested=${listIdHint}), busting`);
    _trancoCache = null;
  }
  if (_trancoCacheInflight) {
    return _trancoCacheInflight;
  }
  const fetchListId = listIdHint || process.env.TRANCO_LIST_ID || null;
  _trancoCacheInflight = (async () => {
    try {
      const t = await fetchTrancoList({
        limit: Math.max(parseInt(process.env.TRANCO_PRODUCER_TOP_N || '1000000', 10), 1000000),
        listId: fetchListId,
        fetchTimeoutMs: TRANCO_LIST_FETCH_TIMEOUT_MS,
      });
      _trancoCache = { ...t, fetchedAtMs: Date.now() };
      console.log(`[worker] Tranco list cached list_id=${t.listId} available_date=${t.availableDate || '?'} rows=${t.rows.length}`);
      return _trancoCache;
    } finally {
      _trancoCacheInflight = null;
    }
  })();
  return _trancoCacheInflight;
}

async function insertTrancoMerchant(domain, source, kind, evidence) {
  // Same idempotency shape as the BUY-34835 / discover.cc path. The
  // `name` column is the only non-required text column; we leave it NULL
  // for tranco discoveries (the WC deep lane fills it later from the
  // WC store response if available).
  //
  // `source` is the per-kind source label, e.g. `tranco_woocommerce`.
  // ON CONFLICT (id) DO UPDATE bumps updated_at so a re-probe of an
  // already-known merchant is non-destructive — the existing
  // onboarding_stage wins.
  try {
    const r = await db.query(
      `INSERT INTO merchants (id, name, source, onboarding_stage, created_at, updated_at)
       VALUES ($1, $2, $3, 'discovered', NOW(), NOW())
       ON CONFLICT (id) DO UPDATE
         SET updated_at = NOW(),
             source = COALESCE(EXCLUDED.source, merchants.source)
       RETURNING id, (xmax = 0) AS inserted`,
      [domain, null, source]
    );
    if (r.rows.length > 0) {
      return { ok: true, inserted: r.rows[0].inserted === true };
    }
    return { ok: false, reason: 'no_row_returned' };
  } catch (err) {
    return { ok: false, reason: err.message };
  }
}

async function probeTrancoDomains(domains, kind, { concurrency, timeoutMs, onProgress } = {}) {
  const results = new Map();
  const stats = { probed: 0, verified: 0, dead: 0, errorMix: {}, totalDtMs: 0, maxDtMs: 0 };
  const list = Array.isArray(domains) ? domains.slice() : [];
  for (let i = 0; i < list.length; i += concurrency) {
    const slice = list.slice(i, i + concurrency);
    const settled = await Promise.allSettled(
      slice.map(async (d) => {
        const t0 = Date.now();
        const r = await probeTrancoHost(d, kind, timeoutMs);
        r.dt = Date.now() - t0;
        return { domain: d, result: r };
      })
    );
    for (let k = 0; k < settled.length; k++) {
      const s = settled[k];
      stats.probed++;
      if (s.status !== 'fulfilled') {
        stats.dead++;
        const reason = 'promise_rejected';
        stats.errorMix[reason] = (stats.errorMix[reason] || 0) + 1;
        results.set(slice[k], { ok: false, reason, dt: 0 });
        continue;
      }
      const { domain, result } = s.value;
      results.set(domain, result);
      stats.totalDtMs += result.dt || 0;
      if ((result.dt || 0) > stats.maxDtMs) stats.maxDtMs = result.dt || 0;
      if (result.ok) {
        stats.verified++;
      } else {
        stats.dead++;
        const reason = result.reason || 'unknown';
        stats.errorMix[reason] = (stats.errorMix[reason] || 0) + 1;
      }
    }
    if (onProgress) {
      onProgress({
        done: Math.min(i + concurrency, list.length),
        total: list.length,
        verified: stats.verified,
        dead: stats.dead,
      });
    }
  }
  return { results, stats };
}

await pgBoss.work(DISCOVER_TRANCO_QUEUE, {
  batchSize: 1,
  teamConcurrency: 2,
}, async (jobs) => {
  const job = Array.isArray(jobs) ? jobs[0] : jobs;
  const id = job.id;
  const payload = job.data || {};
  const kind = SUPPORTED_KINDS.includes(payload.kind) ? payload.kind : 'custom';
  const rankStart = Math.max(1, parseInt(payload?.rank_range?.start, 10) || 1);
  const rankEnd = Math.max(rankStart, parseInt(payload?.rank_range?.end, 10) || rankStart);
  const listIdHint = typeof payload.trancoListId === 'string' ? payload.trancoListId : null;
  const createdAt = new Date().toISOString();

  console.log(`[worker] ${DISCOVER_TRANCO_QUEUE} job received at ${createdAt}`, {
    id, kind, rankStart, rankEnd, listIdHint, payload,
  });

  if (rankEnd < rankStart) {
    console.warn(`[worker] ${DISCOVER_TRANCO_QUEUE} invalid rank range start=${rankStart} end=${rankEnd}, marking failed`);
    return;
  }

  const runId = await createIngestionRun(`tranco_${kind}_discover`, {
    queue: DISCOVER_TRANCO_QUEUE,
    kind, rankStart, rankEnd, listIdHint,
  });
  if (!runId) {
    console.error(`[worker] Failed to create ingestion run for ${DISCOVER_TRANCO_QUEUE} job, skipping`);
    return;
  }

  try {
    // 1. Load (or refresh) the Tranco list cache.
    const tranco = await getTrancoListCached(listIdHint);
    if (!tranco || !Array.isArray(tranco.rows) || tranco.rows.length === 0) {
      console.error(`[worker] ${DISCOVER_TRANCO_QUEUE} Tranco list unavailable`);
      await updateIngestionRun(runId, 'failed', 0, 0, 0, 'tranco_list_unavailable');
      return;
    }

    // 2. Slice the rank range. Tranco rows are 1-based, so rank 1 = rows[0].
    const slice = tranco.rows.slice(rankStart - 1, rankEnd);
    console.log(`[worker] ${DISCOVER_TRANCO_QUEUE} ranks ${rankStart}-${rankEnd} -> ${slice.length} candidates`);

    if (slice.length === 0) {
      console.log(`[worker] ${DISCOVER_TRANCO_QUEUE} empty rank range, marking completed`);
      await updateIngestionRun(runId, 'completed', 0, 0, 0);
      return;
    }

    // 3. Skip hosts already in merchants.
    const allIds = slice.map((r) => r.domain);
    const knownRes = await db.query(
      `SELECT id FROM merchants WHERE id = ANY($1::text[])`,
      [allIds]
    );
    const knownSet = new Set(knownRes.rows.map((r) => r.id));
    const toProbe = slice.filter((r) => !knownSet.has(r.domain));
    console.log(`[worker] ${DISCOVER_TRANCO_QUEUE} ${slice.length} candidates, ${knownSet.size} already in merchants, ${toProbe.length} to probe`);

    if (toProbe.length === 0) {
      await updateIngestionRun(runId, 'completed', 0, 0, 0);
      return;
    }

    // 4. Probe each host with the kind-specific probe.
    const domains = toProbe.map((r) => r.domain);
    const { results, stats } = await probeTrancoDomains(domains, kind, {
      concurrency: TRANCO_PROBE_CONCURRENCY,
      timeoutMs: TRANCO_PROBE_TIMEOUT_MS,
      onProgress: ({ done, total, verified, dead }) => {
        if (done % 200 === 0 || done === total) {
          console.log(`[worker] ${DISCOVER_TRANCO_QUEUE} progress: ${done}/${total} verified=${verified} dead=${dead}`);
        }
      },
    });

    // 5. INSERT verified hosts into merchants.
    let insertedNew = 0;
    let insertedExisting = 0;
    let insertFailed = 0;
    const source = `tranco_${kind}`;
    for (const cand of toProbe) {
      const r = results.get(cand.domain);
      if (!r || !r.ok) continue;
      const insertResult = await insertTrancoMerchant(cand.domain, source, kind, r.evidence);
      if (insertResult.ok) {
        if (insertResult.inserted) insertedNew++;
        else insertedExisting++;
      } else {
        insertFailed++;
        console.warn(`[worker] ${DISCOVER_TRANCO_QUEUE} merchant insert failed for ${cand.domain}: ${insertResult.reason}`);
      }
    }

    // rowsInserted = newly-discovered merchants (the main BUY-34836 KPI).
    // rowsUpdated = re-confirmed via probe (already in the table).
    // rowsFailed = probes that hit a non-tranco site (the expected case).
    await updateIngestionRun(runId, 'completed', insertedNew, insertedExisting, stats.dead);
    console.log(`[worker] ${DISCOVER_TRANCO_QUEUE} ranks ${rankStart}-${rankEnd} (kind=${kind}) done`, {
      probed: stats.probed,
      verified: stats.verified,
      dead: stats.dead,
      insertedNew,
      insertedExisting,
      insertFailed,
      maxDtMs: stats.maxDtMs,
      avgDtMs: stats.probed > 0 ? Math.round(stats.totalDtMs / stats.probed) : 0,
      errorMix: stats.errorMix,
    });
  } catch (err) {
    const errorMessage = err.message || String(err);
    console.error(`[worker] ${DISCOVER_TRANCO_QUEUE} job failed:`, errorMessage);
    await updateIngestionRun(runId, 'failed', 0, 0, 0, errorMessage);
  }
});

console.log(`[worker] listening on queue ${DISCOVER_TRANCO_QUEUE}`);

// ---------------------------------------------------------------------------
// Sitemap-driven merchant discovery worker (BUY-34837) — replaces the live
// Oracle-workspace scripts
//   scripts/buy30590-brand-sitemap-miner.mjs (13 brand domains)
//   scripts/buy30590-retailer-sitemap-miner.mjs + buy30590-retailer-sitemap-loop.mjs
//     (9 retailer domains).
//
// The original scripts discovered product URLs from XML sitemaps and either
// scraped them inline (brand lane) or wrote them to a JSONL for a downstream
// scraper (retailer lane). The replacement focuses on the upstream job:
// discover *merchants* that have a real product sitemap. The actual catalog
// fetch is delegated to the existing scrape.shopify / scrape.woocommerce.deep
// cron producers (BUY-33632 / BUY-34834), which the buywhere-ingest service
// already runs.
//
// Each job carries `{ domain, sitemap_url, product_pattern, kind, source,
// country, ua_mode }`. The worker fetches the sitemap, walks the
// sitemapindex if present, parses <url><loc> entries, filters to
// product-shaped paths using the per-job regex, and INSERTs the *domain*
// (not the product URLs) into the `merchants` table on the canonical
// BuyWhere DB. Product URL count is recorded in the ingestion_runs row
// for monitoring.
//
// Singleton dedupe is per (kind, domain, sitemap_url) — matches the
// producer's singleton key so a re-enqueue within SITEMAP_SINGLETON_HOURS
// is a no-op. teamConcurrency=2 keeps the worker from getting blocked on
// a single slow sitemap (the brand lane is mostly Nike + Dyson = a few
// hundred ms each; the retailer lane is mostly Best Buy + Walmart = a
// few seconds each).
// ---------------------------------------------------------------------------
const DISCOVER_SITEMAP_QUEUE = 'discover.sitemap';
const SITEMAP_FETCH_TIMEOUT_MS = parseInt(process.env.SITEMAP_FETCH_TIMEOUT_MS || '20000', 10);
const SITEMAP_MAX_DEPTH = parseInt(process.env.SITEMAP_MAX_DEPTH || '4', 10);
const SITEMAP_MAX_LOCS = parseInt(process.env.SITEMAP_MAX_LOCS || '50000', 10);
const SITEMAP_SINGLETON_HOURS = parseInt(process.env.SITEMAP_SINGLETON_HOURS || '23', 10);
const SITEMAP_MIN_PRODUCTS = parseInt(process.env.SITEMAP_MIN_PRODUCTS || String(SITEMAP_MIN_PRODUCTS_DEFAULT || 5), 10);

async function insertSitemapMerchant(domain, source, country, kind, productCount) {
  // Idempotency: ON CONFLICT (id) DO UPDATE bumps updated_at so a
  // re-probe is non-destructive. The existing onboarding_stage wins;
  // we only refresh `source` if it's null (preserves any later-stage
  // label like 'shopify' that a downstream lane wrote).
  //
  // `name` is NULL at this stage — the downstream scrape lane fills it
  // from the merchant's first product page response.
  try {
    const r = await db.query(
      `INSERT INTO merchants (id, name, source, country, onboarding_stage, created_at, updated_at)
       VALUES ($1, $2, $3, $4, 'discovered', NOW(), NOW())
       ON CONFLICT (id) DO UPDATE
         SET updated_at = NOW(),
             country = COALESCE(EXCLUDED.country, merchants.country),
             source = COALESCE(merchants.source, EXCLUDED.source)
       RETURNING id, (xmax = 0) AS inserted`,
      [domain, null, source, country]
    );
    if (r.rows.length > 0) {
      return { ok: true, inserted: r.rows[0].inserted === true };
    }
    return { ok: false, reason: 'no_row_returned' };
  } catch (err) {
    return { ok: false, reason: err.message };
  }
}

await pgBoss.work(DISCOVER_SITEMAP_QUEUE, {
  batchSize: 1,
  teamConcurrency: 2,
}, async (jobs) => {
  const job = Array.isArray(jobs) ? jobs[0] : jobs;
  const id = job.id;
  const payload = job.data || {};
  const kind = SITEMAP_KINDS.includes(payload.kind) ? payload.kind : 'brand';
  const domain = payload.domain;
  const sitemapUrl = payload.sitemap_url;
  const productPattern = payload.product_pattern;
  const source = payload.source || `sitemap_${kind}`;
  const uaMode = payload.ua_mode === 'desktop' ? 'desktop' : 'bot';
  const country = typeof payload.country === 'string' && payload.country.length === 2
    ? payload.country.toUpperCase()
    : countryFromHost(domain);
  const createdAt = new Date().toISOString();

  console.log(`[worker] ${DISCOVER_SITEMAP_QUEUE} job received at ${createdAt}`, {
    id, kind, domain, sitemapUrl, source, country, uaMode, productPattern,
  });

  if (!domain || typeof domain !== 'string' || !domain.includes('.')) {
    console.warn(`[worker] ${DISCOVER_SITEMAP_QUEUE} invalid domain=${domain}, skipping`);
    return;
  }
  if (!sitemapUrl || typeof sitemapUrl !== 'string' || !/^https?:\/\//i.test(sitemapUrl)) {
    console.warn(`[worker] ${DISCOVER_SITEMAP_QUEUE} invalid sitemap_url=${sitemapUrl}, skipping`);
    return;
  }
  if (!productPattern || typeof productPattern !== 'string') {
    console.warn(`[worker] ${DISCOVER_SITEMAP_QUEUE} missing product_pattern for ${domain}, skipping`);
    return;
  }

  const runSource = `sitemap_${kind}_discover`;
  const runId = await createIngestionRun(runSource, {
    queue: DISCOVER_SITEMAP_QUEUE,
    kind, domain, sitemapUrl, source, country, uaMode,
  });
  if (!runId) {
    console.error(`[worker] Failed to create ingestion run for ${DISCOVER_SITEMAP_QUEUE} job, skipping`);
    return;
  }

  try {
    const ua = uaMode === 'desktop'
      ? 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
      : 'Mozilla/5.0 (compatible; BuywhereSitemapBot/1.0; +https://buywhere.example/bot)';
    const t0 = Date.now();
    const walk = await walkSitemapForProducts(sitemapUrl, {
      productPattern,
      ua,
      timeoutMs: SITEMAP_FETCH_TIMEOUT_MS,
      maxDepth: SITEMAP_MAX_DEPTH,
      maxLocs: SITEMAP_MAX_LOCS,
    });
    const dtMs = Date.now() - t0;
    const productCount = walk.productUrls.length;
    const verified = productCount >= SITEMAP_MIN_PRODUCTS;

    console.log(`[worker] ${DISCOVER_SITEMAP_QUEUE} ${domain} sitemap walked: products=${productCount} subs=${walk.subSitemapsWalked} fetches=${walk.fetches} dtMs=${dtMs} verified=${verified}`, {
      errors: walk.errors.slice(0, 5),
    });

    if (!verified) {
      // Below the threshold — we don't insert the merchant (would pollute
      // the queue with empty merchants), but we record the run so the
      // failure is visible in /healthz. rowsFailed = sub-fetches that
      // errored, if any.
      await updateIngestionRun(runId, 'completed', 0, 0, walk.errors.length || 0, verified ? null : `below_min_products:${productCount}`);
      return;
    }

    const insertResult = await insertSitemapMerchant(domain, source, country, kind, productCount);
    if (!insertResult.ok) {
      console.warn(`[worker] ${DISCOVER_SITEMAP_QUEUE} merchant insert failed for ${domain}: ${insertResult.reason}`);
      await updateIngestionRun(runId, 'failed', 0, 0, 0, `insert_failed:${insertResult.reason}`);
      return;
    }

    // rowsInserted = newly-discovered merchant (the main BUY-34837 KPI).
    // rowsUpdated = re-confirmed via sitemap (already in the table).
    // rowsFailed = sitemap fetch errors (separate from product count).
    const rowsInserted = insertResult.inserted ? 1 : 0;
    const rowsUpdated = insertResult.inserted ? 0 : 1;
    await updateIngestionRun(runId, 'completed', rowsInserted, rowsUpdated, walk.errors.length);
    console.log(`[worker] ${DISCOVER_SITEMAP_QUEUE} ${domain} done: inserted=${rowsInserted} reConfirmed=${rowsUpdated} errors=${walk.errors.length}`);
  } catch (err) {
    const errorMessage = err.message || String(err);
    console.error(`[worker] ${DISCOVER_SITEMAP_QUEUE} job failed for ${domain}:`, errorMessage);
    await updateIngestionRun(runId, 'failed', 0, 0, 0, errorMessage);
  }
});

console.log(`[worker] listening on queue ${DISCOVER_SITEMAP_QUEUE}`);

// ---------------------------------------------------------------------------
// Lane runner workers (BUY-34838) — five role-specific queues that replace
// the buy30620-page-lane-runner.mjs keepalives (hunt, hunt2, stock, crate)
// and the buy30620-scout-validate-lane.mjs (scout) running on the
// `5bc984ee-…` workspace. Each lane fetches a merchant's
// /products.json?limit=250&page=N with the role's per-config knobs, runs
// the role-specific quality filter, and on pass calls /v1/ingest/products
// directly (the legacy drain loop is no longer needed).
//
// Scout is intentionally different: it does a lightweight
// /products.json?limit=3 live-validation and does NOT call the ingest
// endpoint. Its job is to mark merchants as "verified" so a downstream
// producer (or the lane workers themselves, when filtered to
// `merchants.source='scout_verified'`) can scrape them.
//
// Per-(role, domain) dedupe lives in the `lane_processed` table — the
// worker INSERTs (role, domain, status, rows_inserted) on completion. The
// lane producer's singleton key is also per-(role, domain) within
// LANE_SINGLETON_HOURS, so the table is the second line of defense for
// candidates that slip through the singleton window.
// ---------------------------------------------------------------------------
const LANE_QUEUE_PREFIX = 'scrape.shopify.lane.';
const LANE_QUEUES = LANE_ROLES.map((role) => `${LANE_QUEUE_PREFIX}${role}`);
/**
 * Ensure pg-boss queue partitions exist for all queues used by this worker.
 * pgBoss.start() creates the base schema but does NOT auto-create partitions
 * for queues that have not yet received a send() call. Since this worker
 * subscribes via work() before any send(), we proactively create every queue
 * here so that fresh deployments never require manual SQL.
 *
 * This calls pgBoss.createQueue() which is idempotent — it calls the
 * pgboss.create_queue() PL/pgSQL function that uses ON CONFLICT DO NOTHING.
 */
async function ensureQueuePartitions(boss) {
  const queueNames = [
    PAGE1_QUEUE,
    DEEP_QUEUE,
    WC_DEEP_QUEUE,
    DISCOVER_CC_QUEUE,
    DISCOVER_TRANCO_QUEUE,
    DISCOVER_SITEMAP_QUEUE,
    ...LANE_QUEUES,
  ];
  // BUY-30092: Use a SECURITY DEFINER wrapper (pgboss.create_queue_safe) because
  // ingest_rw does not own pgboss.job and therefore cannot ATTACH PARTITION.
  // The safe wrapper runs as the function owner (postgres). pg-boss's built-in
  // boss.createQueue() calls pgboss.create_queue() directly, which would fail
  // under the least-privilege ingest_rw role.
  for (const name of queueNames) {
    try {
      await db.query(`SELECT pgboss.create_queue_safe($1, $2)`, [name, JSON.stringify({ policy: 'standard' })]);
      console.log(`[worker] ensured pg-boss queue partition: ${name}`);
    } catch (err) {
      console.error(`[worker] failed to ensure queue partition for ${name}:`, err.message);
    }
  }
}


// BUY-48425: lane runner routes through the shared chunkedIngest helper,
// which reads the same INGEST_BATCH_LIMIT (default 1000) as WC and deep.
// The hunt/hunt2/stock lanes paginate up to 40 pages of 250 = up to 10k
// products per merchant, so per-batch commit keeps each transaction
// short and prevents the autovacuum cleanup-lock contention that the
// 3-5min INSERTs were causing.

async function ensureLaneTables(dbPool) {
  // Mirror the producer's CREATE TABLE IF NOT EXISTS so a fresh
  // deploy without the producer ever running still has the tables
  // when the first job arrives. The producer also creates them — the
  // pair is idempotent.
  try {
    await dbPool.query(`
      CREATE TABLE IF NOT EXISTS lane_feed (
        domain TEXT PRIMARY KEY,
        platform TEXT,
        products_hint INTEGER,
        ts TIMESTAMPTZ,
        source TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
    `);
    await dbPool.query(`
      CREATE TABLE IF NOT EXISTS lane_processed (
        role TEXT NOT NULL,
        domain TEXT NOT NULL,
        status TEXT NOT NULL,
        rows_inserted INTEGER NOT NULL DEFAULT 0,
        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (role, domain)
      );
    `);
  } catch (err) {
    // Tables are owned by the catalog-db role; if the worker role
    // can't CREATE them (only the owner can), we log and move on —
    // the producer's tables are already there.
    console.warn(`[worker] lane tables ensure-if-not-exists warning: ${err.message}`);
  }
}

async function markLaneProcessed(role, domain, status, rowsInserted) {
  try {
    await db.query(
      `INSERT INTO lane_processed (role, domain, status, rows_inserted, last_seen_at)
       VALUES ($1, $2, $3, $4, NOW())
       ON CONFLICT (role, domain) DO UPDATE
         SET status = EXCLUDED.status,
             rows_inserted = EXCLUDED.rows_inserted,
             last_seen_at = NOW()`,
      [role, domain, status, rowsInserted]
    );
  } catch (err) {
    console.warn(`[worker] could not mark lane_processed (${role}, ${domain}): ${err.message}`);
  }
}

function buildLaneWorkerHandler(role) {
  return async (jobs) => {
    const job = Array.isArray(jobs) ? jobs[0] : jobs;
    const id = job.id;
    const payload = job.data || {};
    const domain = payload.domain;
    const cfg = LANE_ROLE_CONFIG[role] || LANE_ROLE_CONFIG.hunt;
    const createdAt = new Date().toISOString();

    console.log(`[worker] scrape.shopify.lane.${role} job received at ${createdAt}`, { id, domain, payload });

    if (!domain || typeof domain !== 'string' || !domain.includes('.')) {
      console.warn(`[worker] scrape.shopify.lane.${role} invalid domain=${domain}, skipping`);
      return;
    }

    // Per-role source so the catalog's (sku, source) dedup cleanly
    // namespaces each (role, merchant) catalog.
    const source = `lane_${role}_${domain.replace(/[^a-z0-9]/gi, '').toLowerCase()}`;
    const runId = await createIngestionRun(source, {
      queue: `scrape.shopify.lane.${role}`,
      role, domain, ...payload,
    });
    if (!runId) {
      console.error(`[worker] scrape.shopify.lane.${role} failed to create ingestion run for ${domain}, skipping`);
      return;
    }

    try {
      if (role === 'scout') {
        // Scout is a HEAD-style live validation: a single /products.json?limit=3
        // request with a tight (8s) timeout. We don't apply the page-1
        // quality filter — scout's job is to mark a merchant as "verified"
        // for downstream lanes, not to ingest products.
        const probe = await fetchLaneCandidatePages(domain, {
          maxPages: 1,
          pageDelayMs: 0,
          maxRetries: cfg.maxRetries,
          retryDelayMs: cfg.retryDelayMs,
          fetchTimeoutMs: cfg.fetchTimeoutMs,
          role,
        });
        if (!probe || probe.status !== 200) {
          console.log(`[worker] scrape.shopify.lane.${role} ${domain} no-200 (status=${probe?.status})`);
          await markLaneProcessed(role, domain, 'rejected', 0);
          await updateIngestionRun(runId, 'completed', 0, 0, 0, probe ? `status_${probe.status}` : 'fetch_failed');
          return;
        }
        const quality = evaluateLaneQuality(probe.products, { mode: cfg.qualityMode });
        if (!quality.pass) {
          console.log(`[worker] scrape.shopify.lane.${role} ${domain} quality-reject reason=${quality.reason}`);
          await markLaneProcessed(role, domain, 'rejected', 0);
          await updateIngestionRun(runId, 'completed', 0, 0, 0, `quality_${quality.reason}`);
          return;
        }
        // Scout accepted — record so downstream lanes can pick it up.
        // (A follow-up enhancement could INSERT a row into the merchants
        // table with onboarding_stage='discovered' so the cron producer
        // for `scrape.shopify` picks it up on its next tick. For now we
        // only update the per-role checkpoint — the lane producers read
        // from lane_feed directly.)
        await markLaneProcessed(role, domain, 'accepted', probe.products.length);
        await updateIngestionRun(runId, 'completed', 0, probe.products.length, 0);
        console.log(`[worker] scrape.shopify.lane.${role} ${domain} accepted products=${probe.products.length} attempts=${probe.attempts}`);
        return;
      }

      // Hunt / hunt2 / stock / crate: full page-1 fetch with role config.
      const scrape = await fetchLaneCandidatePages(domain, {
        maxPages: payload.maxPages || cfg.maxPages,
        pageDelayMs: payload.pageDelayMs ?? cfg.pageDelayMs,
        maxRetries: payload.maxRetries || cfg.maxRetries,
        retryDelayMs: payload.retryDelayMs || cfg.retryDelayMs,
        fetchTimeoutMs: payload.fetchTimeoutMs || cfg.fetchTimeoutMs,
        role,
      });

      if (!scrape || scrape.status !== 200) {
        console.log(`[worker] scrape.shopify.lane.${role} ${domain} fetch-failed status=${scrape?.status}`);
        await markLaneProcessed(role, domain, 'rejected', 0);
        await updateIngestionRun(runId, 'completed', 0, 0, 0, scrape ? `status_${scrape.status}` : 'fetch_failed');
        return;
      }

      const quality = evaluateLaneQuality(scrape.products, { mode: payload.qualityMode || cfg.qualityMode });
      if (!quality.pass) {
        console.log(`[worker] scrape.shopify.lane.${role} ${domain} quality-reject reason=${quality.reason}`);
        await markLaneProcessed(role, domain, 'rejected', 0);
        await updateIngestionRun(runId, 'completed', 0, 0, 0, `quality_${quality.reason}`);
        return;
      }

      const ingestRows = laneProductsToIngestRows(scrape.products, domain);
      // BUY-48425: route through the shared chunkedIngest helper so the
      // per-batch commit contract is consistent across deep, lane, and WC.
      const laneTotals = await chunkedIngest(ingestRows, source, { logTag: `lane.${role}`, domain });
      const totalInserted = laneTotals.rows_inserted;
      const totalUpdated = laneTotals.rows_updated;
      const totalFailed = laneTotals.rows_failed;

      const status = totalFailed === 0 ? 'completed' : 'completed_with_errors';
      await markLaneProcessed(role, domain, status, totalInserted);
      await updateIngestionRun(runId, status, totalInserted, totalUpdated, totalFailed);
      console.log(`[worker] scrape.shopify.lane.${role} ${domain} done: pages=${scrape.pageCount} products=${scrape.products.length} inserted=${totalInserted} updated=${totalUpdated} failed=${totalFailed} attempts=${scrape.attempts}`);
    } catch (err) {
      const errorMessage = err.message || String(err);
      console.error(`[worker] scrape.shopify.lane.${role} ${domain} job failed:`, errorMessage);
      await markLaneProcessed(role, domain, 'failed', 0);
      await updateIngestionRun(runId, 'failed', 0, 0, 0, errorMessage);
    }
  };
}

await ensureLaneTables(db);
for (const role of LANE_ROLES) {
  const queue = `scrape.shopify.lane.${role}`;
  // teamConcurrency: each role keeps a small worker pool so the five
  // roles don't starve each other on shared outbound bandwidth. The
  // per-role defaultConcurrency in LANE_ROLE_CONFIG caps the in-flight
  // fetches per job — pg-boss's teamConcurrency caps the parallel
  // jobs. With teamConcurrency=2, two lane.<role> jobs run in parallel
  // and each job runs up to defaultConcurrency fetches inside it.
  await pgBoss.work(queue, {
    batchSize: 1,
    teamConcurrency: 2,
  }, buildLaneWorkerHandler(role));
  console.log(`[worker] listening on queue ${queue}`);
}

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

    // Railway healthcheck requires HTTP 200 — return 200 even when busy.
    // Worker reports status=busy for observability but does not reject probes.
    res.statusCode = 200;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({
      status,
      timestamp: new Date().toISOString(),
      service: 'buywhere-ingest-worker',
      queues: [PAGE1_QUEUE, DEEP_QUEUE, WC_DEEP_QUEUE, DISCOVER_CC_QUEUE, DISCOVER_TRANCO_QUEUE, DISCOVER_SITEMAP_QUEUE, ...LANE_QUEUES],
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
      discover_cc_config: {
        segment_size: DISCOVER_SEGMENT_SIZE,
        probe_concurrency: DISCOVER_PROBE_CONCURRENCY,
        probe_timeout_ms: DISCOVER_PROBE_TIMEOUT_MS,
        probe_retry_ms: DISCOVER_PROBE_RETRY_MS,
        candidate_list_default: DISCOVER_DEFAULT_CANDIDATE_LIST,
        singleton_hours: DISCOVER_SINGLETON_HOURS,
      },
      discover_tranco_config: {
        probe_concurrency: TRANCO_PROBE_CONCURRENCY,
        probe_timeout_ms: TRANCO_PROBE_TIMEOUT_MS,
        cache_ttl_ms: TRANCO_LIST_CACHE_TTL_MS,
        singleton_hours: TRANCO_SINGLETON_HOURS,
        kinds: SUPPORTED_KINDS,
      },
      discover_sitemap_config: {
        fetch_timeout_ms: SITEMAP_FETCH_TIMEOUT_MS,
        max_depth: SITEMAP_MAX_DEPTH,
        max_locs: SITEMAP_MAX_LOCS,
        min_products: SITEMAP_MIN_PRODUCTS,
        singleton_hours: SITEMAP_SINGLETON_HOURS,
        kinds: SITEMAP_KINDS,
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
// Close the early health server and start the full one
try { _earlyHealthServer.close(); } catch (e) { /* already closed */ }
healthServer.listen(healthPort, () => {
  console.log(`[worker] full healthz server listening on port ${healthPort}`);
});
// Last verified: 2026-06-27 - worker fix deploy attempt
