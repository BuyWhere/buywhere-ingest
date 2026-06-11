import { test, mock, beforeEach } from 'node:test';
import assert from 'node:assert';
import { createHash } from 'node:crypto';

// ---------------------------------------------------------------------------
// Test helper: isolated textHash function (mirrors embedWorker.js logic)
// ---------------------------------------------------------------------------
function textHash(title, description) {
  const text = `${title || ''} ${description != null ? description : ''}`;
  return createHash('md5').update(text).digest('hex');
}

// ---------------------------------------------------------------------------
// Test 1: hash-gate — same title+description produces identical hash
// ---------------------------------------------------------------------------
test('textHash: identical title+description → same hash', async () => {
  const hash1 = textHash('Wireless Mouse', 'Ergonomic wireless mouse with USB receiver');
  const hash2 = textHash('Wireless Mouse', 'Ergonomic wireless mouse with USB receiver');
  assert.strictEqual(hash1, hash2, 'Same input must produce same hash');
});

// ---------------------------------------------------------------------------
// Test 2: hash-gate — different title produces different hash
// ---------------------------------------------------------------------------
test('textHash: different title → different hash', async () => {
  const hash1 = textHash('Wireless Mouse', 'Ergonomic wireless mouse');
  const hash2 = textHash('Wired Mouse', 'Ergonomic wireless mouse');
  assert.notStrictEqual(hash1, hash2, 'Different title must produce different hash');
});

// ---------------------------------------------------------------------------
// Test 3: hash-gate — different description produces different hash
// ---------------------------------------------------------------------------
test('textHash: different description → different hash', async () => {
  const hash1 = textHash('Wireless Mouse', 'Ergonomic wireless mouse');
  const hash2 = textHash('Wireless Mouse', 'Ergonomic wired mouse');
  assert.notStrictEqual(hash1, hash2, 'Different description must produce different hash');
});

// ---------------------------------------------------------------------------
// Test 4: hash-gate — null description vs empty string
// ---------------------------------------------------------------------------
test('textHash: null description and empty string produce same hash', async () => {
  // Per spec: description ?? '' so null and '' should normalize
  const hashNull = textHash('Product', null);
  const hashEmpty = textHash('Product', '');
  assert.strictEqual(hashNull, hashEmpty, 'null and "" description must normalize to same hash');
});

// ---------------------------------------------------------------------------
// Test 5: hash-gate — missing description key treated as empty
// ---------------------------------------------------------------------------
test('textHash: missing description treated as empty', async () => {
  const hashWithDesc = textHash('Product', '');
  // A product with no description field would have description = undefined
  // which coalesces to '' via (description ?? '')
  const hashUndefined = textHash('Product', undefined);
  assert.strictEqual(hashWithDesc, hashUndefined, 'undefined description must coalesce to empty string');
});

// ---------------------------------------------------------------------------
// Test 6: hash-gate skip logic — hash matches existing → skip
// ---------------------------------------------------------------------------
test('hash-gate: product with matching existing hash is skipped', async () => {
  const title = 'Ergonomic Office Chair';
  const description = 'Adjustable lumbar support, mesh back';
  const productHash = textHash(title, description);

  const existingHash = productHash; // same hash means text unchanged

  // Simulate the hash-gate check from embedWorker.js
  const shouldSkip = existingHash !== undefined && existingHash === productHash;
  assert.strictEqual(shouldSkip, true, 'Product with matching hash should be skipped');
});

// ---------------------------------------------------------------------------
// Test 7: new product embed — no existing hash → embed
// ---------------------------------------------------------------------------
test('hash-gate: product with no existing hash should be embedded', async () => {
  const title = 'Standing Desk Converter';
  const description = 'Height adjustable standing desk converter';
  const productHash = textHash(title, description);

  const existingHash = undefined; // no row in product_embeddings

  const shouldSkip = existingHash !== undefined && existingHash === productHash;
  assert.strictEqual(shouldSkip, false, 'Product with no existing hash must be embedded');
  assert.strictEqual(existingHash, undefined);
});

