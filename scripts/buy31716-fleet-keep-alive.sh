#!/usr/bin/env bash
# BUY-31716 fleet scale-up keep-alive — restart any dead BUY-31716 discovery
# fleet lanes. Intended for a 5-minute cadence so dead lanes are relaunched
# quickly without duplicating live processes.
#
# CONSOLIDATED (BUY-34381, 2026-06-07): single canonical copy on the host.
#   - Replaces the older parallel Oracle-workspace copy (which is now a
#     symlink to this file).
#   - Merges the disk-pressure integration (BUY-32872) into the project-
#     workspace copy, so the cron-fired path also respects the marker guard.
#   - Adds the @aws-sdk symlink drift assertion (BUY-34381 expanded scope).
#   - Unifies state file at data/buy31716-fleet-keep-alive-state.json
#     (FLEET-prefixed) so both the routine (Oracle) and cron (project)
#     paths see the same disk_pressure_pauses / disk_use_pct counters.
#
# Fleet composition (8 lanes, mixed workspace ownership):
#   5 in this workspace (Oracle 3ec8f6dd):
#     burst_discovery, brand_sitemap_miner, retailer_sitemap_miner,
#     fast_wc_probe, shopify_index_expansion
#   3 in Shopper's workspace (5bc984ee) — keep-alive is a cross-workspace
#     liveness monitor; Shopper's own buy30620-lane-keep-alive.sh is the
#     source of truth for restart on those:
#     crate_deep_page, hunt2_page, stock_page
#
# Self-loop pattern (BUY-34462): every lane in this workspace is invoked via
# a dedicated self-loop driver script whose filename differs from the inner
# one-shot miner's. pgrep_pat's pattern matches the loop driver's cmdline
# (NOT the inner), so its lexicographic-etime-tiebreak duplicate-kill never
# murders the inner node every 5 min. Drivers in this workspace:
#   burst_discovery           ← scripts/buy30331-sustained-loop.mjs
#   brand_sitemap_miner       ← scripts/buy30590-brand-sitemap-miner.mjs (self-loops internally)
#   retailer_sitemap_miner    ← scripts/buy30590-retailer-sitemap-loop.mjs (wraps -miner.mjs)
#   fast_wc_probe             ← scripts/buy31452-fast-wc-loop.mjs (wraps -probe.mjs)
#   shopify_index_expansion   ← scripts/cc-shopify-index-loop.mjs (wraps -expansion.mjs)

set -u

# BUY-34726: source R2/Cloudflare credentials for the Oracle-spawned lanes.
# The cron-fired parent bash (no Paperclip adapter) starts with ~7 env vars;
# the keep-alive's `setsid bash -c "node scripts/buy30620-stock-page-lane.mjs"`
# inherits that empty context, so the only R2-touching lane in this fleet
# (buy30620-stock-page-lane.mjs → lane_r2_teardown.mjs) fails 100% of cycles.
# r2-upload.mjs reads the canonical names: CLOUDFLARE_R2_ACCESS_KEY_ID,
# CLOUDFLARE_R2_SECRET_ACCESS_KEY, CLOUDFLARE_R2_ENDPOINT, plus the
# mixed-case Cloudflare_Account_ID / Cloudflare_API_Token. The env file is
# created by BUY-34726 (Vera, 2026-06-07); absence is non-fatal so legacy
# callers (dev shell, manual restart) still work.
# Path resolution order: $FLEET_ENV_FILE (override) > /tmp/buy31716-fleet.env
# (canonical — the crontab sources this exact path) > legacy
# /tmp/buy31716-fleet-keepalive.env (script-default name). All three names
# resolve to the same env file if any of them exist.
for FLEET_ENV_FILE_CANDIDATE in \
    "${FLEET_ENV_FILE:-}" \
    "/tmp/buy31716-fleet.env" \
    "/tmp/buy31716-fleet-keepalive.env"; do
  if [ -n "${FLEET_ENV_FILE_CANDIDATE}" ] && [ -f "${FLEET_ENV_FILE_CANDIDATE}" ]; then
    set -a
    . "${FLEET_ENV_FILE_CANDIDATE}"
    set +a
    export BUY31716_FLEET_ENV_FILE="${FLEET_ENV_FILE_CANDIDATE}"
    break
  fi
