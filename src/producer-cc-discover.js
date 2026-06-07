// BUY-34835: Common Crawl Shopify discovery — daily producer.
//
// One-shot CLI / Railway scheduled job that reads a candidate list
// (bundled WAT pool snapshot, or a URL via CC_CANDIDATE_LIST_URL), filters
// out domains already in the `merchants` table, and enqueues one
// `discover.cc` job per segment of N candidates (default 1000).
//
// Mirrors the structure of producer.js (Shopify) and producer-woocommerce.js:
// same singleton-dedupe shape, same summary log, same pgBoss stop+finally
// teardown so the railway.json `scheduled` entry that runs this is a
// drop-in alongside the existing producers.
//
// The singleton key is `discover.cc:<kind>:<segmentStart>` so re-running
// the producer within DISCOVER_SINGLETON_HOURS (default 24h) is a no-op
// for segments that already have a pending or recently-completed job.

import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';
import { loadCandidateList, isProbeableDomain } from './ccDiscover.js';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

const QUEUE_NAME = 'discover.cc';
const KIND = (process.env.CC_DISCOVER_KIND || 'wat').toLowerCase() === 'index' ? 'index' : 'wat';
const SEGMENT_SIZE = parseInt(process.env.DISCOVER_SEGMENT_SIZE || '1000', 10);
// pg-boss asserts expireInHours/60/60 < 24 (strict-less-than). With
// expireInHours = SINGLETON_HOURS + 1, the safe max for SINGLETON_HOURS
// is 22 (so expireInHours=23). We default to 22, which gives a 22-hour
// dedupe window — covers the daily cron with a small margin. The worker's
// "skip if already in merchants" check is the second line of defense for
// the case where the singleton window has expired.
const SINGLETON_HOURS = Math.max(1, Math.min(22, parseInt(process.env.DISCOVER_SINGLETON_HOURS || '22', 10)));
const CANDIDATE_LIST =
  process.env.CC_CANDIDATE_LIST_URL ||
  process.env.DISCOVER_CANDIDATE_LIST_PATH ||
  'data/wat-pool.jsonl';
const COUNTRY_FILTER = (process.env.CC_DISCOVER_COUNTRY || '').split(',').map((s) => s.trim()).filter(Boolean);
// Optional cap so the producer can be tuned for a slow first run (e.g.
// CC_DISCOVER_MAX_SEGMENTS=5 to limit to 5,000 candidates on day 1).
const MAX_SEGMENTS = parseInt(process.env.CC_DISCOVER_MAX_SEGMENTS || '0', 10);

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
  kind: KIND,
  candidateList: CANDIDATE_LIST,
  segmentSize: SEGMENT_SIZE,
  totalCandidates: 0,
  totalSegments: 0,
  alreadyKnown: 0,
  enqueued: 0,
  skippedSingleton: 0,
  skippedError: 0,
  errors: [],
};

async function findAlreadyKnownMerchants(domains) {
  if (!domains.length) return new Set();
  // Chunk to keep query plan simple — 5000 / round-trip is a fine
  // tradeoff for the producer that runs once per day.
  const CHUNK = 5000;
  const known = new Set();
  for (let i = 0; i < domains.length; i += CHUNK) {
    const slice = domains.slice(i, i + CHUNK);
    const r = await db.query(
      `SELECT id FROM merchants WHERE id = ANY($1::text[])`,
      [slice]
    );
    for (const row of r.rows) known.add(row.id);
  }
  return known;
}

async function enqueueDiscoverJobs({ kind, candidateList, totalCandidates, knownSet, segmentsToEmit }) {
  let enqueued = 0;
  let skippedSingleton = 0;
  let skippedError = 0;
  const errors = [];

  for (const segIdx of segmentsToEmit) {
    const segmentStart = segIdx * SEGMENT_SIZE;
    const segmentEnd = Math.min(totalCandidates, segmentStart + SEGMENT_SIZE);
    if (segmentStart >= totalCandidates) break;
    const singletonKey = `discover.cc:${kind}:${segIdx}`;

    try {
      const jobId = await pgBoss.send(QUEUE_NAME, {
        kind,
        segmentStart,
        segmentEnd,
        candidateList,
        enqueuedAt: new Date().toISOString(),
        enqueuedBySegment: segIdx,
      }, {
        singletonKey,
        singletonHours: SINGLETON_HOURS,
        retryLimit: 1,
        expireInHours: SINGLETON_HOURS + 1,
      });
      enqueued++;
      console.log(`[cc-producer] Enqueued ${QUEUE_NAME} job ${jobId || '<accepted>'} for kind=${kind} segment ${segmentStart}-${segmentEnd} (singleton=${singletonKey})`);
    } catch (err) {
      const msg = String((err && err.message) || err);
      if (/singleton/i.test(msg) || /already.*active/i.test(msg)) {
        skippedSingleton++;
        console.log(`[cc-producer] Skipped segment ${segmentStart}-${segmentEnd} (singleton dedupe, retry within ${SINGLETON_HOURS}h)`);
      } else {
        skippedError++;
        errors.push({ segment: segIdx, error: msg });
        console.error(`[cc-producer] Failed to enqueue segment ${segmentStart}-${segmentEnd}:`, msg);
      }
    }
  }

  return { enqueued, skippedSingleton, skippedError, errors };
}

