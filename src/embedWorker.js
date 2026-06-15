import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';
import crypto from 'crypto';
import https from 'https';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
const vectorDbUrl = process.env.VECTOR_DB_URL || catalogDbUrl; // fallback to catalog DB if no separate vector DB
const cohereApiKey = process.env.COHERE_API_KEY;

if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}
if (!cohereApiKey) {
  throw new Error('Missing COHERE_API_KEY environment variable.');
}

const EMBED_QUEUE = 'embed.products';
const BATCH_SIZE = 64; // Cohere batch size per spec
const COHERE_MODEL = 'embed-multilingual-v3.0';
const COHERE_INPUT_TYPE = 'search_document';
const COHERE_DIMENSIONS = 1024; // Cohere multilingual v3.0 dimension
const COHERE_API_URL = 'https://api.cohere.ai/v1/embed';
const MAX_RETRIES = 3;
const BOSS_CONCURRENCY = 3;

const pgBoss = new PgBoss({
  connectionString: catalogDbUrl,
  schema: 'pgboss',
});

const db = new pg.Pool({
  connectionString: catalogDbUrl,
  max: 4,
});

const vectorDb = new pg.Pool({
  connectionString: vectorDbUrl,
  max: 2,
});

pgBoss.on('error', (err) => {
  console.error('[pg-boss] error', err);
});

await pgBoss.start();

// ---------------------------------------------------------------------------
// Hash-gate: compute SHA256(title + ' ' + COALESCE(description, ''))
// ---------------------------------------------------------------------------
function textHash(title, description) {
  const text = `${title || ''} ${description != null ? description : ''}`;
  return crypto.createHash('sha256').update(text).digest('hex');
}