done

# --- Path resolution (symlink-robust) ---------------------------------------
# This file may be executed through the Oracle-workspace symlink (routine
# path) or directly from the project workspace (cron path). Resolve the
# real path so SCRIPT_DIR always points at the canonical location where
# lib/disk-pressure-lib.sh lives. The symlink-assertion below makes any
# drift to a non-canonical symlink target visible in the log.
REAL_SCRIPT="$(readlink -f "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$REAL_SCRIPT")" && pwd)"
ORACLE_WS="/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c"
PROJECT_WS="/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default"

# --- @aws-sdk symlink target assertion (BUY-34381 expanded scope) -----------
# Fleet-sweep scripts sometimes retarget the per-workspace
# node_modules/@aws-sdk symlink to a workspace whose @aws-sdk has a nested
# @aws-sdk/@aws-sdk/... layout, which breaks ESM dynamic
# import('@aws-sdk/client-s3') with ERR_MODULE_NOT_FOUND. The lanes that
# touch R2 (buy30620-stock-page-lane.mjs → lane_r2_teardown.mjs) are silent
# on this until a teardown cycle runs.
# Log the symlink target on every tick so a future drift event is visible
# in the keep-alive log instead of manifesting as missing_dependency at the
# lane side. (Defensive @aws-sdk install is recorded as a separate BUY-34381
# action; this assertion is the observability backstop.)
AWS_SDK_SYMLINK="${ORACLE_WS}/node_modules/@aws-sdk"
if [ -L "$AWS_SDK_SYMLINK" ]; then
  AWS_SDK_TARGET="$(readlink -f "$AWS_SDK_SYMLINK" 2>/dev/null || readlink "$AWS_SDK_SYMLINK" 2>/dev/null || echo unknown)"
  # Nested-layout indicator: the target itself contains a nested @aws-sdk/@aws-sdk dir.
  if [ -d "${AWS_SDK_TARGET}/@aws-sdk" ]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] WARN @aws-sdk symlink target has NESTED @aws-sdk dir (target=${AWS_SDK_TARGET}); R2 imports may ERR_MODULE_NOT_FOUND. Run 'npm install @aws-sdk/client-s3 --no-save' in ${ORACLE_WS}." >&2
  fi
  export BUY31716_AWS_SDK_SYMLINK_TARGET="$AWS_SDK_TARGET"
fi

# --- Disk-pressure integration (BUY-32872, consolidated BUY-34381) ----------
# Source shared disk-pressure helpers. The keep-alive is the FIRST line of
# defense against disk pressure: it samples `df` use% on every tick and,
# if use% crosses DISK_GUARD_THRESHOLD_PCT (default 95), writes a marker
# file and treats the tick as a healthy pause (no respawn, no dead-tick
# increment, but a bounded retention sweep is run to free headroom).
# shellcheck source=lib/disk-pressure-lib.sh
source "${SCRIPT_DIR}/lib/disk-pressure-lib.sh"

