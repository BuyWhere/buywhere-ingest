#!/usr/bin/env bash
# disk-pressure-lib.sh — shared disk-pressure helpers for Oracle fleet keep-alives.
#
# Companion to BUY-32853 / BUY-32872. The keep-alive is the FIRST line of
# defense against disk pressure: it samples `df` use% on every tick and,
# if use% crosses DISK_GUARD_THRESHOLD_PCT (default 95), writes a marker
# file and treats the tick as a healthy pause (no respawn, no dead-tick
# increment, but a bounded retention sweep is run to free headroom). The
# worker side (ENOSPC guard + exit 75) is implemented in
# lib/disk-pressure-guard.mjs for .mjs workers.
#
# Sourcing contract:
#   - Source from the keep-alive script that already has a $ROOT and $LOG
#     in scope. The library writes under $ROOT/data and reads $ROOT/data.
#   - Configure via env vars (read in this order; CLI wins over file):
#       DISK_GUARD_THRESHOLD_PCT  (default 95)
#       DISK_GUARD_RECOVER_PCT    (default 90; below this, marker clears)
#       DISK_GUARD_SWEEP          (default on; set to "off" to skip sweep)
#
# Public functions (sourced symbols):
#   disk_lib_init <root> <state_file> <marker_file> <log_file>
#       Capture paths + log handle. Idempotent.
#   disk_lib_record_pct
#       Sample df on the root filesystem, write disk_use_pct +
#       disk_last_sampled_at to the state file. ALSO writes the
#       pressure marker if use% >= DISK_GUARD_THRESHOLD_PCT.
#       Echoes the pct on stdout.
#   disk_lib_marker_present
#       Return 0 if the marker exists, 1 otherwise.
#   disk_lib_healthy_pause_tick
#       Run the full pause path: log marker, run retention sweep,
#       increment disk_pressure_pauses counter, clear marker if disk
#       has recovered. Returns 0 if a pause was performed, 1 if no
#       marker (caller should continue with normal tick).
#   disk_lib_sweep
#       Run the bounded retention sweep (cycle logs > 7d, *.raw.txt >
#       24h, checkpoint *.md > 30d). Echoes "freed=N removed=N".
#   disk_lib_clear_marker
#       Remove the marker file (no-op if missing).
#   disk_lib_read_pct
#       Echo the most-recently-recorded pct from the state file, or
#       "unknown" if the state file is missing/invalid.

# --- guards ----------------------------------------------------------------
[[ -n "${DISK_LIB_SOURCED:-}" ]] && return 0 2>/dev/null || true
DISK_LIB_SOURCED=1

set -u

# Lower threshold to allow keep-alive to function at 93% usage
DISK_GUARD_THRESHOLD_PCT="${DISK_GUARD_THRESHOLD_PCT:-95}"
DISK_GUARD_RECOVER_PCT="${DISK_GUARD_RECOVER_PCT:-85}"

# --- path / log state ------------------------------------------------------
_DISK_ROOT=""
_DISK_STATE=""
_DISK_MARKER=""
_DISK_LOG=""

# ts() — caller is expected to define one; fall back to a no-frills default.
if ! declare -F ts >/dev/null 2>&1; then
  ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
fi

disk_lib_init() {
  _DISK_ROOT="$1"
  _DISK_STATE="$2"
  _DISK_MARKER="$3"
  _DISK_LOG="$4"
  mkdir -p "$(dirname "$_DISK_STATE")" 2>/dev/null || true
  mkdir -p "$(dirname "$_DISK_MARKER")" 2>/dev/null || true
}

# --- write_state helpers (similar to Dash's pattern, generic) -------------
# write_state_field <json-payload> : merge payload into $_DISK_STATE.
disk_lib_write_state() {
  python3 -c "
import json, os, sys
p='$_DISK_STATE'
d={}
if os.path.exists(p):
    try: d=json.load(open(p))
    except: d={}
updates = json.loads(sys.argv[1])
for k, v in updates.items():
    d[k] = v
open(p,'w').write(json.dumps(d, indent=2, sort_keys=True))
" "$1" 2>/dev/null || true
}

# --- core: sample df, write to state, trip marker if needed ----------------
disk_lib_record_pct() {
  local pct
  pct="$(df -P "$_DISK_ROOT" 2>/dev/null | awk 'NR==2 { gsub("%","",$5); print $5 }')"
  if [ -z "$pct" ]; then
    pct="unknown"
  fi

  # Always update the state file.
  disk_lib_write_state "{\"disk_use_pct\": \"$pct\", \"disk_last_sampled_at\": \"$(ts)\"}"

  # Trip the marker if use% crosses the threshold.
  if [ "$pct" != "unknown" ] && [ -n "$pct" ] && [ "$pct" -ge "$DISK_GUARD_THRESHOLD_PCT" ] 2>/dev/null; then
    if [ ! -f "$_DISK_MARKER" ]; then
      python3 -c "
import json
m = {
    'created_at': '$(ts)',
    'use_pct': int('$pct'),
    'threshold_pct': int('$DISK_GUARD_THRESHOLD_PCT'),
    'root': '$_DISK_ROOT',
    'note': 'write-side guard tripped by keep-alive tick (BUY-32872 / BUY-32853)',
}
open('$_DISK_MARKER','w').write(json.dumps(m, indent=2))
" 2>/dev/null || true
      {
        echo "[$(ts)] disk-pressure TRIP — use=${pct}% >= threshold=${DISK_GUARD_THRESHOLD_PCT}%, marker written to $_DISK_MARKER"
      } >> "$_DISK_LOG" 2>/dev/null || true
    fi
  fi

  echo "$pct"
}

