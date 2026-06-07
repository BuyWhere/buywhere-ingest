import dotenv from 'dotenv';
import pg from 'pg';

dotenv.config();

const catalogDbUrl = process.env.CATALOG_DB_URL || process.env.DATABASE_URL;

if (!catalogDbUrl) {
  throw new Error('Missing CATALOG_DB_URL (or DATABASE_URL) environment variable.');
}

// BUY-34833 / BUY-34834 / BUY-34835 / BUY-34836: surface all ingest queues
// in /healthz:
//   - scrape.shopify           — Shopify page 1 (XML sitemap → first ~250)
//   - scrape.shopify.deep      — Shopify deep pages 7-80 (migrated from
//                                buy30590-deep-page-loop.mjs; row rate must
//                                match the live loop for 24h before cutover)
//   - scrape.woocommerce.deep  — WooCommerce deep pages 1-80 (Store API)
//   - discover.cc              — Common Crawl Shopify discovery
//   - discover.tranco          — Tranco non-Shopify platform discovery
//                                (woocommerce/magento/bigcommerce/custom)
const TRACKED_QUEUES = [
  'scrape.shopify',
  'scrape.shopify.deep',
  'scrape.woocommerce.deep',
  'discover.cc',
  'discover.tranco',
];

const db = new pg.Pool({
  connectionString: catalogDbUrl,
});

async function getIngestionStats() {
  try {
    const result = await db.query(`
      SELECT
        COUNT(*) as total_runs,
        COUNT(*) FILTER (WHERE status = 'completed') as completed_runs,
        COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
        COUNT(*) FILTER (WHERE status = 'running') as running_runs,
        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as last_hour_runs,
        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h_runs,
        SUM(rows_inserted) FILTER (WHERE rows_inserted IS NOT NULL) as total_rows_inserted,
        SUM(rows_updated) FILTER (WHERE rows_updated IS NOT NULL) as total_rows_updated,
        MAX(created_at) as last_run_at
      FROM ingestion_runs
    `);
    return result.rows[0];
  } catch (err) {
    console.error('[health] Error fetching ingestion stats:', err);
    return null;
  }
}

async function getRecentJobs(limit = 10) {
  try {
    const result = await db.query(`
      SELECT
        id, source, status, created_at, finished_at,
        rows_inserted, rows_updated, rows_failed, error_message
      FROM ingestion_runs
      ORDER BY created_at DESC
      LIMIT $1
    `, [limit]);
    return result.rows;
  } catch (err) {
    console.error('[health] Error fetching recent jobs:', err);
    return [];
  }
}

async function getQueueStats() {
  try {
    // Per-queue stats. pgboss stores jobs in pgboss.job. The single-query
    // GROUP BY is cheaper than N queries. /healthz uses these to surface
    // deep-queue throughput (BUY-34833 acceptance: deep-page row rate >= live loop).
    const result = await db.query(`
      SELECT
        name as queue_name,
        COUNT(*) FILTER (WHERE state = 'created') as pending,
        COUNT(*) FILTER (WHERE state = 'active') as active,
        COUNT(*) FILTER (WHERE state = 'completed') as completed,
        COUNT(*) FILTER (WHERE state = 'failed') as failed
      FROM pgboss.job
      WHERE name = ANY($1)
      GROUP BY name
    `, [TRACKED_QUEUES]);

    // Always return a row per tracked queue (with zeros if absent) so the
    // /healthz payload shape is stable across "no jobs yet" states.
    const byName = Object.fromEntries(result.rows.map((r) => [r.queue_name, r]));
    return TRACKED_QUEUES.map((name) => byName[name] || {
      queue_name: name,
      pending: 0,
      active: 0,
      completed: 0,
      failed: 0,
    });
  } catch (err) {
    console.error('[health] Error fetching queue stats:', err);
    return null;
  }
}

export { getIngestionStats, getRecentJobs, getQueueStats };

export async function handler(event) {
  const stats = await getIngestionStats();
  const recentJobs = await getRecentJobs();
  const queueStats = await getQueueStats();

  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'buywhere-ingest',
    stats: stats || {},
    queue: queueStats || {},
    recent_jobs: recentJobs
  };

  if (!stats) {
    health.status = 'degraded';
  }

  if (stats && stats.running_runs > 5) {
    health.status = 'busy';
  }

  if (stats && stats.failed_runs > 0 && stats.completed_runs === 0) {
    health.status = 'unhealthy';
  }

  return {
    statusCode: health.status === 'healthy' ? 200 : 503,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(health, null, 2),
  };
}
