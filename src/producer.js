import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;

if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

const QUEUE_NAME = 'scrape.shopify';
const BATCH_LIMIT = parseInt(process.env.PRODUCER_BATCH_LIMIT || '50', 10);
const SINGLETON_HOURS = parseInt(process.env.PRODUCER_SINGLETON_HOURS || '6', 10);
const COUNTRY_FILTER = (process.env.PRODUCER_COUNTRY || 'US,SG').split(',').map(s => s.trim()).filter(Boolean);

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
      WHERE source = 'shopify'
        AND onboarding_stage IN ('discovered', 'interested', 'backfilled_orphan')
        AND ($1::text[] IS NULL OR cardinality($1::text[]) = 0 OR country = ANY($1::text[]))
      ORDER BY created_at ASC
      LIMIT $2`,
    [COUNTRY_FILTER.length ? COUNTRY_FILTER : null, limit]
  );
  return result.rows;
}

async function enqueueShopifyJobs(merchants) {
  let enqueued = 0;
  let skippedSingleton = 0;

  for (const merchant of merchants) {
    const domain = merchant.id;
    if (!domain || typeof domain !== 'string' || !domain.includes('.')) {
      console.warn(`[producer] Skipping invalid merchant row: id=${domain}`);
      summary.skippedError++;
      continue;
    }

    const source = `shopify_${domain.replace(/[^a-z0-9]/gi, '').toLowerCase()}`;

    try {
      const jobId = await pgBoss.send(QUEUE_NAME, {
        merchantId: domain,
        domain,
        source,
        country: merchant.country,
        onboardingStage: merchant.onboarding_stage,
        enqueuedAt: new Date().toISOString(),
      }, {
        singletonKey: domain,
        singletonHours: SINGLETON_HOURS,
        retryLimit: 2,
        expireInHours: 23,
      });
      enqueued++;
      console.log(`[producer] Enqueued scrape.shopify job ${jobId || '<accepted>'} for ${domain} (${merchant.onboarding_stage}, country=${merchant.country})`);
    } catch (err) {
      const msg = String(err && err.message || err);
      if (/singleton/i.test(msg) || /already.*active/i.test(msg)) {
        skippedSingleton++;
        console.log(`[producer] Skipped ${domain} (singleton dedupe, retry within ${SINGLETON_HOURS}h)`);
      } else {
        summary.errors.push({ domain, error: msg });
        console.error(`[producer] Failed to enqueue job for ${domain}:`, msg);
      }
    }
  }

  summary.enqueued = enqueued;
  summary.skippedSingleton = skippedSingleton;
  return { enqueued, skippedSingleton };
}

async function main() {
  console.log('[producer] Starting Shopify scrape job producer...');
  console.log(`[producer] config: BATCH_LIMIT=${BATCH_LIMIT} SINGLETON_HOURS=${SINGLETON_HOURS} COUNTRY_FILTER=${COUNTRY_FILTER.join(',') || '<all>'}`);

  await pgBoss.start();
  console.log('[producer] pgboss started (schema bootstrapped if needed)');

  const candidates = await findCandidateMerchants(BATCH_LIMIT);
  summary.candidatesFound = candidates.length;
  console.log(`[producer] Found ${candidates.length} candidate merchants in [discovered, interested, backfilled_orphan]`);

  if (candidates.length === 0) {
    console.log('[producer] No candidate merchants to enqueue, exiting cleanly');
    return;
  }

  await enqueueShopifyJobs(candidates);

  console.log(`[producer] Enqueued ${summary.enqueued} jobs; ${summary.skippedSingleton} skipped by singleton dedupe; ${summary.skippedError} invalid; ${summary.errors.length} errors`);
}

main()
  .then(async () => {
    summary.finishedAt = new Date().toISOString();
    console.log('[producer] summary:', JSON.stringify(summary, null, 2));
  })
  .catch(async (err) => {
    console.error('[producer] Fatal error:', err);
    summary.errors.push({ fatal: String(err && err.message || err) });
    summary.finishedAt = new Date().toISOString();
    console.log('[producer] summary:', JSON.stringify(summary, null, 2));
    process.exitCode = 1;
  })
  .finally(async () => {
    try { await pgBoss.stop(); } catch {}
    try { await db.end(); } catch {}
  });
