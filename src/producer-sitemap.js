// BUY-34837: Sitemap-driven merchant discovery producer.
//
// One-shot CLI / Railway scheduled job that reads the hand-curated
// brand and retailer seed lists (data/brands.json, data/retailers.json),
// validates each entry, and enqueues one `discover.sitemap` job per
// (domain, sitemap_url, kind) tuple on the canonical BuyWhere DB.
//
// Mirrors the structure of producer-cc-discover.js and producer-tranco.js:
// same singleton-dedupe shape, same summary log, same pgBoss stop+finally
// teardown so the railway.json `scheduled` entry that runs this is a
// drop-in alongside the existing producers.
//
// Singleton key shape: `discover.sitemap:<kind>:<domain>:<sitemap_url>`
// so re-running the producer within SITEMAP_PRODUCER_SINGLETON_HOURS is
// a no-op for (domain, sitemap_url) pairs that already have a pending
// or recently-completed job. 23h matches the WC / CC / Tranco producers.
//
// The 'brand' and 'retailer' kinds are processed in a single tick; the
// SITEMAP_PRODUCER_KINDS env var can limit which kinds are emitted
// (e.g. SITEMAP_PRODUCER_KINDS=brand for a brand-only first run).

import dotenv from 'dotenv';
import PgBoss from 'pg-boss';

import { loadSeedList, validateSeedEntry, SUPPORTED_KINDS } from './sitemapDiscover.js';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;
if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

const QUEUE_NAME = 'discover.sitemap';
const SINGLETON_HOURS = Math.max(1, Math.min(23, parseInt(process.env.SITEMAP_PRODUCER_SINGLETON_HOURS || '23', 10)));
const ENABLED_KINDS = (process.env.SITEMAP_PRODUCER_KINDS || SUPPORTED_KINDS.join(','))
  .split(',').map((s) => s.trim()).filter((k) => SUPPORTED_KINDS.includes(k));
const BRAND_LIST_PATH = process.env.SITEMAP_BRAND_LIST || 'data/brands.json';
const RETAILER_LIST_PATH = process.env.SITEMAP_RETAILER_LIST || 'data/retailers.json';
const SOURCE_LABEL_OVERRIDE = process.env.SITEMAP_PRODUCER_SOURCE_LABEL || null;
// pg-boss caps expireInHours at 24h; singletonHours+1 must stay <= 24.
const EXPIRE_HOURS = Math.min(24, SINGLETON_HOURS + 1);

const pgBoss = new PgBoss({
  connectionString: catalogDbUrl,
  schema: 'pgboss',
});

const summary = {
  startedAt: new Date().toISOString(),
  enabledKinds: ENABLED_KINDS,
  brandList: BRAND_LIST_PATH,
  retailerList: RETAILER_LIST_PATH,
  totalEntries: 0,
  totalSitemapUrls: 0,
  enqueued: 0,
  skippedSingleton: 0,
  skippedInvalid: 0,
  errors: [],
};

function listPathFor(kind) {
  if (kind === 'brand') return BRAND_LIST_PATH;
  if (kind === 'retailer') return RETAILER_LIST_PATH;
  return null;
}

async function enqueueSitemapJob({ kind, domain, source, country, sitemapUrl, productPattern, uaMode }) {
  const singletonKey = `discover.sitemap:${kind}:${domain}:${sitemapUrl}`;
  try {
    const jobId = await pgBoss.send(QUEUE_NAME, {
      kind,
      domain,
      source,
      country,
      sitemap_url: sitemapUrl,
      product_pattern: productPattern,
      ua_mode: uaMode,
      enqueuedAt: new Date().toISOString(),
    }, {
      singletonKey,
      singletonHours: SINGLETON_HOURS,
      retryLimit: 1,
      expireInHours: EXPIRE_HOURS,
    });
    summary.enqueued++;
    console.log(`[sitemap-producer] Enqueued ${QUEUE_NAME} job ${jobId || '<accepted>'} for ${domain} kind=${kind} url=${sitemapUrl} (singleton=${singletonKey})`);
  } catch (err) {
    const msg = String(err && err.message || err);
    if (/singleton/i.test(msg) || /already.*active/i.test(msg)) {
      summary.skippedSingleton++;
      console.log(`[sitemap-producer] Skipped ${domain} ${sitemapUrl} (singleton dedupe, retry within ${SINGLETON_HOURS}h)`);
    } else {
      summary.errors.push({ domain, sitemapUrl, error: msg });
      console.error(`[sitemap-producer] Failed to enqueue job for ${domain} ${sitemapUrl}:`, msg);
    }
  }
}

async function processKind(kind) {
  const path = listPathFor(kind);
  let entries;
  try {
    entries = await loadSeedList(path);
  } catch (e) {
    summary.errors.push({ kind, path, error: e.message });
    console.error(`[sitemap-producer] Failed to load ${kind} seed list from ${path}: ${e.message}`);
    return;
  }
  console.log(`[sitemap-producer] Loaded ${entries.length} ${kind} entries from ${path}`);

  for (const entry of entries) {
    const v = validateSeedEntry(entry);
    if (!v.ok) {
      summary.skippedInvalid++;
      summary.errors.push({ kind, domain: entry?.domain, errors: v.errors });
      console.warn(`[sitemap-producer] Invalid ${kind} entry (domain=${entry?.domain}): ${v.errors.join(', ')}`);
      continue;
    }
    summary.totalEntries++;
    for (const sitemapUrl of entry.sitemaps) {
      summary.totalSitemapUrls++;
      const source = SOURCE_LABEL_OVERRIDE
        ? `${SOURCE_LABEL_OVERRIDE}_${entry.domain.replace(/[^a-z0-9]/gi, '').toLowerCase()}`
        : entry.source;
      await enqueueSitemapJob({
        kind,
        domain: entry.domain,
        source,
        country: entry.country,
        sitemapUrl,
        productPattern: entry.productPattern,
        uaMode: entry.uaMode || 'bot',
      });
    }
  }
}

async function main() {
  console.log('[sitemap-producer] Starting sitemap-driven merchant discovery producer...');
  console.log(`[sitemap-producer] config: KINDS=${ENABLED_KINDS.join(',')} SINGLETON_HOURS=${SINGLETON_HOURS} BRAND_LIST=${BRAND_LIST_PATH} RETAILER_LIST=${RETAILER_LIST_PATH}`);

  if (ENABLED_KINDS.length === 0) {
    throw new Error(`No enabled kinds. Set SITEMAP_PRODUCER_KINDS to a comma-separated list of: ${SUPPORTED_KINDS.join(', ')}`);
  }

  await pgBoss.start();
  console.log('[sitemap-producer] pgboss started (schema bootstrapped if needed)');

  for (const kind of ENABLED_KINDS) {
    await processKind(kind);
  }

  console.log(`[sitemap-producer] Enqueued ${summary.enqueued} jobs; ${summary.skippedSingleton} skipped by singleton dedupe; ${summary.skippedInvalid} invalid; ${summary.errors.length} errors`);
}

main()
  .then(async () => {
    summary.finishedAt = new Date().toISOString();
    console.log('[sitemap-producer] summary:', JSON.stringify(summary, null, 2));
  })
  .catch(async (err) => {
    console.error('[sitemap-producer] Fatal error:', err);
    summary.errors.push({ fatal: String(err && err.message || err) });
    summary.finishedAt = new Date().toISOString();
    console.log('[sitemap-producer] summary:', JSON.stringify(summary, null, 2));
    process.exitCode = 1;
  })
  .finally(async () => {
    try { await pgBoss.stop(); } catch {}
  });
