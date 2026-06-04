# BUY-30091: Phase 2 - Real Shopify Scrape Jobs + Observability

This service implements real Shopify product scraping jobs with Railway-based queue processing and throughput observability.

## Architecture

### Components

1. **Worker** (`src/worker.js`): Processes `scrape.shopify` jobs from pg-boss queue
   - Creates `ingestion_runs` records for tracking
   - Executes Shopify scraping via `scrapeShopifyStore()`
   - Ingests products to catalog via BuyWhere API (`/v1/ingest/products`)
   - Records completion status and counts (inserted/updated/failed)

2. **Producer** (`src/producer.js`): Enqueues scrape jobs
   - Queries `merchants` table for active Shopify stores
   - Enqueues `scrape.shopify` jobs with merchant metadata
   - Scheduled every 6 hours for continuous scraping

3. **Shopify Scraper** (`src/shopifyScraper.js`): Core scraping logic
   - Discovers product sitemaps from `sitemap.xml`
   - Parses XML sitemaps to find product URLs
   - Scrapes PDPs for structured data (JSON-LD, meta tags)
   - Returns products in canonical catalog format

4. **Health Endpoint** (`src/server.js`): Monitoring and testing
   - `/health` - Health check with ingestion stats and queue metrics
   - `/test-scraper?domain=example.com` - Test scraper functionality
   - Root endpoint with service info

## Environment Variables

Required for Railway deployment:
- `CATALOG_DB_URL` - PostgreSQL connection string (provided by Railway db service)
- `BUYWHERE_API_KEY` - API key for catalog ingestion (`bw_265c3838655543469dda26d225412864`)
- `BUYWHERE_API_URL` - BuyWhere API base URL (`https://api.buywhere.ai`)

Optional:
- `PGBOSS_ALLOWED_ENV` - Environment for pg-boss validation (`railway`)
- `CATALOG_DB_ENVIRONMENT` - Database environment context
- `CATALOG_DB_CANONICAL` - Enable canonical DB operations

## Deployment

### Railway Setup

1. Connect Railway service to this repository
2. Create PostgreSQL database service:
   - Name: `catalog-db`
   - Adapter: PostgreSQL
   - Database: `catalog`
   - User: `catalog`
   - Role: `buywhere_ingest_rw`

3. Deploy with `railway.json` configuration:
   ```bash
   railway init
   railway up
   ```

4. Set environment variables in Railway dashboard:
   - `BUYWHERE_API_KEY` from adapter config
   - `BUYWHERE_API_URL` (https://api.buywhere.ai)

### Local Testing

```bash
# Start local database and worker
docker compose up

# Test scraper
node scripts/test-scraper.js

# Test with specific domain
node scripts/test-scraper.js SHOPIFY_DOMAIN=store.anycubic.com

# Enqueue test job
docker compose exec ingest-worker npm run producer

# Check health endpoint
curl http://localhost:3000/health
```

## Rollout Plan

### Phase 1: Single Merchant Testing
1. Select one active Shopify merchant from `merchants` table
2. Manually enqueue scrape job:
   ```bash
   docker compose exec ingest-worker node scripts/seed-shopify.js
   ```
3. Monitor ingestion via health endpoint and check catalog
4. Verify no DATABASE_URL drift between API and ingest services

### Phase 2: Scheduled Production
1. Enable scheduled producer (every 6 hours via Railway cron)
2. Expand to all active Shopify merchants
3. Monitor throughput in Grafana via `ingestion_runs.completed/hour` metric
4. Gradual cutover from external ingestion path

### Phase 3: Full Retirement
1. Wait for Railway path to complete ≥1 full ingestion cycle without errors
2. Retire old external ingestion path

## Monitoring

### Key Metrics
- `ingestion_runs.completed` per hour (Grafana)
- Queue depth and job states (health endpoint)
- Error rates and failure reasons (health endpoint)
- Product ingestion volume (catalog API)

### Endpoints
- `/health` - Comprehensive health check with stats
- `/test-scraper?domain=example.com` - Test scraper functionality
- Railway dashboard - Service logs and metrics

## Testing

### Unit Tests
- Test scraper with known Shopify stores
- Test ingestion flow with sample products
- Test error handling and retries

### Integration Tests
- Test job processing end-to-end
- Test health endpoint accuracy
- Test producer with merchant database

### Manual Testing
- Use `seed-shopify.js` to enqueue test jobs
- Use `test-scraper.js` to verify scraping logic
- Monitor ingestion results in catalog

## Security Considerations

- Uses least-privilege database role (`buywhere_ingest_rw`)
- API key authentication for catalog ingestion
- Environment-specific pg-boss validation
- Error handling without sensitive data exposure

## Configuration Files

- `railway.json` - Railway deployment configuration
- `docker-compose.yml` - Local development environment
- `Dockerfile` - Container image for deployment