// ---------------------------------------------------------------------------
// Cohere API call with exponential backoff retry
// ---------------------------------------------------------------------------
async function embedWithCohere(texts, attempt = 1) {
  const response = await fetch(COHERE_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${cohereApiKey}`,
      'X-Client-Name': 'buywhere',
    },
    body: JSON.stringify({
      model: COHERE_MODEL,
      input_type: COHERE_INPUT_TYPE,
      texts: texts,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    const err = new Error(`Cohere API returned ${response.status}: ${errorText}`);
    if (attempt < MAX_RETRIES) {
      const delay = Math.min(1000 * 2 ** (attempt - 1), 10000);
      console.warn(`[embed] Cohere API error (attempt ${attempt}/${MAX_RETRIES}), retrying in ${delay}ms: ${err.message}`);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return embedWithCohere(texts, attempt + 1);
    }
    throw err;
  }

  const data = await response.json();
  return data.embeddings; // array of number[]
}

// ---------------------------------------------------------------------------
// Vector DB upsert — per-batch commit, survives 120s DML kill-watcher
// ---------------------------------------------------------------------------
async function upsertProductEmbeddings(records) {
  if (!records || records.length === 0) return;

  const client = await vectorDb.connect();
  try {
    await client.query('BEGIN');

    for (const rec of records) {
      // Only update if text_hash differs — skip price-only changes (~80% of ingest)
      await client.query(
        `INSERT INTO product_embeddings (product_id, embedding, text_hash, embedded_at)
         VALUES ($1::uuid, $2::halfvec(1024), $3, NOW())
         ON CONFLICT (product_id) DO UPDATE
           SET embedding = EXCLUDED.embedding,
               text_hash = EXCLUDED.text_hash,
               embedded_at = NOW()
         WHERE product_embeddings.text_hash != EXCLUDED.text_hash`,
        [rec.product_id, `[${rec.embedding}]`, rec.text_hash]
      );
    }

    await client.query('COMMIT');
    console.log(`[embed] upserted ${records.length} product_embeddings rows`);
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}

// ---------------------------------------------------------------------------
// embed.products worker
// BOSS_CONCURRENCY=3: batchSize=100 products → Jina API → upsert
// ---------------------------------------------------------------------------
await pgBoss.work(EMBED_QUEUE, {
  batchSize: 1,
  teamConcurrency: BOSS_CONCURRENCY,
}, async (jobs) => {
  const job = Array.isArray(jobs) ? jobs[0] : jobs;
  const id = job.id;
  const payload = job.data || {};
  const products = payload.products || [];
  const createdAt = new Date().toISOString();

  console.log(`[embed] ${EMBED_QUEUE} job ${id} received at ${createdAt} with ${products.length} products`);

  if (products.length === 0) {
    console.log(`[embed] empty product list, skipping`);
    return;
  }

  try {
    // 1. Hash-gate: skip products whose text hash matches the existing record
    const productIds = products.map((p) => p.id);
    const existingRows = await vectorDb.query(
      `SELECT product_id, text_hash FROM product_embeddings WHERE product_id = ANY($1::uuid[])`,
      [productIds]
    );
    const existingHashMap = new Map(existingRows.rows.map((r) => [String(r.product_id), r.text_hash]));

    const toEmbed = [];
    const skippedHashMatch = [];

    for (const product of products) {
      const hash = textHash(product.title, product.description);
      const existingHash = existingHashMap.get(String(product.id));

      if (existingHash !== undefined && existingHash === hash) {
        // Price-only update — skip re-embed
        skippedHashMatch.push(product.id);
      } else {
        toEmbed.push({ ...product, hash });
      }
    }

    if (skippedHashMatch.length > 0) {
      console.log(`[embed] hash-gate skipped ${skippedHashMatch.length} products (text unchanged)`);
    }

    if (toEmbed.length === 0) {
      console.log(`[embed] all ${products.length} products skipped by hash gate, nothing to embed`);
      return;
    }

    console.log(`[embed] embedding ${toEmbed.length} products (${products.length - toEmbed.length} skipped)`);

    // 2. Batch and call Cohere API
    const texts = toEmbed.map((p) => `${p.title || ''} ${p.description != null ? p.description : ''}`.trim());
    const embeddings = await embedWithCohere(texts);

    if (!embeddings || embeddings.length === 0) {
      throw new Error('Cohere API returned empty embeddings array');
    }

    // 3. Build records and upsert to vector DB
    const records = [];

    for (let i = 0; i < toEmbed.length; i++) {
      const product = toEmbed[i];
      const embedding = embeddings[i];
      if (!embedding) {
        console.warn(`[embed] no embedding for product ${product.id} at index ${i}, skipping`);
        continue;
      }
      records.push({
        product_id: product.id,
        embedding: embedding,
        text_hash: product.hash,
      });
    }

    await upsertProductEmbeddings(records);

    console.log(`[embed] job ${id} completed: ${records.length} products embedded, ${skippedHashMatch.length} skipped`);
  } catch (err) {
    console.error(`[embed] job ${id} failed:`, err.message);
    throw err; // re-throw so pg-boss handles retry/dead-letter
  }
});

console.log(`[embed] listening on queue ${EMBED_QUEUE} (teamConcurrency=${BOSS_CONCURRENCY}, batchSize=${BATCH_SIZE})`);

// ---------------------------------------------------------------------------
// Health server on a separate port so the embed worker can run alongside
// the main worker. The embed worker is started independently via:
//   node src/embedWorker.js
// and the main worker.js healthz covers the primary queues only.
// ---------------------------------------------------------------------------
const embedHealthPort = parseInt(process.env.EMBED_HEALTH_PORT || '3001', 10);
const httpsAgent = new https.Agent({ keepAlive: true });

import('express').then(({ default: express }) => {
  const app = express();

  // Simple liveness probe
  app.get('/healthz', (_req, res) => {
    res.json({ status: 'ok', service: 'buywhere-embed-worker', timestamp: new Date().toISOString() });
  });

  // Detailed health: verifies db, vector-db, pgboss queue state
  app.get('/health', async (_req, res) => {
    const out = {
      service: 'buywhere-embed-worker',
      timestamp: new Date().toISOString(),
      checks: {},
    };
    let healthy = true;

    // Check primary (catalog) DB
    try {
      const r = await db.query('SELECT 1 AS ok, NOW() AS now');
      out.checks.catalog_db = { status: 'ok', now: r.rows[0].now };
    } catch (e) {
      out.checks.catalog_db = { status: 'fail', error: e.message };
      healthy = false;
    }

    // Check vector DB
    try {
      const r = await vectorDb.query('SELECT count(*)::bigint AS n FROM product_embeddings');
      const stateRow = await vectorDb.query(
        "SELECT id, last_processed_product_id, products_embedded, started_at FROM embedding_pipeline_state WHERE id = 'main'"
      );
      out.checks.vector_db = {
        status: 'ok',
        embeddings: Number(r.rows[0].n),
        pipeline_state: stateRow.rows[0] || { id: 'main', products_embedded: 0, started_at: null },
        model: COHERE_MODEL,
      };
    } catch (e) {
      out.checks.vector_db = { status: 'fail', error: e.message };
      healthy = false;
    }

    // Check pg-boss state
    try {
      const q = await db.query(
        "SELECT state, count(*)::int AS n FROM pgboss.job WHERE name = 'embed.products' GROUP BY state"
      );
      const states = {};
      for (const row of q.rows) states[row.state] = row.n;
      out.checks.pg_boss = { status: 'ok', embed_products_states: states };
    } catch (e) {
      out.checks.pg_boss = { status: 'fail', error: e.message };
      // not fatal — pg-boss state query is informational
    }

    out.status = healthy ? 'healthy' : 'degraded';
    res.status(healthy ? 200 : 503).json(out);
  });

  app.listen(embedHealthPort, () => {
    console.log(`[embed] health server listening on :${embedHealthPort} (/healthz, /health)`);
  });
}).catch((e) => {
  console.error('[embed] failed to start health server:', e.message);
});

process.on('SIGTERM', async () => {
  console.log('[embed] shutting down...');
  await pgBoss.stop();
  await db.end();
  await vectorDb.end();
  process.exit(0);
});