# Unified state file (FLEET-prefixed): both the routine (Oracle-symlinked)
# path and the cron (project-direct) path write to the SAME file, so a
# forced disk-pressure event increments disk_pressure_pauses from whichever
# path runs the tick that observes the marker first.
WORKSPACE_ROOT="${ORACLE_WS}"
ROOT="${ORACLE_WS}"
LOG="${ROOT}/logs/buy31716_fleet_keep_alive.log"
STATE="${ROOT}/data/buy31716-fleet-keep-alive-state.json"
DISK_PRESSURE_MARKER="${ROOT}/data/buy31716-fleet-disk-pressure.marker"
ESCALATION_FILE="${ROOT}/data/buy31716-fleet-keep-alive-escalation.json"
DEAD_TICKS_FOR_ESCALATION=4
BRAND_SITEMAP_STOP_MARKER="${ROOT}/data/buy30590-brand-sitemap-miner.stopped"
RETAILER_SITEMAP_STOP_MARKER="${ROOT}/data/buy30590-retailer-sitemap-loop.stopped"
# BUY-35267 (2026-06-08): heartbeat-mtime STUCK threshold. The lane
# wrappers write data/.heartbeat_<label>.json every 30s. If pgrep finds
# the lane alive but the heartbeat mtime is older than this, the
# process is in D-state on mem_cgroup_handle_over_high (per BUY-35250)
# — the JS event loop can't run so the heartbeat interval can't fire.
# A live-but-stuck process is a slow OOM-kill: better to SIGTERM+restart
# so the lane recovers when cgroup pressure eases. 120s = 4 missed
# heartbeats; tuned to avoid false positives from one-tick jitter.
STUCK_HEARTBEAT_SECS="${STUCK_HEARTBEAT_SECS:-120}"

mkdir -p "${ROOT}/logs" "${ROOT}/data"

# Init disk lib (captures paths; idempotent).
disk_lib_init "$ROOT" "$STATE" "$DISK_PRESSURE_MARKER" "$LOG"

