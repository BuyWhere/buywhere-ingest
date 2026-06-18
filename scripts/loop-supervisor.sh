#!/bin/bash
# loop-supervisor.sh — Lightweight supervisor for critical ingest loops.
# Ensures loops survive heartbeat boundaries by running as fully detached daemons
# with their own session IDs, and automatically restarting on failure.
#
# BUY-30885: Harden process supervision for sustained-throughput loops.
#
# Usage:
#   bash scripts/loop-supervisor.sh start   # start supervisor daemon
#   bash scripts/loop-supervisor.sh status  # show supervised loop status
#   bash scripts/loop-supervisor.sh stop    # stop supervisor and all loops
#   bash scripts/loop-supervisor.sh restart # restart dead loops (no supervisor)
#
# PID file: data/.loop-supervisor.pid
# Log file: logs/loop-supervisor.log

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$ROOT_DIR/data/.loop-supervisor.pid"
LOG_FILE="$ROOT_DIR/logs/loop-supervisor.log"
CHECK_INTERVAL=30  # seconds between health checks
RESTART_DELAY=10   # seconds to wait before restarting a dead loop
MAX_RESTARTS=5     # max restarts per loop per supervisor cycle
SUPERVISOR_TIMEOUT=43200  # 12 hours — supervisor re-exits and lets next heartbeat restart

mkdir -p "$ROOT_DIR/data" "$ROOT_DIR/logs"

# --- Critical loops to supervise ---
# Each entry: "script_pattern:restart_command"
# script_pattern is used with `pgrep -f` to find running instances
# restart_command is the full command to start the loop

WORKSPACE_3EC="3ec8f6dd-1735-4479-9825-a2c42edac34c"

LOOP_DEFS=(
  "node.*buy30331-sustained-loop\\.mjs:nohup setsid node /paperclip/instances/default/workspaces/${WORKSPACE_3EC}/scripts/buy30331-sustained-loop.mjs >> $ROOT_DIR/logs/supervised-buy30331.log 2>&1 &"
  "node.*buy30590-deep-page-loop\\.mjs:nohup setsid node /paperclip/instances/default/workspaces/${WORKSPACE_3EC}/scripts/buy30590-deep-page-loop.mjs >> $ROOT_DIR/logs/supervised-buy30590-deep.log 2>&1 &"
  # BUY-31452: buy30727 CC-MAIN lane supervisor PERMANENTLY DISABLED — all 47 indices saturated.
  # Commented out entirely (not just stop-marker gated) to prevent any respawn races.
  # "node.*buy30727-lane-supervisor\\.mjs:nohup setsid node /paperclip/instances/default/workspaces/${WORKSPACE_3EC}/scripts/buy30727-lane-supervisor.mjs >> $ROOT_DIR/logs/supervised-buy30727.log 2>&1 &"
  # NOTE: buy30331-ingest-stream.mjs removed — it is a one-shot bulk ingest utility
  # that requires NDJSON file arguments, not a persistent loop. Supervising it
  # causes a crash loop (exits "No input files" → restart → hit max restarts).
)

# BUY-31452: stop-marker check for buy30727 only. If the marker file exists
# at $ROOT_DIR/data/buy30727-supervisor.stopped, treat buy30727 as permanently
# disabled (do not respawn). This overrides is_loop_alive for that one pattern.
buy30727_stop_marker="$ROOT_DIR/data/buy30727-supervisor.stopped"
is_buy30727_stopped() {
  [[ -f "$buy30727_stop_marker" ]]
}

log() {
  local ts
  ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  echo "[$ts] $*" | tee -a "$LOG_FILE"
}

is_loop_alive() {
  local pattern="$1"
  # BUY-31452: respect stop marker for buy30727
  if [[ "$pattern" == *buy30727-lane-supervisor* ]] && is_buy30727_stopped; then
    return 1  # pretend dead so restart logic is bypassed
  fi
  # pgrep -f can match the supervisor's own shell — count only node processes
  local count
  count=$(pgrep -af "$pattern" 2>/dev/null | grep -c "[n]ode" || true)
  (( count > 0 ))
}

short_name() {
  local pattern="$1"
  # Extract script name from regex pattern like "node.*buy30331-sustained-loop\.mjs"
  echo "$pattern" | sed 's/node\.\*//' | sed 's/\\.mjs//' | sed 's/\.\*//'
}

start_loop() {
  local pattern="$1"
  local cmd="$2"
  local name
  name=$(short_name "$pattern")
  # BUY-31452: respect stop marker
  if [[ "$pattern" == *buy30727-lane-supervisor* ]] && is_buy30727_stopped; then
    log "Skipped: $name (stop marker present)"
    return 0
  fi
  if is_loop_alive "$pattern"; then
    return 0
  fi
  log "Starting: $name"
  eval "$cmd"
  sleep "$RESTART_DELAY"
  if is_loop_alive "$pattern"; then
    log "  ✓ Started successfully (PID: $(pgrep -f "$pattern" | head -1))"
    return 0
  else
    log "  ✗ Failed to start: $name"
    return 1
  fi
}

