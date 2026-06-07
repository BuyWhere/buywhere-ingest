// BUY-34834: WooCommerce deep-page producer.
//
// One-shot CLI / Railway scheduled job that finds WooCommerce merchants
// in the `merchants` table (source = 'woocommerce') whose
// onboarding_stage is in ('discovered', 'interested') and enqueues one
// `scrape.woocommerce.deep` job per merchant with the page range from
// WC_DEEP_START_PAGE to WC_DEEP_END_PAGE (default 1..80).
//
// Mirrors the structure of producer.js (Shopify) — same singleton dedupe
// shape, same summary log, same pgBoss stop/finally teardown — so the
// buywhere-ingest/railway.json `scheduled` entry that runs this is a
// drop-in alongside the shopify-producer entry.

import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

const QUEUE_NAME = 'scrape.woocommerce.deep';
const BATCH_LIMIT = parseInt(process.env.WC_PRODUCER_BATCH_LIMIT || '500', 10);
const SINGLETON_HOURS = parseInt(process.env.WC_DEEP_SINGLETON_HOURS || process.env.WC_PRODUCER_SINGLETON_HOURS || '23', 10);
const START_PAGE = parseInt(process.env.WC_DEEP_START_PAGE || '1', 10);
const END_PAGE = parseInt(process.env.WC_DEEP_END_PAGE || '80', 10);
const COUNTRY_FILTER = (process.env.WC_PRODUCER_COUNTRY || '').split(',').map(s => s.trim()).filter(Boolean);

const pgBoss = new PgBoss({
  connectionString: catalogDbUrl,
  schema: 'pgboss',
});

const db = new pg.Pool({
  connectionString: catalogDbUrl,
  max: 2,
});

const summary = {
  startedAt: new Date().toISOString(),
  candidatesFound: 0,
  enqueued: 0,
  skippedSingleton: 0,
  skippedError: 0,
  errors: [],
};

async function findCandidateMerchants(limit) {
  const result = await db.query(
    `SELECT id, name, source, country, onboarding_stage
       FROM merchants
      WHERE source = 'woocommerce'
        AND onboarding_stage IN ('discovered', 'interested')
        AND ($1::text[] IS NULL OR cardinality($1::text[]) = 0 OR country = ANY($1::text[]))
      ORDER BY last_scraped_at ASC NULLS FIRST, created_at ASC
      LIMIT $2`,
    [COUNTRY_FILTER.length ? COUNTRY_FILTER : null, limit]
  );
  return result.rows;
}

async function enqueueWcJobs(merchants) {
  let enqueued = 0;
  let skippedSingleton = 0;

  for (const merchant of merchants) {
    const domain = merchant.id;
    if (!domain || typeof domain !== 'string' || !domain.includes('.')) {
      console.warn(`[wc-producer] Skipping invalid merchant row: id=${domain}`);
      summary.skippedError++;
      continue;
    }

    // Per-domain source so the per-(sku,source) dedup on the products
    // table cleanly namespaces each merchant's catalog.
    const source = `woocommerce_${domain.replace(/[^a-z0-9]/gi, '').toLowerCase()}`;

    try {
      const jobId = await pgBoss.send(QUEUE_NAME, {
        merchant_id: domain,
        merchantId: domain, // alias for backwards-compat with worker code
        domain,
        source,
        country: merchant.country,
        onboardingStage: merchant.onboarding_stage,
        page_start: START_PAGE,
        page_end: END_PAGE,
        enqueuedAt: new Date().toISOString(),
      }, {
        singletonKey: domain,
        singletonHours: SINGLETON_HOURS,
        retryLimit: 1,
        expireInHours: SINGLETON_HOURS + 1,
      });
      enqueued++;
      console.log(`[wc-producer] Enqueued ${QUEUE_NAME} job ${jobId || '<accepted>'} for ${domain} (${merchant.onboarding_stage}, country=${merchant.country}, pages=${START_PAGE}-${END_PAGE})`);
    } catch (err) {
      const msg = String(err && err.message || err);
      if (/singleton/i.test(msg) || /already.*active/i.test(msg)) {
        skippedSingleton++;
        console.log(`[wc-producer] Skipped ${domain} (singleton dedupe, retry within ${SINGLETON_HOURS}h)`);
      } else {
        summary.errors.push({ domain, error: msg });
        console.error(`[wc-producer] Failed to enqueue job for ${domain}:`, msg);
      }
    }
  }

  summary.enqueued = enqueued;
  summary.skippedSingleton = skippedSingleton;
  return { enqueued, skippedSingleton };
}

async function main() {
  console.log('[wc-producer] Starting WooCommerce deep-page job producer...');
  console.log(`[wc-producer] config: BATCH_LIMIT=${BATCH_LIMIT} SINGLETON_HOURS=${SINGLETON_HOURS} PAGES=${START_PAGE}-${END_PAGE} COUNTRY_FILTER=${COUNTRY_FILTER.join(',') || '<all>'}`);

  await pgBoss.start();
  console.log('[wc-producer] pgboss started (schema bootstrapped if needed)');

  const candidates = await findCandidateMerchants(BATCH_LIMIT);
  summary.candidatesFound = candidates.length;
  console.log(`[wc-producer] Found ${candidates.length} candidate WooCommerce merchants in [discovered, interested]`);

  if (candidates.length === 0) {
    console.log('[wc-producer] No candidate merchants to enqueue, exiting cleanly');
    return;
  }

  await enqueueWcJobs(candidates);

  console.log(`[wc-producer] Enqueued ${summary.enqueued} jobs; ${summary.skippedSingleton} skipped by singleton dedupe; ${summary.skippedError} invalid; ${summary.errors.length} errors`);
}

main()
  .then(async () => {
    summary.finishedAt = new Date().toISOString();
    console.log('[wc-producer] summary:', JSON.stringify(summary, null, 2));
  })
  .catch(async (err) => {
    console.error('[wc-producer] Fatal error:', err);
    summary.errors.push({ fatal: String(err && err.message || err) });
    summary.finishedAt = new Date().toISOString();
    console.log('[wc-producer] summary:', JSON.stringify(summary, null, 2));
    process.exitCode = 1;
  })
  .finally(async () => {
    try { await pgBoss.stop(); } catch {}
    try { await db.end(); } catch {}
  });
