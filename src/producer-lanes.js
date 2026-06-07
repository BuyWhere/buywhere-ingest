// BUY-34838: Lane runner producer.
//
// One-shot CLI / Railway scheduled job that reads the lane candidate feed
// and enqueues one `scrape.shopify.lane.<role>` job per (role, domain)
// pair, with role-specific maxPages / pageDelayMs / qualityMode config
// in the payload.
//
// The candidate feed is read from EITHER:
//   1. The `lane_feed` table (canonical DB), populated by an external
//      feed-sync (Hex's writer, BUY-33668). This is the preferred path.
//   2. The `LANE_FEED_R2_URL` env (or `LANE_FEED_FILE_PATH` for local
//      testing) — a JSONL of `{ domain, platform, products, ts, ... }`.
//      The producer imports any new domains into `lane_feed` and
//      enqueues from there.
//
// Singleton dedupe is per-(role, domain) within LANE_SINGLETON_HOURS
// (default 22h, capped under 24h to satisfy pg-boss's strict-less-than
// `expireInHours/60/60 < 24` rule). The worker's per-(role, domain)
// checkpoint in `lane_processed` is the second line of defense for
// candidates that slipped through the singleton window.
//
// Mirrors producer.js (Shopify) and producer-woocommerce.js: same
// summary log, same pgBoss stop/finally teardown, so the buywhere-ingest
// scheduled entry that runs this is a drop-in alongside the existing
// producers.

import dotenv from 'dotenv';
import PgBoss from 'pg-boss';
import pg from 'pg';
import fs from 'fs';
import { LANE_ROLES, LANE_ROLE_CONFIG } from './laneRunner.js';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

// pg-boss asserts expireInHours/60/60 < 24 (strict-less-than). With
// expireInHours = SINGLETON_HOURS + 1, the safe max for SINGLETON_HOURS
// is 22. We default to 22 to give a 22-hour dedupe window — covers the
// producer's repeat tick with a small margin.
const SINGLETON_HOURS = Math.max(1, Math.min(22, parseInt(process.env.LANE_SINGLETON_HOURS || '22', 10)));
const BATCH_LIMIT = parseInt(process.env.LANE_PRODUCER_BATCH_LIMIT || '500', 10);
const MAX_DOMAINS = parseInt(process.env.LANE_PRODUCER_MAX_DOMAINS || '0', 10);
const QUEUE_PREFIX = 'scrape.shopify.lane.';
const ROLES = LANE_ROLES.filter((r) => LANE_ROLE_CONFIG[r]);
const R2_URL = process.env.LANE_FEED_R2_URL || '';
const FILE_PATH = process.env.LANE_FEED_FILE_PATH || '';

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
  feedSource: null,
  feedRowsImported: 0,
  candidatesFound: 0,
  enqueued: 0,
  skippedSingleton: 0,
  skippedRole: 0,
  skippedError: 0,
  errors: [],
};