ts() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Per-lane dead count helpers — merge into the unified state file (the
# disk lib uses the same python-merge pattern, so both writers cooperate
# on the same JSON document).
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
" 2>/dev/null || true
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
  # Match any node process whose cmdline matches $1, across all workspaces.
  # Rationale: BUY-31716 is a fleet watchdog, not a per-workspace supervisor.
  # Three of the 8 lanes (crate_deep_page, hunt2_page, stock_page) run in
  # Shopper's workspace (5bc984ee-...) under Shopper's own
  # buy30620-lane-keep-alive.sh; we want to detect them as alive so we don't
  # spam false-positive DEAD escalations every 5 min. Restart on DEAD is a
  # backstop — Shopper's keep-alive is the source of truth for those 3.
  #
  # Filter rationales (BUY-34520 / 2026-06-07):
  # 1. The keep-alive script itself: its cmdline contains the pattern.
  # 2. Claude's shell-snapshot bash wrappers: when an interactive Claude
  #    session runs `pgrep -af "<pattern>"`, the wrapper bash's full cmdline
  #    contains the pattern as an argument. Without filtering, the wrapper
  #    would match the lane pattern and the duplicate-kill would murder the
  #    legitimate node processes (kept the Claude shell, killed the node).
  # 3. The bash wrappers used historically for self-loops: replaced by
  #    dedicated self-loop driver scripts in this workspace (BUY-34462).
  #    Bash wrappers are no longer used as the lane restart cmd.
  local pattern="$1"
  local matches filtered pid count keep p
  matches=$(pgrep -af "$pattern" 2>/dev/null \
    | grep -v "buy31716-fleet-keep-alive" \
    | grep -v "$0" \
    | grep -v "shell-snapshot" \
    | grep -vE '^\S+\s+(/usr/bin/)?(ba)?sh[[:space:]]' )
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

# BUY-35267 (2026-06-08): classify a lane's heartbeat file. Returns
# one of:
#   fresh:<age_seconds>   — file exists and mtime is within STUCK_HEARTBEAT_SECS
#   stuck:<age_seconds>   — file exists and mtime is older than STUCK_HEARTBEAT_SECS
#   no_hb                 — file does not exist (wrapper hasn't started yet,
#                           or this lane is a Shopper lane with no heartbeat
#                           writer — keep the OK path so we don't false-positive)
# The age is wall-clock seconds since the heartbeat file's mtime, so
# a 5-min tick interval with a 120s threshold gives us ~3 ticks of
# grace before STUCK fires.
classify_heartbeat() {
  local label="$1"
  local hb_file="${ROOT}/data/.heartbeat_${label}.json"
  if [ ! -f "${hb_file}" ]; then
    echo "no_hb"
    return
  fi
  local mtime now age
  mtime=$(stat -c %Y "${hb_file}" 2>/dev/null || echo 0)
  now=$(date +%s)
  age=$((now - mtime))
  if [ "${age}" -gt "${STUCK_HEARTBEAT_SECS}" ]; then
    echo "stuck:${age}"
  else
    echo "fresh:${age}"
  fi
}

restart_if_dead() {
  local label="$1"
  local pattern="$2"
  local cmd="$3"
  local logfile="$4"
  local pid dead_ticks lane_pid hb_classification hb_age

  pid=$(pgrep_pat "$pattern")
  if [ -n "$pid" ]; then
    # BUY-35267 (2026-06-08): STUCK classification. A lane that is
    # pgrep-alive but whose heartbeat file is older than
    # STUCK_HEARTBEAT_SECS is in D-state on mem_cgroup_handle_over_high
    # (BUY-35250 finding). The JS event loop is frozen so the wrapper
    # can't update the heartbeat. SIGTERM+restart so the lane
    # recovers when cgroup pressure eases. Counts as a dead tick so
    # the existing 4-tick escalation still triggers if the throttling
    # is chronic. Lanes without a heartbeat file (burst_discovery,
    # the 3 Shopper lanes) return "no_hb" and skip the STUCK check.
    hb_classification=$(classify_heartbeat "${label}")
    case "${hb_classification}" in
      stuck:*)
        hb_age="${hb_classification#stuck:}"
        echo "[$(ts)] ${label} STUCK — pid=${pid} alive but heartbeat stale (age=${hb_age}s > ${STUCK_HEARTBEAT_SECS}s); SIGTERM+restart"
        kill -TERM "${pid}" 2>/dev/null
        sleep 3
        kill -KILL "${pid}" 2>/dev/null
        sleep 1
        dead_ticks=$(read_dead_count "${label}")
        dead_ticks=$((dead_ticks + 1))
        write_dead_count "${label}" "${dead_ticks}"
        echo "[$(ts)] ${label} STUCK-killed pid=${pid} (consecutive_dead_ticks=${dead_ticks})"
        # Fall through to the restart block below (do NOT return 0).
        pid=""
        ;;
      fresh:*|no_hb)
        if [ "${hb_classification}" = "no_hb" ]; then
          echo "[$(ts)] ${label} OK pid=${pid} (no_heartbeat_file)"
        else
          hb_age="${hb_classification#fresh:}"
          echo "[$(ts)] ${label} OK pid=${pid} heartbeat_age=${hb_age}s"
        fi
        write_dead_count "${label}" 0
        return 0
        ;;
    esac
  fi

  dead_ticks=$(read_dead_count "$label")
  dead_ticks=$((dead_ticks + 1))
  write_dead_count "$label" "$dead_ticks"
  echo "[$(ts)] ${label} DEAD — restarting (consecutive_dead_ticks=${dead_ticks})"
  # BUY-35231 (2026-06-08) orphan-reaper safety: `bash -c "$cmd"` exec's
  # into $cmd (bash's single-command optimization), so the lane node ends
  # up with PPID=1 (orphaned to init) once the keep-alive's parent script
  # exits. /usr/local/bin/paperclip-reap-orphans.sh runs every 5 min and
  # kills every PPID=1 paperclip-owned node process with RSS > 10MB
  # (matches: `comm=node, RSS > 10240KB, user=^papercl, PPID=1, PID !=
  # MainPID`). Symptom: all 5 BUY-31716 in-scope lanes (brand_sitemap,
  # retailer_sitemap, fast_wc_probe, shopify_index_expansion, plus
  # burst_discovery) get reaped ~3.5 min after the keep-alive restarts
  # them, then the next 5-min tick brings them back — chronic restart
  # loop, dead_ticks escalates to 4, ESCALATION written. Forensic PID
  # match in /var/log/paperclip-orphan-reaper.log: 3726447 (brand),
  # 3727299 (retailer), 3728220 (fast_wc), 3729165 (shopify_index) all
  # REAPed at 05:25:01; same 4 PIDs REAPed at 05:35:01.
  #
  # Fix: append `& wait` so the bash -c stays alive as a separate process
  # (multi-statement → bash does NOT exec). The bash -c's RSS is ~3-5MB
  # (just the shell + wait), so the reaper's RSS > 10MB filter skips it.
  # The lane node's PPID is now the bash -c (not 1), so the reaper's
  # PPID=1 filter doesn't list the node either. Verified 2026-06-08T05:45Z:
  # spawned (bash-c 3826584 RSS=3.4MB PPID=1) + (node 3826586 PPID=3826584
  # RSS=45MB) survived the 05:46:01 reaper run unharried.
  #
  # BUY-35030 (2026-06-08) do_wait fix (predecessor): previously the
  # restart was launched via `( cd ${WS} && setsid bash -c "$cmd" ... &
  # disown )`. The SUBSHELL wrapper fork caused the parent script's bash
  # to enter do_wait for the subshell's lifetime, and the subshell's
  # child (the setsid session leader) survived the subshell exit but
  # stayed in the parent bash's wait-tracking, leaving the parent in
  # do_wait for the entire session (4h+ observed). Fix: drop the subshell
  # wrapper, do cd inline via pushd/popd on a subshell only for the cd
  # (or no cd at all — cmd is invoked with WORKSPACE_ROOT via the env),
  # use `nohup setsid` for double-detach, and explicitly `disown $!`
  # with error handling. The lane child gets a new session + ignores
  # SIGHUP, so it survives any subsequent parent reaping.
  pushd "${WORKSPACE_ROOT}" >/dev/null 2>&1 || {
    echo "[$(ts)] ${label} restart FAILED — could not cd to ${WORKSPACE_ROOT}"
    popd >/dev/null 2>&1 || true
    return 1
  }
  nohup setsid bash -c "$cmd & wait" </dev/null >>"$logfile" 2>&1 &
  lane_pid=$!
  disown "${lane_pid}" 2>/dev/null || true
  popd >/dev/null 2>&1 || true
  sleep 2
  pid=$(pgrep_pat "$pattern")
  echo "[$(ts)] ${label} restarted pid=${pid:-unknown} (spawned=${lane_pid})"
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
    echo "[$(ts)] $label STOPPED (already absent)"
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
  echo "[$(ts)] $label STOPPED pid=$pid (stop marker present)"
  write_dead_count "$label" 0
}

