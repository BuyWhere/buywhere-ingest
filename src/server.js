import dotenv from 'dotenv';
import express from 'express';
import { scrapeShopifyStore } from './shopifyScraper.js';
import { getIngestionStats, getRecentJobs, getQueueStats } from './health.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

// Health endpoint
app.get('/health', async (req, res) => {
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

// Test endpoint for manual Shopify scraping
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

// Simple root endpoint
app.get('/', (req, res) => {
  res.json({
    service: 'buywhere-ingest',
    status: 'running',
    version: '1.0.0',
    endpoints: [
      '/health - Health check and stats',
      '/test-scraper?domain=example.com - Test scraper'
    ]
  });
});

app.listen(port, () => {
  console.log(`buywhere-ingest server running on port ${port}`);
});