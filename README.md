# buywhere-ingest (Phase 1 scaffold)

This directory contains the `buywhere-ingest` worker skeleton for issue `BUY-22769`.

- Subscribes to queue: `scrape.shopify`
- Logs job payloads (no real ingestion call yet)
- Uses `pg-boss` schema under `pgboss.*`
- Containerized via `Dockerfile`

## Run locally

From this directory:

```bash
docker compose up --build
```

This starts:

- a throwaway Postgres database on `localhost:5432`
- a one-shot `pgboss.*` schema bootstrap against that throwaway database
- the worker container connected via `postgres://catalog:catalog@postgres:5432/catalog`

The bootstrap step only runs in local compose because it is explicitly gated. For any non-compose or manual bootstrap, set explicit env so dev/test does not accidentally point at the wrong catalog DB:

```bash
BOOTSTRAP_PG_BOSS_SCHEMA=true \
PGBOSS_ALLOWED_ENV=local \
CATALOG_DB_ENVIRONMENT=local \
CATALOG_DB_CANONICAL=true \
CATALOG_DB_URL=postgres://catalog:catalog@postgres:5432/catalog \
node scripts/bootstrap-pgboss.js
```

To publish a one-off test job:

```bash
docker compose exec ingest-worker node scripts/seed-shopify.js
```

## Repo structure

- `src/worker.js` — queue worker stub
- `scripts/bootstrap-pgboss.js` — idempotent schema bootstrap with explicit canonical guard
- `scripts/seed-shopify.js` — optional local smoke publisher
- `Dockerfile` — worker container image
- `docker-compose.yml` — local dev harness
