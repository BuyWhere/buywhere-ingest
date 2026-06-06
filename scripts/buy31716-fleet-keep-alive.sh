#!/usr/bin/env bash
# BUY-31716 fleet keep-alive — restart any dead BUY-31716 discovery fleet lanes.
# Intended for a 5-minute cadence so dead lanes are relaunched quickly without
# duplicating live processes.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${WORKSPACE_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c}"
LOG="${ROOT}/logs/buy31716_keep_alive.log"
STATE="${ROOT}/data/buy31716-keep-alive-state.json"
ESCALATION_FILE="${ROOT}/data/buy31716-keep-alive-escalation.json"
DEAD_TICKS_FOR_ESCALATION=4

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
import json, os
p='${STATE}'
data = {}
if os.path.exists(p):
    try:
        data = json.load(open(p))
    except Exception:
        data = {}
data['${label}'] = ${count}
open(p, 'w').write(json.dumps(data, indent=2))
"
}

record_escalation() {
  local label="$1"
  local count="$2"
  python3 -c "
import json, os
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
    'note': 'lane DEAD on >=${DEAD_TICKS_FOR_ESCALATION} consecutive keep-alive ticks; escalate with diagnostic context'
})
open(p, 'w').write(json.dumps(data, indent=2))
"
}

pgrep_pat() {
  local pattern="$1"
  local matches filtered pid cwd count keep p
  matches=$(pgrep -af "$pattern" 2>/dev/null | grep -v "buy31716-fleet-keep-alive" | grep -v "$0")
  filtered=""
  if [ -z "$matches" ]; then
    echo ""
    return
  fi

  while IFS= read -r line; do
    [ -z "$line" ] && continue
    pid=$(echo "$line" | awk '{print $1}')
    [ -z "$pid" ] && continue
    cwd=""
    if [ -L "/proc/$pid/cwd" ]; then
      cwd=$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)
    fi
    if [[ "$line" == *"${WORKSPACE_ROOT}"* ]] || [ "$cwd" = "${WORKSPACE_ROOT}" ]; then
      filtered+="${pid}"$'\n'
    fi
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
  local cmd="$3"
  local logfile="$4"
  local pid dead_ticks

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
  (
    cd "${WORKSPACE_ROOT}" &&
    nohup bash -c "$cmd" >> "$logfile" 2>&1 < /dev/null &
    disown
  )
  sleep 2
  pid=$(pgrep_pat "$pattern")
  echo "[$(ts)] ${label} restarted pid=${pid:-unknown}"
  if [ "$dead_ticks" -ge "$DEAD_TICKS_FOR_ESCALATION" ]; then
    record_escalation "$label" "$dead_ticks"
    echo "[$(ts)] ${label} ESCALATED — consecutive_dead_ticks=${dead_ticks} >= ${DEAD_TICKS_FOR_ESCALATION}; written to ${ESCALATION_FILE}"
  fi
}

{
  echo "===== keep-alive tick $(ts) ====="

  restart_if_dead \
    "burst_discovery" \
    "buy30331-burst-discovery\.mjs" \
    "node scripts/buy30331-burst-discovery.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30331_burst_discovery.log"

  restart_if_dead \
    "brand_sitemap_miner" \
    "buy30590-brand-sitemap-miner\.mjs" \
    "node scripts/buy30590-brand-sitemap-miner.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30590_brand_sitemap_miner.log"

  restart_if_dead \
    "retailer_sitemap_miner" \
    "buy30590-retailer-sitemap-miner\.mjs" \
    "node scripts/buy30590-retailer-sitemap-miner.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30590_retailer_sitemap_miner.log"

  restart_if_dead \
    "fast_wc_probe" \
    "buy31452-fast-wc-probe\.mjs" \
    "node scripts/buy31452-fast-wc-probe.mjs" \
    "${WORKSPACE_ROOT}/logs/buy31452_fast_wc_probe.log"

  restart_if_dead \
    "shopify_index_expansion" \
    "cc-shopify-index-expansion\.mjs" \
    "node scripts/cc-shopify-index-expansion.mjs" \
    "${WORKSPACE_ROOT}/logs/cc_shopify_index_expansion.log"

  restart_if_dead \
    "crate_deep_page" \
    "buy30620-crate-deep-page-lane\.mjs" \
    "node scripts/buy30620-crate-deep-page-lane.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30620_crate_deep_page.log"

  restart_if_dead \
    "hunt2_page" \
    "buy30620-hunt2-page-lane\.mjs" \
    "node scripts/buy30620-hunt2-page-lane.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30620_hunt2_page.log"

  restart_if_dead \
    "stock_page" \
    "buy30620-stock-page-lane\.mjs" \
    "node scripts/buy30620-stock-page-lane.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30620_stock_page.log"

  echo "[$(ts)] keep-alive tick complete"
} >> "$LOG" 2>&1
