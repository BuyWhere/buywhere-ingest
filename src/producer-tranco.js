// BUY-34836: Tranco non-Shopify discovery producer.
//
// Daily cron that fetches the latest Tranco top-1M domain list and enqueues
// 1k-batch `discover.tranco` jobs on the canonical BuyWhere DB. Mirrors the
// shape of producer-woocommerce.js (the WC deep producer) so the
// railway.json scheduled entry is a drop-in.
//
// The original `scripts/buy31716-tranco-nonshopify-miner.mjs` (in the
// 5bc984ee-… workspace) probed `/products.json?limit=1` only — which is a
// Shopify endpoint. The replacement breaks the work into 4 platform kinds
// (woocommerce, magento, bigcommerce, custom) so each job's worker probes
// the right endpoint for the right platform. Singleton dedupe is per
// (rank_start, rank_end, kind) so the daily re-enqueue is safe.

import dotenv from 'dotenv';
import PgBoss from 'pg-boss';

import { fetchTrancoList, SUPPORTED_KINDS } from './trancoDiscovery.js';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

const QUEUE_NAME = 'discover.tranco';
const BATCH_SIZE = parseInt(process.env.TRANCO_PRODUCER_BATCH_SIZE || '1000', 10);
const TOP_N = parseInt(process.env.TRANCO_PRODUCER_TOP_N || '1000000', 10);
const SINGLETON_HOURS = parseInt(process.env.TRANCO_PRODUCER_SINGLETON_HOURS || '23', 10);
const ENABLED_KINDS = (process.env.TRANCO_PRODUCER_KINDS || SUPPORTED_KINDS.join(','))
  .split(',').map((s) => s.trim()).filter((k) => SUPPORTED_KINDS.includes(k));
const TRANCO_LIST_ID = process.env.TRANCO_LIST_ID || null;
const TRANCO_FETCH_TIMEOUT_MS = parseInt(process.env.TRANCO_FETCH_TIMEOUT_MS || '30000', 10);

const pgBoss = new PgBoss({
  connectionString: catalogDbUrl,
  schema: 'pgboss',
});

const summary = {
  startedAt: new Date().toISOString(),
  listId: null,
  availableDate: null,
  topN: TOP_N,
  batchSize: BATCH_SIZE,
  enabledKinds: ENABLED_KINDS,
  totalRows: 0,
  totalBatches: 0,
  enqueued: 0,
  skippedSingleton: 0,
  skippedInvalid: 0,
  errors: [],
};

async function enqueueBatchJob(rankStart, rankEnd, kind) {
  const singletonKey = `tranco:${rankStart}-${rankEnd}:${kind}`;
  try {
    const jobId = await pgBoss.send(QUEUE_NAME, {
      rank_range: { start: rankStart, end: rankEnd },
      kind,
      enqueuedAt: new Date().toISOString(),
      trancoListId: summary.listId,
    }, {
      singletonKey,
      singletonHours: SINGLETON_HOURS,
      retryLimit: 1,
      expireInHours: SINGLETON_HOURS + 1,
    });
    summary.enqueued++;
    console.log(`[tranco-producer] Enqueued ${QUEUE_NAME} job ${jobId || '<accepted>'} for ranks ${rankStart}-${rankEnd} (kind=${kind}, key=${singletonKey})`);
  } catch (err) {
    const msg = String(err && err.message || err);
    if (/singleton/i.test(msg) || /already.*active/i.test(msg)) {
      summary.skippedSingleton++;
      console.log(`[tranco-producer] Skipped ranks ${rankStart}-${rankEnd} (kind=${kind}, singleton dedupe, retry within ${SINGLETON_HOURS}h)`);
    } else {
      summary.errors.push({ singletonKey, error: msg });
      console.error(`[tranco-producer] Failed to enqueue job for ranks ${rankStart}-${rankEnd} (kind=${kind}):`, msg);
    }
  }
}

async function main() {
  console.log('[tranco-producer] Starting Tranco non-Shopify discovery producer...');
  console.log(`[tranco-producer] config: TOP_N=${TOP_N} BATCH_SIZE=${BATCH_SIZE} SINGLETON_HOURS=${SINGLETON_HOURS} KINDS=${ENABLED_KINDS.join(',')} TRANCO_LIST_ID=${TRANCO_LIST_ID || '<latest>'}`);

  if (ENABLED_KINDS.length === 0) {
    throw new Error(`No enabled kinds. Set TRANCO_PRODUCER_KINDS to a comma-separated list of: ${SUPPORTED_KINDS.join(', ')}`);
  }

  // Fetch the latest Tranco list.
  const tranco = await fetchTrancoList({
    limit: TOP_N,
    listId: TRANCO_LIST_ID,
    fetchTimeoutMs: TRANCO_FETCH_TIMEOUT_MS,
  });
  summary.listId = tranco.listId;
  summary.availableDate = tranco.availableDate;
  summary.totalRows = tranco.rows.length;
  console.log(`[tranco-producer] Tranco list fetched list_id=${tranco.listId} available_date=${tranco.availableDate || '?'} rows=${tranco.rows.length}`);

  if (tranco.rows.length === 0) {
    console.log('[tranco-producer] Tranco list empty, exiting cleanly');
    return;
  }

  // Calculate batch count.
  const totalBatches = Math.ceil(tranco.rows.length / BATCH_SIZE);
  summary.totalBatches = totalBatches;
  console.log(`[tranco-producer] Planning ${totalBatches} rank-batches × ${ENABLED_KINDS.length} kinds = ${totalBatches * ENABLED_KINDS.length} jobs`);

  await pgBoss.start();
  console.log('[tranco-producer] pgboss started (schema bootstrapped if needed)');

  for (let b = 0; b < totalBatches; b++) {
    const rankStart = b * BATCH_SIZE + 1; // 1-based rank range
    const rankEnd = Math.min((b + 1) * BATCH_SIZE, tranco.rows.length);
    for (const kind of ENABLED_KINDS) {
      await enqueueBatchJob(rankStart, rankEnd, kind);
    }
  }

  console.log(`[tranco-producer] Enqueued ${summary.enqueued} jobs; ${summary.skippedSingleton} skipped by singleton dedupe; ${summary.errors.length} errors`);
}

main()
  .then(async () => {
    summary.finishedAt = new Date().toISOString();
    console.log('[tranco-producer] summary:', JSON.stringify(summary, null, 2));
  })
  .catch(async (err) => {
    console.error('[tranco-producer] Fatal error:', err);
    summary.errors.push({ fatal: String(err && err.message || err) });
    summary.finishedAt = new Date().toISOString();
    console.log('[tranco-producer] summary:', JSON.stringify(summary, null, 2));
    process.exitCode = 1;
  })
  .finally(async () => {
    try { await pgBoss.stop(); } catch {}
  });
