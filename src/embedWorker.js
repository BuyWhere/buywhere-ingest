import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';
import crypto from 'crypto';
import https from 'https';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
const vectorDbUrl = process.env.VECTOR_DB_URL || catalogDbUrl; // fallback to catalog DB if no separate vector DB
const jinaApiKey = process.env.JINA_API_KEY;

if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}
if (!jinaApiKey) {
  throw new Error('Missing JINA_API_KEY environment variable.');
}

const EMBED_QUEUE = 'embed.products';
const BATCH_SIZE = 100;
const JINA_MODEL = 'jina-embeddings-v3';
const JINA_TASK = 'retrieval.passage';
const JINA_DIMENSIONS = 512;
const JINA_API_URL = 'https://api.jina.ai/v1/embeddings';
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
// Hash-gate: compute md5(title + ' ' + (description ?? ''))
// ---------------------------------------------------------------------------
function textHash(title, description) {
  const text = `${title || ''} ${description != null ? description : ''}`;
  return crypto.createHash('md5').update(text).digest('hex');
}

// ---------------------------------------------------------------------------
// Jina API call with exponential backoff retry
// ---------------------------------------------------------------------------
async function embedWithJina(texts, attempt = 1) {
  const response = await fetch(JINA_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${jinaApiKey}`,
    },
    body: JSON.stringify({
      model: JINA_MODEL,
      task: JINA_TASK,
      dimensions: JINA_DIMENSIONS,
      input: texts,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    const err = new Error(`Jina API returned ${response.status}: ${errorText}`);
    if (attempt < MAX_RETRIES) {
      const delay = Math.min(1000 * 2 ** (attempt - 1), 10000);
      console.warn(`[embed] Jina API error (attempt ${attempt}/${MAX_RETRIES}), retrying in ${delay}ms: ${err.message}`);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return embedWithJina(texts, attempt + 1);
    }
    throw err;
  }

  const data = await response.json();
  return data.data; // array of { index, embedding: number[] }
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
        `INSERT INTO product_embeddings (product_id, embedding, text_hash, model_ver, embedded_at)
         VALUES ($1, $2, $3, $4, NOW())
         ON CONFLICT (product_id) DO UPDATE
           SET embedding = EXCLUDED.embedding,
               text_hash = EXCLUDED.text_hash,
               embedded_at = NOW()
         WHERE product_embeddings.text_hash != EXCLUDED.text_hash`,
        [rec.product_id, rec.embedding, rec.text_hash, JINA_MODEL]
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
    const existingRows = await db.query(
      `SELECT product_id, text_hash FROM product_embeddings WHERE product_id = ANY($1::bigint[])`,
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

    // 2. Batch and call Jina API
    const texts = toEmbed.map((p) => `${p.title || ''} ${p.description != null ? p.description : ''}`.trim());
    const embeddings = await embedWithJina(texts);

    if (!embeddings || embeddings.length === 0) {
      throw new Error('Jina API returned empty embeddings array');
    }

    // 3. Build records and upsert to vector DB
    const embeddingMap = new Map(embeddings.map((e) => [e.index, e.embedding]));
    const records = [];

    for (let i = 0; i < toEmbed.length; i++) {
      const product = toEmbed[i];
      const embedding = embeddingMap.get(i);
      if (!embedding) {
        console.warn(`[embed] no embedding for product ${product.id} at index ${i}, skipping`);
        continue;
      }
      records.push({
        product_id: product.id,
        embedding: JSON.stringify(embedding),
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

process.on('SIGTERM', async () => {
  console.log('[embed] shutting down...');
  await pgBoss.stop();
  await db.end();
  await vectorDb.end();
  process.exit(0);
});