do_status() {
  log "=== Loop Supervisor Status ==="
  local alive=0 dead=0
  for entry in "${LOOP_DEFS[@]}"; do
    local pattern="${entry%%:*}"
    local name
    name=$(short_name "$pattern")
    if is_loop_alive "$pattern"; then
      local pid
      pid=$(pgrep -f "$pattern" | head -1)
      local etime
      etime=$(ps -o etime= -p "$pid" 2>/dev/null || echo "?")
      log "  ✓ $name — PID $pid, uptime $etime"
      ((alive++))
    else
      log "  ✗ $name — DEAD"
      ((dead++))
    fi
  done
  log "Alive: $alive, Dead: $dead"
  # Also check supervisor itself
  if [[ -f "$PID_FILE" ]]; then
    local spid
    spid=$(cat "$PID_FILE")
    if kill -0 "$spid" 2>/dev/null; then
      log "Supervisor: running (PID $spid)"
    else
      log "Supervisor: stale PID file (PID $spid not running)"
    fi
  else
    log "Supervisor: not running"
  fi
}

do_restart_dead() {
  log "=== Restarting dead loops ==="
  local restarted=0
  for entry in "${LOOP_DEFS[@]}"; do
    local pattern="${entry%%:*}"
    local cmd="${entry#*:}"
    if ! is_loop_alive "$pattern"; then
      if start_loop "$pattern" "$cmd"; then
        ((restarted++))
      fi
      sleep 2
    fi
  done
  log "Restarted $restarted loops"
  return 0
}

do_supervise() {
  log "=== Supervisor starting (PID $$) ==="
  echo $$ > "$PID_FILE"

  local start_time
  start_time=$(date +%s)
  local restart_counts=()
  for i in "${!LOOP_DEFS[@]}"; do
    restart_counts[$i]=0
  done

  while true; do
    local now
    now=$(date +%s)
    local elapsed=$(( now - start_time ))

    # Timeout — let next heartbeat restart the supervisor
    if (( elapsed >= SUPERVISOR_TIMEOUT )); then
      log "Supervisor timeout reached (${elapsed}s). Exiting for fresh restart."
      rm -f "$PID_FILE"
      exit 0
    fi

    local i=0
    for entry in "${LOOP_DEFS[@]}"; do
      local pattern="${entry%%:*}"
      local cmd="${entry#*:}"

      if ! is_loop_alive "$pattern"; then
        if (( restart_counts[$i] < MAX_RESTARTS )); then
          log "Detected dead loop: $pattern (restart #${restart_counts[$i]})"
          if start_loop "$pattern" "$cmd"; then
            restart_counts[$i]=$(( restart_counts[$i] + 1 ))
          fi
        else
          log "Max restarts reached for: $pattern — giving up this cycle"
        fi
      fi
      ((i++))
    done

    sleep "$CHECK_INTERVAL"
  done
}

do_start() {
  # Check if already running
  if [[ -f "$PID_FILE" ]]; then
    local spid
    spid=$(cat "$PID_FILE")
    if kill -0 "$spid" 2>/dev/null; then
      log "Supervisor already running (PID $spid)"
      do_status
      return 0
    else
      log "Stale PID file, removing"
      rm -f "$PID_FILE"
    fi
  fi

  log "Starting supervisor daemon..."

  # Start loops first
  do_restart_dead

  # Double-fork to fully detach from any session
  (
    setsid bash "$0" _supervise >> "$LOG_FILE" 2>&1 &
  )

  sleep 1
  if [[ -f "$PID_FILE" ]]; then
    log "Supervisor started (PID $(cat "$PID_FILE"))"
  else
    log "WARNING: Supervisor may not have started. Check $LOG_FILE"
  fi
  do_status
}

do_stop() {
  log "=== Stopping supervisor ==="
  if [[ -f "$PID_FILE" ]]; then
    local spid
    spid=$(cat "$PID_FILE")
    if kill -0 "$spid" 2>/dev/null; then
      kill "$spid" 2>/dev/null || true
      log "Supervisor (PID $spid) stopped"
    fi
    rm -f "$PID_FILE"
  else
    log "No PID file found"
  fi
  do_status
}

# Main dispatch
case "${1:-status}" in
  start)     do_start ;;
  stop)      do_stop ;;
  status)    do_status ;;
  restart)   do_restart_dead ;;
  _supervise) do_supervise ;;
  *)
    echo "Usage: $0 {start|stop|status|restart}"
    echo ""
    echo "  start    — Start supervisor daemon and all dead loops"
    echo "  stop     — Stop supervisor (loops continue running)"
    echo "  status   — Show status of all supervised loops"
    echo "  restart  — Restart any dead loops (one-shot, no supervisor)"
    exit 1
    ;;
esac