async function ensureLaneTables() {
  // `lane_feed` is the canonical candidate pool (one row per domain).
  // The producer reads from it. The worker's per-(role, domain)
  // checkpoint is in `lane_processed`, written by the worker after
  // each job completes. We don't store products here — the worker's
  // outcome (accepted/rejected) and the ingestion_runs row give the
  // operator everything they need.
  await db.query(`
    CREATE TABLE IF NOT EXISTS lane_feed (
      domain TEXT PRIMARY KEY,
      platform TEXT,
      products_hint INTEGER,
      ts TIMESTAMPTZ,
      source TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);
  await db.query(`
    CREATE INDEX IF NOT EXISTS lane_feed_created_at_idx ON lane_feed (created_at);
  `);
  await db.query(`
    CREATE TABLE IF NOT EXISTS lane_processed (
      role TEXT NOT NULL,
      domain TEXT NOT NULL,
      status TEXT NOT NULL,
      rows_inserted INTEGER NOT NULL DEFAULT 0,
      last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (role, domain)
    );
  `);
}

async function importFromJsonl(jsonlText) {
  let imported = 0;
  let skipped = 0;
  for (const raw of jsonlText.split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    let entry;
    try { entry = JSON.parse(line); } catch { skipped += 1; continue; }
    const domain = String(entry.domain || entry.host || entry.url || '')
      .trim().toLowerCase()
      .replace(/^https?:\/\//, '')
      .replace(/\/$/, '');
    if (!domain || !domain.includes('.')) { skipped += 1; continue; }
    const platform = entry.platform || entry.source || 'unknown';
    const productsHint = Number(entry.products) || 0;
    const ts = entry.ts || entry.discovered_at || entry.checked_at || null;
    try {
      await db.query(
        `INSERT INTO lane_feed (domain, platform, products_hint, ts, source)
         VALUES ($1, $2, $3, $4, $5)
         ON CONFLICT (domain) DO UPDATE
           SET platform = COALESCE(EXCLUDED.platform, lane_feed.platform),
               products_hint = GREATEST(COALESCE(lane_feed.products_hint, 0), EXCLUDED.products_hint),
               ts = COALESCE(EXCLUDED.ts, lane_feed.ts)`,
        [domain, platform, productsHint, ts, entry.source || null]
      );
      imported += 1;
    } catch (err) {
      // Unique violation on PK is impossible (ON CONFLICT). Anything
      // else is logged but doesn't fail the import.
      console.warn(`[lanes-producer] import row failed for ${domain}: ${err.message}`);
      skipped += 1;
    }
  }
  return { imported, skipped };
}

async function syncFeed() {
  // External feed paths (R2 URL or local file) take precedence on
  // each producer tick so the worker can pick up newly-imported
  // candidates without waiting for a separate sync job.
  if (R2_URL) {
    summary.feedSource = `r2:${R2_URL}`;
    console.log(`[lanes-producer] fetching feed from R2 URL: ${R2_URL}`);
    try {
      const res = await fetch(R2_URL, { signal: AbortSignal.timeout(parseInt(process.env.LANE_FEED_FETCH_TIMEOUT_MS || '60000', 10)) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const text = await res.text();
      const { imported, skipped } = await importFromJsonl(text);
      summary.feedRowsImported = imported;
      console.log(`[lanes-producer] R2 import done: imported=${imported} skipped=${skipped}`);
    } catch (err) {
      console.error(`[lanes-producer] R2 fetch/import failed: ${err.message}`);
      summary.errors.push(`r2_import:${err.message}`);
    }
  } else if (FILE_PATH && fs.existsSync(FILE_PATH)) {
    summary.feedSource = `file:${FILE_PATH}`;
    console.log(`[lanes-producer] reading local feed file: ${FILE_PATH}`);
    const text = fs.readFileSync(FILE_PATH, 'utf8');
    const { imported, skipped } = await importFromJsonl(text);
    summary.feedRowsImported = imported;
    console.log(`[lanes-producer] file import done: imported=${imported} skipped=${skipped}`);
  } else {
    summary.feedSource = 'db:lane_feed';
    console.log(`[lanes-producer] no R2/file configured; using existing lane_feed table`);
  }
}

async function loadUnprocessedCandidates(limit) {
  // Pull domains from lane_feed that haven't been processed for any
  // role in the last LANE_SKIP_DONE_HOURS (default 6h). This keeps the
  // producer cheap on repeat ticks (it skips everything Hex's writer
  // already drained). Hex can override this with LANE_FORCE_REPROCESS=1
  // for backfill scenarios.
  const skipDoneHours = parseInt(process.env.LANE_SKIP_DONE_HOURS || '6', 10);
  const force = process.env.LANE_FORCE_REPROCESS === '1';
  const result = await db.query(
    `SELECT f.domain, f.platform, f.products_hint
       FROM lane_feed f
       ${force ? '' : `
       WHERE NOT EXISTS (
         SELECT 1 FROM lane_processed p
          WHERE p.domain = f.domain
            AND p.status = 'accepted'
            AND p.last_seen_at > NOW() - ($1 || ' hours')::interval
       )`}
      ORDER BY f.created_at ASC
      LIMIT $${force ? 1 : 2}`,
    force ? [limit] : [String(skipDoneHours), limit]
  );
  return result.rows;
}

async function enqueueLaneJobs(candidates) {
  for (const cand of candidates) {
    const domain = cand.domain;
    if (!domain || typeof domain !== 'string' || !domain.includes('.')) {
      console.warn(`[lanes-producer] skipping invalid domain=${domain}`);
      summary.skippedError += 1;
      continue;
    }
    for (const role of ROLES) {
      const cfg = LANE_ROLE_CONFIG[role];
      const payload = {
        domain,
        role,
        platform: cand.platform,
        maxPages: cfg.maxPages,
        pageDelayMs: cfg.pageDelayMs,
        maxRetries: cfg.maxRetries,
        retryDelayMs: cfg.retryDelayMs,
        qualityMode: cfg.qualityMode,
        fetchTimeoutMs: cfg.fetchTimeoutMs,
        enqueuedAt: new Date().toISOString(),
      };
      try {
        const jobId = await pgBoss.send(`${QUEUE_PREFIX}${role}`, payload, {
          singletonKey: `${role}:${domain}`,
          singletonHours: SINGLETON_HOURS,
          retryLimit: 2,
          expireInHours: SINGLETON_HOURS + 1,
        });
        if (jobId) summary.enqueued += 1;
        else summary.skippedSingleton += 1;
      } catch (err) {
        const msg = String(err?.message || err);
        if (/singleton/i.test(msg) || /already.*active/i.test(msg)) {
          summary.skippedSingleton += 1;
        } else {
          console.warn(`[lanes-producer] enqueue ${role} for ${domain} failed: ${msg}`);
          summary.errors.push(`enqueue_${role}_${domain}:${msg}`);
          summary.skippedError += 1;
        }
      }
    }
  }
}

async function main() {
  console.log(`[lanes-producer] starting singletonHours=${SINGLETON_HOURS} batchLimit=${BATCH_LIMIT} roles=${ROLES.join(',')}`);
  await ensureLaneTables();
  await syncFeed();

  const limit = MAX_DOMAINS > 0 ? Math.min(BATCH_LIMIT, MAX_DOMAINS) : BATCH_LIMIT;
  const candidates = await loadUnprocessedCandidates(limit);
  summary.candidatesFound = candidates.length;
  console.log(`[lanes-producer] ${candidates.length} candidates (limit=${limit})`);

  if (candidates.length > 0) {
    await enqueueLaneJobs(candidates);
  }

  summary.finishedAt = new Date().toISOString();
  console.log('[lanes-producer] summary', JSON.stringify(summary, null, 2));
}

try {
  await pgBoss.start();
  await main();
} catch (err) {
  console.error('[lanes-producer] fatal:', err);
  summary.errors.push(`fatal:${err.message}`);
  process.exitCode = 1;
} finally {
  try { await pgBoss.stop({ graceful: true, wait: true }); } catch {}
  try { await db.end(); } catch {}
  console.log('[lanes-producer] done');
}
