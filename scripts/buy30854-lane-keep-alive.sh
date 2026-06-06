#!/usr/bin/env bash
# BUY-30854 lane keep-alive watchdog
# Checks buy30590-deep-page-loop, buy30331-sustained-loop,
# buy30590-woocommerce-discover, buy30727-lane-supervisor.
# Restarts any dead process. Idempotent — never duplicates.

WORKSPACE="/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/buy30854_keep_alive.log"
TICK="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

mkdir -p "${PROJECT_ROOT}/logs"

log() { echo "[${TICK}] $*" | tee -a "${LOG_FILE}"; }

check_lane() {
    local name="$1"
    local extra_args="${2:-}"
    local completed_marker="${3:-}"

    if [[ -n "${completed_marker}" && -f "${completed_marker}" ]]; then
        log "COMPLETED ${name} (discovery finished, no restart needed)"
        return 0
    fi

    # pgrep pattern: match the bare filename so both `node scripts/<name>` (relative
    # path, used by our own restarts) and `node /abs/path/scripts/<name>` (absolute
    # path, used by hand/legacy starts) are detected. Matching `node scripts/<name>`
    # alone would MISS the long-lived absolute-path processes and cause duplicate
    # restarts that die in the heartbeat-cgroup window. Filename-only matches both.
    if pgrep -af "${name}" | grep -v "buy30854-lane-keep-alive" | grep -v "/bin/bash" > /dev/null 2>&1; then
        local pid; pid=$(pgrep -af "${name}" | grep -v "buy30854-lane-keep-alive" | grep -v "/bin/bash" | awk '{print $1}' | head -1)
        log "ALIVE ${name} pid=${pid}"
    else
        log "DEAD ${name} — restarting"
        cd "${WORKSPACE}"
        nohup node "scripts/${name}" ${extra_args} \
            >> "${WORKSPACE}/logs/${name%.mjs}_keepalive.log" 2>&1 &
        log "RESTARTED ${name} pid=$!"
    fi
}

log "=== BUY-30854 keep-alive tick ==="
check_lane "buy30590-deep-page-loop.mjs"
check_lane "buy30331-sustained-loop.mjs"
check_lane "buy30590-woocommerce-discover.mjs" "" \
    "${WORKSPACE}/data/checkpoints/buy30590_woocommerce.completed"
check_lane "buy30727-lane-supervisor.mjs"
log "=== tick done ==="