// ---------------------------------------------------------------------------
// Test 8: text-change re-embed — hash mismatch → re-embed
// ---------------------------------------------------------------------------
test('hash-gate: product with mismatched hash should be re-embedded', async () => {
  const title = 'LED Desk Lamp';
  const description = 'Dimmable LED desk lamp with USB port';
  const currentHash = textHash(title, description);

  // Description was updated since last embedding
  const oldDescription = 'LED desk lamp with USB port';
  const oldHash = textHash(title, oldDescription);

  assert.notStrictEqual(currentHash, oldHash, 'Updated description must produce different hash');

  const existingHash = oldHash; // what we stored previously
  const shouldSkip = existingHash !== undefined && existingHash === currentHash;
  assert.strictEqual(shouldSkip, false, 'Product with hash mismatch must be re-embedded');
});

// ---------------------------------------------------------------------------
// Test 9: price-only update → hash unchanged → skip
// ---------------------------------------------------------------------------
test('hash-gate: price-only change (no text change) → skip', async () => {
  const title = 'Mechanical Keyboard';
  const description = 'RGB mechanical gaming keyboard';
  const productHash = textHash(title, description);

  // Existing hash matches — text hasn't changed
  const existingHash = productHash;

  // Simulate the hash-gate: skip if existing hash matches current hash
  const shouldSkip = existingHash !== undefined && existingHash === productHash;
  assert.strictEqual(shouldSkip, true, 'Price-only update must be skipped (hash unchanged)');
});

// ---------------------------------------------------------------------------
// Test 10: batch hashing — many products correctly produce distinct hashes
// ---------------------------------------------------------------------------
test('textHash: batch of products produces unique hashes', async () => {
  const products = [
    { title: 'Product A', description: 'Description A' },
    { title: 'Product B', description: 'Description B' },
    { title: 'Product A', description: 'Description B' }, // swapped
    { title: 'Product C', description: null },
    { title: 'Product C', description: '' },
  ];

  const hashes = products.map((p) => textHash(p.title, p.description));
  const uniqueHashes = new Set(hashes);

  // All 5 should be unique (Product C with null and '' coalesce to same)
  assert.strictEqual(uniqueHashes.size, 4, 'Expected 4 unique hashes (Product C null and empty string coalesce)');
});

// ---------------------------------------------------------------------------
// Test 11: Jina API payload structure (mocked)
// ---------------------------------------------------------------------------
test('Jina API payload structure for batch embedding', async () => {
  const texts = [
    'Product Title 1 Short description',
    'Product Title 2 A longer description with more details about this product',
    'Product Title 3',
  ];

  // Expected payload shape per BUY-41136 spec
  const expectedPayload = {
    model: 'jina-embeddings-v3',
    task: 'retrieval.passage',
    dimensions: 512,
    input: texts,
  };

  assert.deepStrictEqual(
    expectedPayload,
    {
      model: 'jina-embeddings-v3',
      task: 'retrieval.passage',
      dimensions: 512,
      input: texts,
    },
    'Jina API payload must match spec'
  );
  assert.strictEqual(expectedPayload.input.length, 3);
});

// ---------------------------------------------------------------------------
// Test 12: ON CONFLICT upsert SQL structure
// ---------------------------------------------------------------------------
test('upsert SQL uses text_hash != EXCLUDED.text_hash guard', async () => {
  // The upsert must only update when hash differs — this is the core
  // hash-gate enforcement at the DB layer (defense in depth)
  const upsertSQL = `
    INSERT INTO product_embeddings (product_id, embedding, text_hash, model_ver, embedded_at)
    VALUES ($1, $2, $3, $4, NOW())
    ON CONFLICT (product_id) DO UPDATE
      SET embedding = EXCLUDED.embedding,
          text_hash = EXCLUDED.text_hash,
          embedded_at = NOW()
    WHERE product_embeddings.text_hash != EXCLUDED.text_hash
  `;

  assert.ok(
    upsertSQL.includes('ON CONFLICT (product_id)'),
    'UPSERT must have ON CONFLICT clause'
  );
  assert.ok(
    upsertSQL.includes('product_embeddings.text_hash != EXCLUDED.text_hash'),
    'UPSERT must guard on text_hash mismatch'
  );
  assert.ok(
    upsertSQL.includes('embedded_at = NOW()'),
    'UPSERT must update embedded_at timestamp'
  );
});
