#!/usr/bin/env bash
# BUY-30854 lane keep-alive — restart any dead Oracle discovery/scrape lane.
# Intended for a 5-minute cadence so dead lanes are relaunched quickly without
# duplicating live processes.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${WORKSPACE_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
WORKSPACES_ROOT="${WORKSPACES_ROOT:-/paperclip/instances/default/workspaces}"
LOG="${ROOT}/logs/buy30854_keep_alive.log"
STATE="${ROOT}/data/buy30854-keep-alive-state.json"
ESCALATION_FILE="${ROOT}/data/buy30854-keep-alive-escalation.json"
LOCK_FILE="${ROOT}/data/buy30854-keep-alive.lock"
DEAD_TICKS_FOR_ESCALATION=4
DEEP_PAGE_STOP_MARKER="${ROOT}/data/buy30590-deep-page-loop.stopped"

mkdir -p "${ROOT}/logs" "${ROOT}/data"

ts() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

read_dead_count() {
  local label="$1"
  python3 -c "
import json, os
p='${STATE}'
if not os.path.exists(p):
    print(0)
    raise SystemExit
try:
    data = json.load(open(p))
except Exception:
    data = {}
print(int(data.get('${label}', 0)))
" 2>/dev/null || echo 0
}

write_dead_count() {
  local label="$1"
  local count="$2"
  python3 -c "
import json, os, tempfile
p='${STATE}'
data = {}
if os.path.exists(p):
    try:
        data = json.load(open(p))
    except Exception:
        data = {}
data['${label}'] = ${count}
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix='.buy30854-state.', suffix='.tmp')
with os.fdopen(fd, 'w') as fh:
    fh.write(json.dumps(data, indent=2))
    fh.write('\n')
os.replace(tmp, p)
"
}

delete_state_key() {
  local label="$1"
  python3 -c "
import json, os, tempfile
p='${STATE}'
if not os.path.exists(p):
    raise SystemExit
try:
    data = json.load(open(p))
except Exception:
    data = {}
if '${label}' not in data:
    raise SystemExit
del data['${label}']
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix='.buy30854-state.', suffix='.tmp')
with os.fdopen(fd, 'w') as fh:
    fh.write(json.dumps(data, indent=2))
    fh.write('\n')
os.replace(tmp, p)
" 2>/dev/null || true
}

prune_legacy_lane_counts() {
  local label
  for label in \
    "buy30745_substrate_supervisor" \
    "buy33243_custom_domain_supervisor"
  do
    delete_state_key "$label"
  done
}

record_escalation() {
  local label="$1"
  local count="$2"
  python3 -c "
import json, os, tempfile
p='${ESCALATION_FILE}'
data = {'escalations': []}
if os.path.exists(p):
    try:
        data = json.load(open(p))
    except Exception:
        data = {'escalations': []}
data['escalations'].append({
    'lane': '${label}',
    'dead_ticks': ${count},
    'at': '$(ts)',
    'note': 'lane DEAD on >=${DEAD_TICKS_FOR_ESCALATION} consecutive keep-alive ticks; escalate to parent BUY-30854 with diagnostic context'
})
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix='.buy30854-escalation.', suffix='.tmp')
with os.fdopen(fd, 'w') as fh:
    fh.write(json.dumps(data, indent=2))
    fh.write('\n')
os.replace(tmp, p)
"
}

root_from_pid() {
  local pid="$1"
  local cwd=""
  cwd=$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)
  if [ -n "$cwd" ]; then
    echo "$cwd"
  fi
}

discover_lane_root_from_processes() {
  local pattern="$1"
  local matches pid root
  matches=$(pgrep -af "$pattern" 2>/dev/null | grep -v "buy30854-lane-keep-alive" | grep -v "$0" || true)
  [ -n "$matches" ] || return 0

  while IFS= read -r line; do
    [ -n "$line" ] || continue
    pid=$(echo "$line" | awk '{print $1}')
    [ -n "$pid" ] || continue
    root=$(root_from_pid "$pid")
    if [ -n "$root" ]; then
      echo "$root"
      return 0
    fi
  done <<< "$matches"
}