async function main() {
  console.log('[cc-producer] Starting Common Crawl Shopify discovery producer...');
  console.log(`[cc-producer] config: KIND=${KIND} CANDIDATE_LIST=${CANDIDATE_LIST} SEGMENT_SIZE=${SEGMENT_SIZE} SINGLETON_HOURS=${SINGLETON_HOURS} COUNTRY_FILTER=${COUNTRY_FILTER.join(',') || '<n/a>'}`);

  await pgBoss.start();
  console.log('[cc-producer] pgboss started (schema bootstrapped if needed)');

  const candidates = await loadCandidateList(CANDIDATE_LIST);
  summary.totalCandidates = candidates.length;
  console.log(`[cc-producer] Loaded ${candidates.length} candidates from ${CANDIDATE_LIST}`);

  if (candidates.length === 0) {
    console.log('[cc-producer] No candidates loaded, exiting cleanly');
    return;
  }

  // Drop domains that don't look probeable — the loader already enforces
  // isProbeableDomain, so this is a belt-and-suspenders filter.
  const probeable = candidates.filter((c) => isProbeableDomain(c.domain));
  const allDomains = probeable.map((c) => c.domain);
  const knownSet = await findAlreadyKnownMerchants(allDomains);
  summary.alreadyKnown = knownSet.size;
  console.log(`[cc-producer] ${allDomains.length} probeable candidates, ${knownSet.size} already in merchants table`);

  // The WAT pool is a flat list — we don't have a per-segment "is this
  // segment fully known" check, so we always emit ALL segments. The
  // worker is the one that short-circuits when an entire segment is in
  // the known set, so re-enqueuing is cheap (the worker queries
  // merchants before probing).
  const totalSegments = Math.ceil(probeable.length / SEGMENT_SIZE);
  summary.totalSegments = totalSegments;

  let segmentsToEmit = [];
  for (let i = 0; i < totalSegments; i++) {
    if (MAX_SEGMENTS > 0 && segmentsToEmit.length >= MAX_SEGMENTS) break;
    segmentsToEmit.push(i);
  }
  console.log(`[cc-producer] Emitting ${segmentsToEmit.length} of ${totalSegments} segments (MAX_SEGMENTS=${MAX_SEGMENTS || 'unbounded'})`);

  if (segmentsToEmit.length === 0) {
    console.log('[cc-producer] No segments to enqueue, exiting cleanly');
    return;
  }

  const result = await enqueueDiscoverJobs({
    kind: KIND,
    candidateList: CANDIDATE_LIST,
    totalCandidates: probeable.length,
    knownSet,
    segmentsToEmit,
  });

  summary.enqueued = result.enqueued;
  summary.skippedSingleton = result.skippedSingleton;
  summary.skippedError = result.skippedError;
  summary.errors = result.errors;
  console.log(`[cc-producer] Enqueued ${result.enqueued} jobs; ${result.skippedSingleton} skipped by singleton dedupe; ${result.skippedError} invalid; ${result.errors.length} errors`);
}

main()
  .then(async () => {
    summary.finishedAt = new Date().toISOString();
    console.log('[cc-producer] summary:', JSON.stringify(summary, null, 2));
  })
  .catch(async (err) => {
    console.error('[cc-producer] Fatal error:', err);
    summary.errors.push({ fatal: String((err && err.message) || err) });
    summary.finishedAt = new Date().toISOString();
    console.log('[cc-producer] summary:', JSON.stringify(summary, null, 2));
    process.exitCode = 1;
  })
  .finally(async () => {
    try { await pgBoss.stop(); } catch {}
    try { await db.end(); } catch {}
  });
