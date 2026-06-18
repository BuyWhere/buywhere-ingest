#!/usr/bin/env bash
# cleanup-teardown.sh — Cycle teardown wrapper for safe-data-cleanup.sh.
# BUY-33094: Wire safe-data-cleanup.sh into scrape teardown + 6-hourly sweep.
#
# Invoked at the end of a scrape/ingest cycle (or from a 6-hourly cron/systemd
# sweep) to trundle a workspace's data/ down to the 5 GB budget without ever
# removing un-ingested or in-flight material.
#
# Usage:
#   bash cleanup-teardown.sh <workspace_path> [--apply] [--grace=H] [--timeout=S]
#
# - <workspace_path> is the agent workspace root (e.g. .../workspaces/<agent-id>).
#   The script uses <workspace>/data/ as the cleanup target.
# - Default is dry-run (safe). Pass --apply to actually move old confirmed files
#   into <data>/_trash/<date>/.
# - Failures are logged but the wrapper exits 0 so it never blocks the parent
#   cycle (per BUY-33094 acceptance: "failures are logged but do not block").
# - Per-workspace concurrency caps and 6-hourly jitter are enforced by the
#   caller (systemd timer/routine); this wrapper is a single-shot worker.
# - Logs are appended to <workspace>/logs/data-cleanup.log so the cycle report
#   ends up in the standard location for the workspace's owning agent.
# - SAFETY: The catalog sample (Gate B3) and lsof (Gate A2) are NEVER skipped
#   by default. Skipping them is opt-in via env vars, and only for the
#   per-cycle teardown where the calling scraper has its own freshness
#   guarantees. The 6-hourly fleet sweep NEVER skips them. This avoids
#   mass-trashing of un-ingested data when the catalog check is the only
#   safety net.

set -uo pipefail

WS="${1:-}"
shift || true
APPLY=0
GRACE_H=""
TIMEOUT_S=600
# Skips default to OFF. Override via env for performance-critical paths.
SKIP_LSOF="${CLEANUP_SKIP_LSOF:-0}"
SKIP_CATALOG="${CLEANUP_SKIP_CATALOG:-0}"
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --grace=*) GRACE_H=${a#*=} ;;
    --timeout=*) TIMEOUT_S=${a#*=} ;;
  esac
done

if [ -z "$WS" ] || [ ! -d "$WS" ]; then
  echo "ABORT: workspace path missing or not a directory: '$WS'" >&2
  exit 0
fi

DATA_DIR="$WS/data"
LOG_DIR="$WS/logs"
LOG_FILE="$LOG_DIR/data-cleanup.log"
CLEANUP_SCRIPT="$WS/safe-data-cleanup.sh"

mkdir -p "$LOG_DIR"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# Single one-line cycle report the 6-hourly sweep posts to the housekeeping
# channel. Per BUY-33094 acceptance: "one-line cycle report".
report_line=""

log_to_file() {
  local line="[$(ts)] $*"
  echo "$line" | tee -a "$LOG_FILE" >/dev/null
  echo "$line" >&2
}

# Capture the wrapper exit logic — never propagate non-zero from the inner
# script because the parent cycle must not block on cleanup failures.
run_cleanup() {
  local start end dur
  start=$(date +%s)
  log_to_file "teardown start workspace=$WS apply=$APPLY grace=${GRACE_H:-default} skip_lsof=$SKIP_LSOF skip_catalog=$SKIP_CATALOG"

  if [ ! -x "$CLEANUP_SCRIPT" ] && [ ! -f "$CLEANUP_SCRIPT" ]; then
    log_to_file "SKIP: safe-data-cleanup.sh not found at $CLEANUP_SCRIPT"
    report_line="cleanup SKIP: missing safe-data-cleanup.sh"
    return 0
  fi

  local args=()
  [ "$APPLY" = 1 ] && args+=(--apply)
  [ -n "$GRACE_H" ] && args+=(--grace="$GRACE_H")
  # BUY-33094: --skip-r2 is still the default for the 6-hourly fleet sweep
  # (R2-marker durability layer BUY-33089 + uploader BUY-33090 are in flight).
  # The bypass is opt-out for raw scrape files: those live in data/buy*/ and
  # carry the same durably-stored risk that the 2026-06-07 incident surfaced
  # (1.6GB buy30620_scout_full_scrape moved to _trash on catalog-sample alone,
  # with the live scraper still rotating files in the same directory). For
  # raw files we require a sibling <file>.ingested.json R2 marker, regardless
  # of the global --skip-r2 toggle. data/ingested/ and the canonical widening
  # batches already have their own ingestion signal, so they keep the bypass.
  #
  # Override:
  #   CLEANUP_REQUIRE_R2=1            -> require R2 for ALL files (strict)
  #   CLEANUP_REQUIRE_R2_FOR_RAW=0    -> skip R2 even for raw (legacy, not recommended)
  if [ "${CLEANUP_REQUIRE_R2:-0}" != "1" ]; then
    if [ "${CLEANUP_REQUIRE_R2_FOR_RAW:-1}" = "1" ]; then
      # New policy: --skip-r2 globally is OK, but raw files get a stricter
      # check at the gate layer. safe-data-cleanup.sh honors
      # CLEANUP_REQUIRE_R2_FOR_RAW (default 1) by refusing to delete a raw
      # file without a sibling .ingested.json R2 marker, even when --skip-r2
      # is set. This honors the "do not delete files that have not been
      # ingested" constraint from BUY-32838.
      export CLEANUP_REQUIRE_R2_FOR_RAW=1
    fi
    args+=(--skip-r2)
  fi
  [ "$SKIP_LSOF" = 1 ] && args+=(--skip-lsof)
  [ "$SKIP_CATALOG" = 1 ] && args+=(--skip-catalog-check)

  # Wrap in timeout to keep teardown bounded. Use `timeout` from coreutils.
  local out
  if out=$(timeout "$TIMEOUT_S" bash "$CLEANUP_SCRIPT" "$DATA_DIR" "${args[@]}" 2>&1); then
    :
  else
    local rc=$?
    log_to_file "WARN: safe-data-cleanup.sh exited rc=$rc (logged but not blocking)"
  fi
  # Always log the script's output, even on success, so we have a per-cycle trail.
  if [ -n "$out" ]; then
    while IFS= read -r ln; do
      [ -n "$ln" ] && log_to_file "  | $ln"
    done <<< "$out"
  fi

  end=$(date +%s)
  dur=$(( end - start ))

  # Build the one-line cycle report from the script's own summary line if any.
  local summary
  summary=$(printf '%s\n' "$out" | grep -E '^--- ' | tail -1)
  if [ -z "$summary" ]; then
    summary="(no summary line — nothing eligible in dry-run, or timeout)"
  fi
  report_line="[$WS] cleaned $(printf '%s' "$summary" | sed 's/^--- //') dur=${dur}s apply=$APPLY"
  log_to_file "teardown done $report_line"
}

run_cleanup

# Echo a final one-line report on stdout so the caller (systemd, cron, or the
# scraper loop's spawnSync) can capture and surface it.
echo "$report_line"

exit 0
