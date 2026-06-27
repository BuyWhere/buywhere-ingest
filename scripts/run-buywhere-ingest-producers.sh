#!/bin/bash
# BUY-58462: Self-feeding producer cron for buywhere-ingest.
# Runs Shopify + WooCommerce + sitemap + cc-discover + tranco + lanes + embed producers
# every 30 minutes, ensuring the worker always has fresh jobs.
#
# Cron entries (added by this script):
#   */30 * * * * bash .../buywhere-ingest/scripts/run-buywhere-ingest-producers.sh >> .../buywhere-ingest/logs/producer-cron.log 2>&1

set -uo pipefail

REPO_ROOT="/paperclip/instances/default/workspaces/85b280a3-a3e8-4681-83ce-dfd953888c33/buywhere-ingest"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "$LOG_DIR"

cd "$REPO_ROOT"

# Ensure node_modules is present (Railway/Render-style env may have wiped it)
if [ ! -d "node_modules" ]; then
  echo "[producer-cron] $(date -u) installing node_modules..."
  npm ci --no-audit --no-fund >> "$LOG_DIR/producer-cron.log" 2>&1 || true
fi

# Load .env if present (Railway injects these at runtime, but local crontab may need them)
if [ -f "$REPO_ROOT/.env" ]; then
  set -a; . "$REPO_ROOT/.env"; set +a
fi

# Database URL must be set (Paperclip server injects DATABASE_URL via env, cron inherits)
if [ -z "${DATABASE_URL:-}" ]; then
  echo "[producer-cron] $(date -u) FATAL: DATABASE_URL not set"
  exit 2
fi

run_producer() {
  local script="$1"; shift
  local label="$1"; shift
  echo "[producer-cron] $(date -u) start $label"
  if timeout 60 node "$REPO_ROOT/src/$script" "$@" 2>&1; then
    echo "[producer-cron] $(date -u) ok $label"
  else
    local rc=$?
    echo "[producer-cron] $(date -u) FAIL $label (rc=$rc)"
  fi
}

# BUY-33060: Shopify producer — runs every 30min with 1h singleton so we always
# work through the backlog without re-enqueueing same domain within an hour.
run_producer producer.js "shopify-us-sg (50/30min)" \
  PRODUCER_COUNTRY="US,SG" \
  PRODUCER_BATCH_LIMIT=50 \
  PRODUCER_SINGLETON_HOURS=1

# BUY-34834: WooCommerce deep producer — 100 merchants per tick, 22h singleton
# (pinned at max safe value to avoid the 24h ceiling rejection).
run_producer producer-woocommerce.js "woocommerce-us-sg (100/30min)" \
  WC_PRODUCER_BATCH_LIMIT=100 \
  WC_PRODUCER_COUNTRY="US,SG"

# BUY-42617 / Sitemap discovery
run_producer producer-sitemap.js "sitemap (1h singleton)"

echo "[producer-cron] $(date -u) done"
