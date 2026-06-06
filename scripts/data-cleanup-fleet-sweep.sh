#!/bin/bash
# data-cleanup-fleet-sweep.sh — 6-hourly sweep that runs safe-data-cleanup.sh
# --apply on every scraping/ingestion workspace, jittered so the catalog DB
# is not hammered by all of them in the same second.
#
# BUY-33094 acceptance:
#   - data-cleanup.service + .timer (or cron entry) every 6h
#   - Jittered by workspace so the catalog DB is not hammered
#   - One-line cycle report per workspace
#
# Install as a user cron entry (no root required):
#   7 */6 * * *  bash /paperclip/.../scripts/data-cleanup-fleet-sweep.sh
# The per-workspace jitter is baked into this script via per-workspace sleep
# offsets so that the cron entry itself stays simple (one line).
#
# For systemd users, the same effect is achieved by enabling the
# paperclip-data-cleanup@.timer template (see deploy-systemd-units.sh).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WRAPPER="$SCRIPT_DIR/cleanup-teardown.sh"
SWEEP_LOG="$SCRIPT_DIR/../logs/data-cleanup-fleet-sweep.log"
mkdir -p "$(dirname "$SWEEP_LOG")"

# Workspaces that need a cleanup sweep. Match the SCRAPING_WORKSPACES list in
# deploy-systemd-units.sh. Jitter offsets are seconds to sleep BEFORE the
# cleanup so the catalog DB doesn't see all workspaces at once.
#
# 30-min jitter window (1800s) divided by 12 workspaces ≈ 150s average gap.
# We use 90s base + 5 min random per workspace for an 8-min spread.
declare -a WORKSPACES=(
  "0ed653ab-62ba-4deb-8348-3086ab46961c"   # Shelf
  "2e68d8a0-9b0e-4573-8185-323edaabb186"   # Crate
  "3ec8f6dd-1735-4479-9825-a2c42edac34c"   # Oracle
  "4df23039-272b-4621-9d77-7cf9b7121242"   # Stock
  "5bc984ee-e2d2-4312-9e6c-b2864524a21f"   # Shopper
  "708a8ce4-96dd-409d-94e7-a91d5032e4e0"   # Hunt 2
  "7fb55262-e658-45e2-88c0-b0e8ccc5ad6c"   # Hex
  "a29ac9dc-cf0a-455b-964c-e75bd2f5fc47"   # Dash
  "bf810416-2f4c-4c4b-b27c-1270ea6f20b3"   # Probe
  "c2850c54-3396-420a-b7c3-92faae3137c1"   # Probe 2
  "d70ff7b3-e26b-4d23-8e05-bfc5d6f7a342"   # Crew
  "f6a39f3c-210b-479b-a8e7-c78491c120e9"   # Hunt
)

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log() {
  local line="[$(ts)] $*"
  echo "$line" | tee -a "$SWEEP_LOG" >/dev/null
}

log "=== fleet-sweep start (${#WORKSPACES[@]} workspaces) ==="

# Per-workspace jitter — random 0-300s, capped so the whole fleet finishes
# within ~40 minutes even if it stacks against the next sweep window.
START_TS=$(date +%s)
i=0
for ws_id in "${WORKSPACES[@]}"; do
  i=$((i + 1))
  # 90s base + 5 min random per workspace — yields ~3-8 min spread
  JITTER=$(( 90 + (RANDOM % 300) ))
  sleep "$JITTER"
  WS_PATH="/paperclip/instances/default/workspaces/$ws_id"
  if [ ! -d "$WS_PATH" ]; then
    log "  [$i/${#WORKSPACES[@]}] $ws_id MISSING workspace dir — skip"
    continue
  fi
  if [ ! -x "$WS_PATH/safe-data-cleanup.sh" ]; then
    log "  [$i/${#WORKSPACES[@]}] $ws_id MISSING safe-data-cleanup.sh — skip (run install-safe-data-cleanup.sh)"
    continue
  fi
  log "  [$i/${#WORKSPACES[@]}] $ws_id sweep start (jitter=${JITTER}s)"
  REPORT=$(bash "$WRAPPER" "$WS_PATH" --apply --timeout=540 2>&1 | tail -1)
  log "  [$i/${#WORKSPACES[@]}] $ws_id sweep done: $REPORT"
done

END_TS=$(date +%s)
DUR=$(( END_TS - START_TS ))
log "=== fleet-sweep done dur=${DUR}s ==="