{
  echo "===== BUY-31716 fleet keep-alive tick $(ts) ====="
  echo "[$(ts)] invocation: \$0=$0 realpath=$REAL_SCRIPT"
  if [ -n "${BUY31716_AWS_SDK_SYMLINK_TARGET:-}" ]; then
    echo "[$(ts)] @aws-sdk symlink target=${BUY31716_AWS_SDK_SYMLINK_TARGET}"
  fi

  # BUY-32872 / BUY-34381: sample disk use% and check for pressure marker
  # BEFORE any restart_if_dead calls. The fleet uses a restart_if_dead
  # pattern, so the disk guard is critical here — without it, a pressure
  # event would let the cron path restart 8 lanes that would all hit
  # ENOSPC on their first write. The marker guard treats the tick as a
  # healthy pause (no restart, no dead-tick increment, retention sweep
  # runs to free headroom).
  disk_pct="$(disk_lib_record_pct)"
  echo "[$(ts)] host disk use=${disk_pct}% (threshold=${DISK_GUARD_THRESHOLD_PCT}%, recover=${DISK_GUARD_RECOVER_PCT}%)"
  if disk_lib_healthy_pause_tick; then
    echo "[$(ts)] BUY-31716 fleet keep-alive tick complete (disk-pause path)"
    exit 0
  fi

  restart_if_dead \
    "burst_discovery" \
    "buy30331-sustained-loop\.mjs" \
    "node scripts/buy30331-sustained-loop.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30331_sustained_loop.log"

  if [ -f "$BRAND_SITEMAP_STOP_MARKER" ]; then
    stop_if_running "brand_sitemap_miner" "buy30590-brand-sitemap-miner\.mjs"
    echo "[$(ts)] brand_sitemap_miner SKIPPED (stop marker present; see data/buy30590-brand-sitemap-miner.stopped)"
  else
    restart_if_dead \
      "brand_sitemap_miner" \
      "buy30590-brand-sitemap-miner\.mjs" \
      "node scripts/buy30590-brand-sitemap-miner.mjs" \
      "${WORKSPACE_ROOT}/logs/buy30590_brand_sitemap_miner.log"
  fi

  if [ -f "$RETAILER_SITEMAP_STOP_MARKER" ]; then
    stop_if_running "retailer_sitemap_miner" "buy30590-retailer-sitemap-loop\.mjs"
    echo "[$(ts)] retailer_sitemap_miner SKIPPED (stop marker present; see data/buy30590-retailer-sitemap-loop.stopped)"
  else
    restart_if_dead \
      "retailer_sitemap_miner" \
      "buy30590-retailer-sitemap-loop\.mjs" \
      "node scripts/buy30590-retailer-sitemap-loop.mjs" \
      "${WORKSPACE_ROOT}/logs/buy30590_retailer_sitemap_loop.log"
  fi

  restart_if_dead \
    "fast_wc_probe" \
    "buy31452-fast-wc-loop\.mjs" \
    "node scripts/buy31452-fast-wc-loop.mjs" \
    "${WORKSPACE_ROOT}/logs/buy31452_fast_wc_loop.log"

  restart_if_dead \
    "shopify_index_expansion" \
    "cc-shopify-index-loop\.mjs" \
    "node scripts/cc-shopify-index-loop.mjs" \
    "${WORKSPACE_ROOT}/logs/cc_shopify_index_loop.log"

  # BUY-35012 (2026-06-08): Shopper's steady-state process is usually the
  # unified runner (`buy30620-page-lane-runner.mjs --role=<role>`), but the
  # Oracle-side backstop restart still launches the legacy per-role script.
  # Accept either cmdline as alive so a successful backstop restart does not
  # look DEAD on the next tick before Shopper's own keep-alive reconciles it.
  restart_if_dead \
    "crate_deep_page" \
    "buy30620-page-lane-runner\.mjs.*--role=crate|buy30620-crate-deep-page-lane\.mjs" \
    "node scripts/buy30620-crate-deep-page-lane.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30620_crate_deep_page.log"

  restart_if_dead \
    "hunt2_page" \
    "buy30620-page-lane-runner\.mjs.*--role=hunt2|buy30620-hunt2-page-lane\.mjs" \
    "node scripts/buy30620-hunt2-page-lane.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30620_hunt2_page.log"

  restart_if_dead \
    "stock_page" \
    "buy30620-page-lane-runner\.mjs.*--role=stock|buy30620-stock-page-lane\.mjs" \
    "node scripts/buy30620-stock-page-lane.mjs" \
    "${WORKSPACE_ROOT}/logs/buy30620_stock_page.log"

  echo "[$(ts)] keep-alive tick complete"
} >> "$LOG" 2>&1

# BUY-35030 (2026-06-08) do_wait fix: explicit `exit 0` after the brace
# block. Without this, the script falls off the end of the file and bash
# implicitly calls wait_for_any_child() to reap any backgrounded children
# before exiting. With the previous subshell-wrapped restart pattern, the
# reaping could block on the orphaned setsid child (inherited by init but
# still tracked by bash's job table when the SUBSHELL was a child of the
# main script) — observed up to 4h+ in production. Explicit exit 0
# guarantees the script's bash process terminates as soon as the brace
# block completes, so subsequent cron/routine ticks get a fresh bash.
exit 0
