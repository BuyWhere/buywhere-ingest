import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';
import crypto from 'crypto';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;

if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

// The maglev-replica products table is the same catalog DB — the query uses
// the product_embeddings table which lives in the same DB.
const EMBED_QUEUE = 'embed.products';
const BATCH_SIZE = 100;          // products per pg-boss job
const FETCH_LIMIT = 50000;       // max products per cron run
const SINGLETON_HOURS = 6;       // prevent re-enqueue of same job within window
const ENQUEUE_BATCH = 500;       // products per embed.products job payload

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
  jobsEnqueued: 0,
  productsEnqueued: 0,
  skippedSingleton: 0,
  errors: [],
};

function textHash(title, description) {
  const text = `${title || ''} ${description != null ? description : ''}`;
  return crypto.createHash('md5').update(text).digest('hex');
}

// ---------------------------------------------------------------------------
// Priority-ordered product selection:
//   - Products not yet embedded (no row in product_embeddings)
//   - Products whose text has changed (hash mismatch)
//   - Ordered by price DESC NULLS LAST (high-value products first)
//   - Limited to FETCH_LIMIT per run
// ---------------------------------------------------------------------------
async function findProductsToEmbed(limit) {
  // The priority ordering from BUY-41136 spec:
  // - NOT EXISTS: no embedding yet
  // - EXISTS with hash mismatch: text changed since last embed
  // - ORDER BY price DESC NULLS LAST
  const result = await db.query(
    `SELECT p.id, p.title, p.description
       FROM products p
      WHERE p.is_active = true
        AND (
          NOT EXISTS (
            SELECT 1 FROM product_embeddings pe
             WHERE pe.product_id = p.id
          )
          OR EXISTS (
            SELECT 1 FROM product_embeddings pe
             WHERE pe.product_id = p.id
               AND pe.text_hash != md5(p.title || ' ' || COALESCE(p.description, ''))
          )
        )
      ORDER BY p.price DESC NULLS LAST
      LIMIT $1`,
    [limit]
  );
  return result.rows;
}

async function enqueueEmbedJobs(products) {
  let jobsEnqueued = 0;
  let productsEnqueued = 0;

  // Chunk products into batches of ENQUEUE_BATCH
  for (let i = 0; i < products.length; i += ENQUEUE_BATCH) {
    const batch = products.slice(i, i + ENQUEUE_BATCH);

    // Each job carries a batch of products (the worker handles batching to Jina)
    const payload = {
      products: batch.map((p) => ({
        id: p.id,
        title: p.title,
        description: p.description,
      })),
      enqueuedAt: new Date().toISOString(),
    };

    try {
      const jobId = await pgBoss.send(EMBED_QUEUE, payload, {
        // No singletonKey — we always want to enqueue every batch.
        // The hash-gate in the worker is what prevents redundant API calls.
        retryLimit: 2,
        expireInHours: 24,
      });
      jobsEnqueued++;
      productsEnqueued += batch.length;
      console.log(`[producer-embed] enqueued job ${jobId || '<accepted>'} with ${batch.length} products (job ${jobsEnqueued}, total ${productsEnqueued})`);
    } catch (err) {
      const msg = String(err && err.message || err);
      summary.errors.push({ batch_start: i, error: msg });
      console.error(`[producer-embed] failed to enqueue batch at offset ${i}:`, msg);
    }
  }

  summary.jobsEnqueued = jobsEnqueued;
  summary.productsEnqueued = productsEnqueued;
}

async function main() {
  console.log('[producer-embed] Starting embed.products job producer...');
  console.log(`[producer-embed] config: FETCH_LIMIT=${FETCH_LIMIT} ENQUEUE_BATCH=${ENQUEUE_BATCH}`);

  await pgBoss.start();
  console.log('[producer-embed] pgboss started');

  const products = await findProductsToEmbed(FETCH_LIMIT);
  summary.candidatesFound = products.length;
  console.log(`[producer-embed] found ${products.length} products needing embedding`);

  if (products.length === 0) {
    console.log('[producer-embed] no products to embed, exiting cleanly');
    return;
  }

  await enqueueEmbedJobs(products);

  console.log(`[producer-embed] enqueued ${summary.jobsEnqueued} jobs for ${summary.productsEnqueued} products`);
}

main()
  .then(async () => {
    summary.finishedAt = new Date().toISOString();
    console.log('[producer-embed] summary:', JSON.stringify(summary, null, 2));
  })
  .catch(async (err) => {
    console.error('[producer-embed] fatal error:', err);
    summary.errors.push({ fatal: String(err && err.message || err) });
    summary.finishedAt = new Date().toISOString();
    console.log('[producer-embed] summary:', JSON.stringify(summary, null, 2));
    process.exitCode = 1;
  })
  .finally(async () => {
    try { await pgBoss.stop(); } catch {}
    try { await db.end(); } catch {}
  });
