import dotenv from 'dotenv';
import express from 'express';
import { scrapeShopifyStore, scrapeShopifyStorePages } from './shopifyScraper.js';
import { getIngestionStats, getRecentJobs, getQueueStats } from './health.js';
import { probeTrancoHost, SUPPORTED_KINDS } from './trancoDiscovery.js';
import { walkSitemapForProducts, countryFromHost, SUPPORTED_KINDS as SITEMAP_KINDS } from './sitemapDiscover.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

// Health endpoint
app.get(['/health', '/healthz'], async (req, res) => {
  try {
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

    res.status(health.status === 'healthy' ? 200 : 503)
      .set('Content-Type', 'application/json')
      .json(health);
  } catch (err) {
    res.status(503).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: err.message
    });
  }
});

// BUY-33060: page-1 scraper test endpoint (existing).
app.get('/test-scraper', async (req, res) => {
  try {
    const { domain } = req.query;
    if (!domain) {
      return res.status(400).json({ error: 'Domain parameter is required' });
    }

    const products = await scrapeShopifyStore(domain, 3);
    res.json({
      domain,
      products_count: products.length,
      products: products.slice(0, 2),
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    res.status(500).json({
      error: err.message,
      timestamp: new Date().toISOString()
    });
  }
});

// BUY-34833: deep-page scraper test endpoint. Mirrors /test-scraper but
// hits /products.json?page=N&limit=250 (pages 7-80 by default). Used for
// pre-deploy verification on Railway against a known-good merchant.
app.get('/test-deep-scraper', async (req, res) => {
  try {
    const { domain, start, end, limit } = req.query;
    if (!domain) {
      return res.status(400).json({ error: 'Domain parameter is required' });
    }
    const startPage = start ? parseInt(start, 10) : 7;
    const endPage = end ? parseInt(end, 10) : 8;
    const pageLimit = limit ? parseInt(limit, 10) : 250;

    const products = await scrapeShopifyStorePages(domain, startPage, endPage, pageLimit);
    res.json({
      domain,
      start_page: startPage,
      end_page: endPage,
      limit: pageLimit,
      products_count: products.length,
      products: products.slice(0, 2),
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    res.status(500).json({
      error: err.message,
      timestamp: new Date().toISOString()
    });
  }
});

// BUY-34836: tranco platform fingerprint probe. Mirrors /test-scraper but
// runs the kind-specific platform probe (woocommerce/magento/bigcommerce/custom)
// against a single host. Used for pre-deploy verification against a known
// non-Shopify merchant (e.g. a WordPress + WC store for kind=woocommerce).
app.get('/test-tranco-probe', async (req, res) => {
  try {
    const { domain, kind, timeoutMs } = req.query;
    if (!domain) {
      return res.status(400).json({ error: 'Domain parameter is required' });
    }
    const useKind = SUPPORTED_KINDS.includes(kind) ? kind : 'woocommerce';
    const useTimeout = timeoutMs ? Math.min(30000, Math.max(500, parseInt(timeoutMs, 10))) : 6000;

    const t0 = Date.now();
    const result = await probeTrancoHost(domain, useKind, useTimeout);
    const dt = Date.now() - t0;
    res.json({
      domain,
      kind: useKind,
      timeout_ms: useTimeout,
      dt_ms: dt,
      ...result,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    res.status(500).json({
      error: err.message,
      timestamp: new Date().toISOString()
    });
  }
});

// BUY-34837: sitemap walker test endpoint. Mirrors /test-tranco-probe but
// fetches a single sitemap URL and returns the product-URL count for it.
// Used for pre-deploy verification on Railway against a known-good
// merchant (e.g. Nike's sitemap_products.xml for kind=brand or Best Buy's
// sitemaps_pdp.xml for kind=retailer). The worker itself does the same
// walk; this endpoint just exposes it for ad-hoc smoke tests.
app.get('/test-sitemap-walk', async (req, res) => {
  try {
    const { url, pattern, kind, timeoutMs, maxDepth, maxLocs } = req.query;
    if (!url) {
      return res.status(400).json({ error: 'url parameter is required (the sitemap URL to walk)' });
    }
    if (!pattern) {
      return res.status(400).json({ error: 'pattern parameter is required (the per-merchant product URL regex)' });
    }
    const useKind = SITEMAP_KINDS.includes(kind) ? kind : 'brand';
    const useTimeout = timeoutMs ? Math.min(60000, Math.max(500, parseInt(timeoutMs, 10))) : 20000;
    const useMaxDepth = maxDepth ? Math.min(10, Math.max(1, parseInt(maxDepth, 10))) : 4;
    const useMaxLocs = maxLocs ? Math.min(200000, Math.max(100, parseInt(maxLocs, 10))) : 50000;
    let host = null;
    try { host = new URL(url).host; } catch {}
    const country = host ? countryFromHost(host) : 'US';

    const t0 = Date.now();
    const walk = await walkSitemapForProducts(url, {
      productPattern: pattern,
      timeoutMs: useTimeout,
      maxDepth: useMaxDepth,
      maxLocs: useMaxLocs,
    });
    const dt = Date.now() - t0;
    res.json({
      url,
      host,
      kind: useKind,
      country,
      product_count: walk.productUrls.length,
      product_urls_sample: walk.productUrls.slice(0, 5),
      sub_sitemaps_walked: walk.subSitemapsWalked,
      fetches: walk.fetches,
      dt_ms: dt,
      errors: walk.errors.slice(0, 10),
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    res.status(500).json({
      error: err.message,
      timestamp: new Date().toISOString()
    });
  }
});

// Simple root endpoint
app.get('/', (req, res) => {
  res.json({
    service: 'buywhere-ingest',
    status: 'running',
    version: '1.0.0',
    endpoints: [
      '/health - Health check and stats (includes scrape.shopify + scrape.shopify.deep + discover.tranco + discover.sitemap queue counts)',
      '/test-scraper?domain=example.com - Test page-1 scraper (sitemap)',
      '/test-deep-scraper?domain=example.com&start=7&end=8 - Test deep scraper (/products.json?page=N)',
      '/test-tranco-probe?domain=example.com&kind=woocommerce - Test tranco non-Shopify platform fingerprint (woocommerce|magento|bigcommerce|custom)',
      '/test-sitemap-walk?url=...&pattern=... - Test sitemap walker (product-URL discovery from a single sitemap URL)'
    ]
  });
});

app.listen(port, () => {
  console.log(`buywhere-ingest server running on port ${port}`);
});
