#!/bin/bash
# lane-watchdog-cron.sh — Cron-based durability watchdog for long-running lanes.
# BUY-31185: Ensures the loop-supervisor and critical lane processes survive
# heartbeat gaps, even before systemd units are deployed by Ops.
#
# This script is idempotent: it checks if processes are alive before restarting.
# Designed to run every 2 minutes via crontab.
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$ROOT_DIR/logs/lane-watchdog-cron.log"
PID_FILE="$ROOT_DIR/data/.loop-supervisor.pid"
SUPERVISOR_SCRIPT="$ROOT_DIR/scripts/loop-supervisor.sh"
TICK="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/data"

log() { echo "[$TICK] $*" >> "$LOG_FILE"; }

# --- Check loop-supervisor is running ---
supervisor_alive=false
if [[ -f "$PID_FILE" ]]; then
  spid=$(cat "$PID_FILE")
  if kill -0 "$spid" 2>/dev/null; then
    supervisor_alive=true
  fi
fi

if ! $supervisor_alive; then
  log "Loop supervisor not running — restarting"
  bash "$SUPERVISOR_SCRIPT" start >> "$LOG_FILE" 2>&1
  log "Supervisor restart triggered"
else
  # Supervisor is alive but check if any critical loops are dead
  # (belt-and-suspenders: supervisor should catch these, but cron adds a safety net)
  dead_count=0

  # Check buy30331
  if ! pgrep -f "node.*buy30331-sustained-loop\\.mjs" | grep -q "[n]ode" 2>/dev/null; then
    log "ALERT: buy30331-sustained-loop is dead (supervisor alive but loop missing)"
    ((dead_count++))
  fi

  # Check buy30590
  if ! pgrep -f "node.*buy30590-deep-page-loop\\.mjs" | grep -q "[n]ode" 2>/dev/null; then
    log "ALERT: buy30590-deep-page-loop is dead (supervisor alive but loop missing)"
    ((dead_count++))
  fi

  # If any critical loops are dead despite supervisor running, trigger a restart cycle
  if (( dead_count > 0 )); then
    log "Triggering supervisor restart-dead for $dead_count dead loops"
    bash "$SUPERVISOR_SCRIPT" restart >> "$LOG_FILE" 2>&1
  fi
fi

# Final status line
alive_30331=$(pgrep -f "node.*buy30331-sustained-loop\\.mjs" | grep -c "[n]ode" 2>/dev/null || echo 0)
alive_30590=$(pgrep -f "node.*buy30590-deep-page-loop\\.mjs" | grep -c "[n]ode" 2>/dev/null || echo 0)
alive_30727=$(pgrep -f "node.*buy30727-lane-supervisor\\.mjs" | grep -c "[n]ode" 2>/dev/null || echo 0)
log "Status: supervisor=$supervisor_alive buy30331=${alive_30331} buy30590=${alive_30590} buy30727=${alive_30727}"
