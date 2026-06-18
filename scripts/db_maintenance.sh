#!/bin/bash

# Database maintenance script for Rex's infrastructure team
# This script helps manage database performance by running periodic maintenance

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/tmp/db_maintenance"

# Create log directory
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/maintenance-$(date '+%Y-%m-%d').log"
echo "Database Maintenance - $(date '+%Y-%m-%dT%H:%M:%S+00:00')" > "$LOG_FILE"

# Database connection
DB_URL="postgresql://buywhere_ingest:MommMnA7BUR3yo6qkPDO0vhxoOh6IQee@maglev.proxy.rlwy.net:31310/railway?sslmode=require"

# Function to log with timestamp
log() {
    echo "[$(date '+%H:%M:%S+00:00')] $1" | tee -a "$LOG_FILE"
}

log "Starting database maintenance..."

# Check dead tuple count before vacuum
log "Checking dead tuple count..."
DEAD_BEFORE=$(psql "$DB_URL" -t -c "SELECT COALESCE(n_dead_tup, 0) FROM pg_stat_user_tables WHERE relname = 'products';" | xargs)

# Run VACUUM ANALYZE
log "Running VACUUM ANALYZE..."
START_TIME=$(date +%s)
psql "$DB_URL" -c "VACUUM ANALYZE products;" >> "$LOG_FILE" 2>&1
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Check dead tuple count after vacuum
DEAD_AFTER=$(psql "$DB_URL" -t -c "SELECT COALESCE(n_dead_tup, 0) FROM pg_stat_user_tables WHERE relname = 'products';" | xargs)

log "Vacuum completed in ${DURATION} seconds"
log "Dead tuples before: ${DEAD_BEFORE}"
log "Dead tuples after: ${DEAD_AFTER}"

# Calculate difference
if [ "$DEAD_BEFORE" -gt "$DEAD_AFTER" ]; then
    REMOVED=$((DEAD_BEFORE - DEAD_AFTER))
    log "✅ Removed $REMOVED dead tuples"
else
    log "⚠️ Dead tuple count didn't decrease - may need more aggressive maintenance"
fi

# Check table size
log "Checking table size..."
TABLE_SIZE=$(psql "$DB_URL" -t -c "SELECT pg_size_pretty(pg_total_relation_size('public.products'));" | xargs)
log "Products table size: $TABLE_SIZE"

# Log any long-running queries
log "Checking for long-running queries..."
LONG_QUERIES=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > INTERVAL '1 minute';" | xargs)
if [ "$LONG_QUERIES" -gt 0 ]; then
    log "⚠️ Found $LONG_QUERIES long-running queries (>1 minute)"
fi

log "Database maintenance completed"
echo "Maintenance log: $LOG_FILE"