discover_lane_root() {
  local script_name="$1"
  local pattern="$2"
  local candidate root

  if [ -f "${ROOT}/scripts/${script_name}" ]; then
    echo "${ROOT}"
    return 0
  fi

  root=$(discover_lane_root_from_processes "$pattern")
  if [ -n "$root" ] && [ -f "${root}/scripts/${script_name}" ]; then
    echo "$root"
    return 0
  fi

  for candidate in "${WORKSPACES_ROOT}"/*/scripts/"${script_name}"; do
    [ -e "$candidate" ] || continue
    dirname "$(dirname "$candidate")"
    return 0
  done

  echo "${ROOT}"
}

pgrep_pat() {
  local pattern="$1"
  local matches filtered pid count keep p
  matches=$(pgrep -af "$pattern" 2>/dev/null \
    | grep -vE "^\S+\s+((/usr/bin|/bin)/)?(ba)?sh\b" \
    | grep -vE "\.claude/shell-snapshots" \
    | grep -v "buy30854-lane-keep-alive" \
    | grep -v "$0" \
    || true)
  filtered=""
  if [ -z "$matches" ]; then
    echo ""
    return
  fi

  while IFS= read -r line; do
    [ -z "$line" ] && continue
    pid=$(echo "$line" | awk '{print $1}')
    [ -z "$pid" ] && continue
    filtered+="${pid}"$'\n'
  done <<< "$matches"

  filtered=$(echo "$filtered" | sed '/^$/d')
  if [ -z "$filtered" ]; then
    echo ""
    return
  fi

  count=$(echo "$filtered" | wc -l | tr -d ' ')
  if [ "$count" -gt 1 ]; then
    keep=$(for p in $filtered; do
      local etimes
      etimes=$(ps -p "$p" -o etimes= 2>/dev/null | tr -d ' ')
      [ -n "$etimes" ] && echo "$etimes $p"
    done | sort -n | head -1 | awk '{print $2}')
    for p in $filtered; do
      if [ "$p" != "$keep" ]; then
        kill "$p" 2>/dev/null && echo "[$(ts)] duplicate $pattern killed pid=$p (kept $keep)" >> "$LOG"
      fi
    done
    echo "$keep"
  else
    echo "$filtered"
  fi
}

restart_if_dead() {
  local label="$1"
  local pattern="$2"
  local script_name="$3"
  local cmd="$4"
  local logfile="$5"
  local pid dead_ticks lane_root lane_pid

  pid=$(pgrep_pat "$pattern")
  if [ -n "$pid" ]; then
    echo "[$(ts)] ${label} OK pid=${pid}"
    write_dead_count "$label" 0
    return 0
  fi

  dead_ticks=$(read_dead_count "$label")
  dead_ticks=$((dead_ticks + 1))
  write_dead_count "$label" "$dead_ticks"
  echo "[$(ts)] ${label} DEAD — restarting (consecutive_dead_ticks=${dead_ticks})"
  lane_root=$(discover_lane_root "$script_name" "$pattern")
  if [ ! -f "${lane_root}/scripts/${script_name}" ]; then
    echo "[$(ts)] ${label} restart failed — missing ${script_name} under ${lane_root}"
    return 0
  fi
  pushd "${lane_root}" >/dev/null 2>&1 || {
    echo "[$(ts)] ${label} restart failed — could not cd to ${lane_root}"
    return 0
  }
  # Close the keep-alive flock before launching the detached lane so the
  # restarted node cannot inherit FD 9 and pin the watchdog lock.
  nohup setsid bash -lc "exec 9>&-; $cmd & wait" >> "$logfile" 2>&1 < /dev/null &
  lane_pid=$!
  disown "${lane_pid}" 2>/dev/null || true
  popd >/dev/null 2>&1 || true
  sleep 2
  pid=$(pgrep_pat "$pattern")
  echo "[$(ts)] ${label} restarted pid=${pid:-unknown} root=${lane_root} spawned=${lane_pid}"
  if [ -n "$pid" ]; then
    # A successful relaunch clears the consecutive-dead streak so we only
    # escalate when the watchdog cannot revive the lane across ticks.
    write_dead_count "$label" 0
    return 0
  fi
  if [ "$dead_ticks" -ge "$DEAD_TICKS_FOR_ESCALATION" ]; then
    record_escalation "$label" "$dead_ticks"
    echo "[$(ts)] ${label} ESCALATED — consecutive_dead_ticks=${dead_ticks} >= ${DEAD_TICKS_FOR_ESCALATION}; written to ${ESCALATION_FILE}"
  fi
}

stop_if_running() {
  local label="$1"
  local pattern="$2"
  local pid
  pid=$(pgrep_pat "$pattern")
  if [ -z "$pid" ]; then
    echo "[$(ts)] ${label} STOPPED (already absent)"
    write_dead_count "$label" 0
    return 0
  fi
  kill "$pid" 2>/dev/null || true
  sleep 1
  local residual
  residual=$(pgrep_pat "$pattern")
  if [ -n "$residual" ]; then
    kill -9 "$residual" 2>/dev/null || true
    sleep 1
  fi
  echo "[$(ts)] ${label} STOPPED pid=${pid} (stop marker present)"
  write_dead_count "$label" 0
}

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "[$(ts)] keep-alive tick skipped — another instance already holds ${LOCK_FILE}" >> "$LOG"
  exit 0
fi

{
  echo "===== keep-alive tick $(ts) ====="
  prune_legacy_lane_counts

  if [ -f "${DEEP_PAGE_STOP_MARKER}" ]; then
    stop_if_running "deep_page_loop" "buy30590-deep-page-loop.mjs"
    echo "[$(ts)] deep_page_loop SKIPPED (stop marker present; see data/buy30590-deep-page-loop.stopped)"
  else
    restart_if_dead \
      "deep_page_loop" \
      "buy30590-deep-page-loop.mjs" \
      "buy30590-deep-page-loop.mjs" \
      "node scripts/buy30590-deep-page-loop.mjs" \
      "${ROOT}/logs/buy30590_deep_page_loop.log"
  fi

  restart_if_dead \
    "sustained_loop" \
    "buy30331-sustained-loop.mjs" \
    "buy30331-sustained-loop.mjs" \
    "node scripts/buy30331-sustained-loop.mjs" \
    "${ROOT}/logs/buy30331_sustained_loop.log"

  if [ ! -f "${ROOT}/data/checkpoints/buy30590_woocommerce.completed" ]; then
    restart_if_dead \
      "woocommerce_discover" \
      "buy30590-woocommerce-discover.mjs" \
      "buy30590-woocommerce-discover.mjs" \
      "node scripts/buy30590-woocommerce-discover.mjs --start=0 --count=10000 --concurrency=40" \
      "${ROOT}/logs/buy30590_woocommerce_discover.log"
  else
    write_dead_count "woocommerce_discover" 0
    echo "[$(ts)] woocommerce_discover SKIPPED (completion marker present; see data/checkpoints/buy30590_woocommerce.completed)"
  fi

  if [ -f "${ROOT}/data/buy30727-supervisor.stopped" ]; then
    write_dead_count "lane_supervisor" 0
    echo "[$(ts)] lane_supervisor SKIPPED (BUY-31452 stop marker present; see data/buy30727-supervisor.stopped)"
  else
    restart_if_dead \
      "lane_supervisor" \
      "buy30727-lane-supervisor.mjs" \
      "buy30727-lane-supervisor.mjs" \
      "node scripts/buy30727-lane-supervisor.mjs" \
      "${ROOT}/logs/buy30727_supervisor.log"
  fi

  echo "[$(ts)] keep-alive tick complete"
} >> "$LOG" 2>&1
