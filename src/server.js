import dotenv from 'dotenv';
import express from 'express';
import { scrapeShopifyStore, scrapeShopifyStorePages } from './shopifyScraper.js';
import { getIngestionStats, getRecentJobs, getQueueStats } from './health.js';

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

// Simple root endpoint
app.get('/', (req, res) => {
  res.json({
    service: 'buywhere-ingest',
    status: 'running',
    version: '1.0.0',
    endpoints: [
      '/health - Health check and stats (includes scrape.shopify + scrape.shopify.deep queue counts)',
      '/test-scraper?domain=example.com - Test page-1 scraper (sitemap)',
      '/test-deep-scraper?domain=example.com&start=7&end=8 - Test deep scraper (/products.json?page=N)'
    ]
  });
});

app.listen(port, () => {
  console.log(`buywhere-ingest server running on port ${port}`);
});
