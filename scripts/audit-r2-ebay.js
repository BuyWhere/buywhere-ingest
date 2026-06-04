/**
 * audit-r2-ebay.js — Checkpoint B gate runner for eBay US R2 batches.
 *
 * Streams each configured R2 key through checkpointB.auditBatch() and
 * prints a summary table.  Exits 1 if any file fails.
 *
 * Usage:
 *   node scripts/audit-r2-ebay.js [r2-key ...]
 *
 * If no keys are supplied, audits the known eBay US batch files.
 *
 * Required env vars:
 *   CLOUDFLARE_R2_ACCOUNT_ID
 *   CLOUDFLARE_R2_ACCESS_KEY_ID
 *   CLOUDFLARE_R2_SECRET_ACCESS_KEY
 *   CLOUDFLARE_R2_BUCKET  (falls back to 'buywhere-data')
 */

import { createHmac, createHash } from 'crypto';
import { createInterface } from 'readline';
import { Readable } from 'stream';
import dotenv from 'dotenv';
import { auditBatch, ZERO_PRICE_MAX_PCT, NULL_IMAGE_MAX_PCT, PLACEHOLDER_TITLE_MAX_PCT } from '../src/checkpointB.js';

dotenv.config();

const ACCOUNT_ID = process.env.CLOUDFLARE_R2_ACCOUNT_ID;
const ACCESS_KEY = process.env.CLOUDFLARE_R2_ACCESS_KEY_ID;
const SECRET_KEY = process.env.CLOUDFLARE_R2_SECRET_ACCESS_KEY;
// BUY-30354: env var has wrong casing 'Buywhere-data'; canonical bucket is all-lowercase.
const BUCKET = (process.env.CLOUDFLARE_R2_BUCKET || 'Buywhere-data').toLowerCase();
const ENDPOINT = `https://${ACCOUNT_ID}.r2.cloudflarestorage.com`;

if (!ACCOUNT_ID || !ACCESS_KEY || !SECRET_KEY) {
  console.error('Missing R2 credentials. Set CLOUDFLARE_R2_ACCOUNT_ID, CLOUDFLARE_R2_ACCESS_KEY_ID, CLOUDFLARE_R2_SECRET_ACCESS_KEY.');
  process.exit(1);
}

const KNOWN_EBAY_KEYS = [
  'scraping/ebay_us/products_20260427_134621.jsonl',
  'scraping/ebay_us/products_20260427_134638.jsonl',
  'ebay_us_20260427.ndjson',
  'ebay_us_20260428.ndjson',
  'ebay_us_20260502.jsonl',
  'ebay_us_20260502.ndjson',
  'ebay_us_20260502_full.jsonl',
];

// ── AWS Signature V4 helpers ────────────────────────────────────────────────

function hmac(key, data) {
  return createHmac('sha256', key).update(data, 'utf8').digest();
}

function sha256hex(data) {
  return createHash('sha256').update(data).digest('hex');
}

function signingKey(secret, date, region, service) {
  const kDate = hmac(`AWS4${secret}`, date);
  const kRegion = hmac(kDate, region);
  const kService = hmac(kRegion, service);
  return hmac(kService, 'aws4_request');
}

/**
 * Build a presigned GET URL for an R2 object (valid 300s).
 */
function presignR2Get(key, expiresSeconds = 300) {
  const now = new Date();
  const amzDate = now.toISOString().replace(/[:\-]|\.\d{3}/g, '').slice(0, 15) + 'Z';
  const dateStr = amzDate.slice(0, 8);
  const region = 'auto';
  const service = 's3';
  const host = `${ACCOUNT_ID}.r2.cloudflarestorage.com`;

  const credentialScope = `${dateStr}/${region}/${service}/aws4_request`;
  const credential = `${ACCESS_KEY}/${credentialScope}`;

  const qs = new URLSearchParams([
    ['X-Amz-Algorithm', 'AWS4-HMAC-SHA256'],
    ['X-Amz-Credential', credential],
    ['X-Amz-Date', amzDate],
    ['X-Amz-Expires', String(expiresSeconds)],
    ['X-Amz-SignedHeaders', 'host'],
  ]);

  const canonicalRequest = [
    'GET',
    `/${BUCKET}/${key}`,
    qs.toString(),
    `host:${host}\n`,
    'host',
    'UNSIGNED-PAYLOAD',
  ].join('\n');

  const stringToSign = [
    'AWS4-HMAC-SHA256',
    amzDate,
    credentialScope,
    sha256hex(canonicalRequest),
  ].join('\n');

  const signature = createHmac('sha256', signingKey(SECRET_KEY, dateStr, region, service))
    .update(stringToSign)
    .digest('hex');

  return `${ENDPOINT}/${BUCKET}/${key}?${qs}&X-Amz-Signature=${signature}`;
}

// ── Stream helpers ──────────────────────────────────────────────────────────

async function* fetchLines(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} fetching R2 object: ${await res.text()}`);
  }
  // Node.js 22 fetch body is a Web ReadableStream; convert for readline
  const nodeStream = Readable.fromWeb(res.body);
  const rl = createInterface({ input: nodeStream, crlfDelay: Infinity });
  yield* rl;
}

// ── Main ────────────────────────────────────────────────────────────────────

const keys = process.argv.slice(2).length > 0 ? process.argv.slice(2) : KNOWN_EBAY_KEYS;

console.log(`Checkpoint B — thresholds: zero_price>${ZERO_PRICE_MAX_PCT}%, null_image>${NULL_IMAGE_MAX_PCT}%, placeholder_title>${PLACEHOLDER_TITLE_MAX_PCT}%`);
console.log(`Bucket: ${BUCKET}  (${keys.length} file(s) to audit)\n`);

const rows = [];
let anyFail = false;

for (const key of keys) {
  process.stdout.write(`Auditing ${key} ... `);
  try {
    const url = presignR2Get(key);
    const result = await auditBatch(fetchLines(url), key);
    const verdict = result.pass ? 'PASS' : 'BLOCKED';
    if (!result.pass) anyFail = true;
    console.log(verdict);
    rows.push({ key, ...result.metrics, pass: result.pass, violations: result.violations });
  } catch (err) {
    console.log(`ERROR: ${err.message}`);
    anyFail = true;
    rows.push({ key, pass: false, violations: [err.message] });
  }
}

console.log('\n─── Summary ───────────────────────────────────────────────────────────────────');
console.log('key | rows | zero_price% | null_image% | placeholder_title% | verdict');
console.log('────────────────────────────────────────────────────────────────────────────────');
for (const r of rows) {
  const zp = r.zeroPricePct != null ? r.zeroPricePct.toFixed(1) + '%' : 'n/a';
  const ni = r.nullImagePct != null ? r.nullImagePct.toFixed(1) + '%' : 'n/a';
  const pt = r.placeholderTitlePct != null ? r.placeholderTitlePct.toFixed(1) + '%' : 'n/a';
  const verdict = r.pass ? 'PASS' : 'BLOCKED';
  console.log(`${r.key.split('/').pop()} | ${r.total ?? '?'} | ${zp} | ${ni} | ${pt} | ${verdict}`);
  if (r.violations?.length) {
    for (const v of r.violations) console.log(`  ⚠ ${v}`);
  }
}

console.log('────────────────────────────────────────────────────────────────────────────────');
console.log(anyFail
  ? '\nCheckpoint B: BLOCKED — do NOT proceed with INSERT until violations are resolved.'
  : '\nCheckpoint B: ALL PASS — safe to proceed with INSERT.'
);

process.exit(anyFail ? 1 : 0);