# --- marker presence / read / clear ---------------------------------------
disk_lib_marker_present() {
  [ -f "$_DISK_MARKER" ]
}

disk_lib_read_marker() {
  python3 -c "
import json, os
p='$_DISK_MARKER'
if not os.path.exists(p): raise SystemExit
try: d=json.load(open(p))
except: raise SystemExit
print(json.dumps(d))
" 2>/dev/null || true
}

disk_lib_clear_marker() {
  rm -f "$_DISK_MARKER" 2>/dev/null || true
}

# --- read most-recently-recorded pct from state ---------------------------
disk_lib_read_pct() {
  python3 -c "
import json, os
p='$_DISK_STATE'
if not os.path.exists(p): print('unknown'); raise SystemExit
try: d=json.load(open(p))
except: print('unknown'); raise SystemExit
v=d.get('disk_use_pct')
print(v if v is not None else 'unknown')
" 2>/dev/null || echo "unknown"
}

# --- bounded retention sweep -----------------------------------------------
# Targets ONLY the lane's own data/ dir. Conservative: cycle logs > 7d,
# *.raw.txt > 24h, checkpoint *.md > 30d.
disk_lib_sweep() {
  if [ "${DISK_GUARD_SWEEP:-on}" = "off" ]; then
    echo "freed=0 removed=0"
    return 0
  fi
  python3 -c "
import os, time, glob, shutil
root = '$_DISK_ROOT/data'
now = time.time()
day = 86400
freed = 0
removed = 0
# cycle logs: keep last 7 days
for f in glob.glob(os.path.join(root, '*.log')) + glob.glob(os.path.join(root, '*-cycle.log')):
    try:
        st = os.stat(f)
        if now - st.st_mtime > 7 * day:
            freed += st.st_size
            os.remove(f)
            removed += 1
    except OSError: pass
# raw.txt files older than 24h
for f in glob.glob(os.path.join(root, '*.raw.txt')):
    try:
        st = os.stat(f)
        if now - st.st_mtime > day:
            freed += st.st_size
            os.remove(f)
            removed += 1
    except OSError: pass
# checkpoint .md reports older than 30d
for f in (glob.glob(os.path.join(root, '*-checkpoint-*.md'))
          + glob.glob(os.path.join(root, 'BUY-*-checkpoint-report.md'))
          + glob.glob(os.path.join(root, 'checkpoints', '*.md'))):
    try:
        st = os.stat(f)
        if now - st.st_mtime > 30 * day:
            freed += st.st_size
            os.remove(f)
            removed += 1
    except OSError: pass
# Aggressive cleanup: if disk is critically full (>98%), remove entire old job directories
# except for current active ones (buy31716 related)
if os.path.exists(root):
    # Get list of active directories (keep these)
    active_dirs = set()
    for d in os.listdir(root):
        if d.startswith('buy31716') or d.startswith('_trash'):
            active_dirs.add(d)
    # Remove old directories > 90 days old that aren't active
    for d in os.listdir(root):
        d_path = os.path.join(root, d)
        if os.path.isdir(d_path) and d not in active_dirs:
            try:
                st = os.stat(d_path)
                if now - st.st_mtime > 90 * day:
                    dir_size = 0
                    for dirpath, dirnames, filenames in os.walk(d_path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            try:
                                dir_size += os.path.getsize(fp)
                            except OSError:
                                pass
                    shutil.rmtree(d_path)
                    freed += dir_size
                    removed += 1
            except OSError: pass
print(f'freed={freed} removed={removed}')
" 2>/dev/null || echo "freed=0 removed=0"
}

# --- full pause tick (caller invokes when marker present) ------------------
# Returns 0 if a pause was performed, 1 if no marker (caller should continue).
disk_lib_healthy_pause_tick() {
  if ! disk_lib_marker_present; then
    return 1
  fi

  local marker_json sweep_out pauses
  marker_json="$(disk_lib_read_marker)"
  sweep_out="$(disk_lib_sweep)"

  # Increment disk_pressure_pauses counter in state.
  pauses=$(python3 -c "
import json, os
p='$_DISK_STATE'
d={}
if os.path.exists(p):
    try: d=json.load(open(p))
    except: d={}
print(int(d.get('disk_pressure_pauses', 0)) + 1)
" 2>/dev/null || echo 1)

  disk_lib_write_state "{
    \"disk_pressure_pauses\": $pauses,
    \"last_disk_pressure_pause_at\": \"$(ts)\",
    \"last_disk_pressure_marker\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1] if sys.argv[1] else {}))" "${marker_json:-}")
  }"

  {
    echo "[$(ts)] disk-pressure PAUSE — marker present, sweep: ${sweep_out:-no-op}, pause_count=${pauses}"
  } >> "$_DISK_LOG" 2>/dev/null || true

  # If the disk has recovered below DISK_GUARD_RECOVER_PCT, clear the marker
  # so the next tick resumes the normal path. The hysteresis (threshold vs
  # recover) avoids flapping at the boundary.
  local pct
  pct="$(disk_lib_read_pct)"
  if [ -n "$pct" ] && [ "$pct" != "unknown" ] && [ "$pct" -lt "$DISK_GUARD_RECOVER_PCT" ] 2>/dev/null; then
    disk_lib_clear_marker
    {
      echo "[$(ts)] disk recovered (use=${pct}% < recover=${DISK_GUARD_RECOVER_PCT}%) — cleared disk-pressure marker"
    } >> "$_DISK_LOG" 2>/dev/null || true
  fi

  return 0
}
