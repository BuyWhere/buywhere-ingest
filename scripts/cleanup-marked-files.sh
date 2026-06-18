#!/usr/bin/env bash
# cleanup-marked-files.sh — Focused one-shot cleanup of files that already
# have a sibling <file>.ingested.json marker with a "key" field.
#
# This is the BUY-32826 fast path: it does NOT call the catalog DB. The
# R2 marker is the durable proof of upload, and the catalog check (B3) is
# the bottleneck (per-file JOINs on a 36M products table currently time
# out at 60s when the DB is loaded with backfill/VACUUM work).
#
# Safety:
#   - Requires a non-empty <file>.ingested.json with a JSON "key" field.
#   - Requires the data file to be mtime-stable (>= --grace hours old) so
#     we never trash a file the active ingester is still rotating.
#   - Skips files where lsof reports an open handle (per Gate A2).
#   - Skips _trash, checkpoints, ingest_ready, merchants subdirs.
#   - Two-phase trash: file AND its marker go to data/_trash/<date>/ with
#     the same relative path, 48h recovery window (raw buy* files get
#     7-day grace per the BUY-32838 hardening).
#
# Usage:
#   bash cleanup-marked-files.sh <workspace_path> [--apply] [--grace=H]
#
# Default is dry-run. --apply actually moves files.
#
# This complements safe-data-cleanup.sh: that script handles files
# without markers (via catalog sampling); this one handles the ~4500+
# files that already have markers and don't need the slow catalog check.

set -uo pipefail

WS="${1:-}"
shift || true
APPLY=0
GRACE_H="${GRACE_H:-24}"
MAX_FILES="${MAX_FILES:-5000}"
MAX_GB="${MAX_GB:-50}"
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --grace=*) GRACE_H=${a#*=} ;;
    --max-files=*) MAX_FILES=${a#*=} ;;
    --max-gb=*) MAX_GB=${a#*=} ;;
  esac
done

if [ -z "$WS" ] || [ ! -d "$WS" ]; then
  echo "ABORT: workspace path missing or not a directory: '$WS'" >&2
  exit 1
fi

DATA="$WS/data"
LOG="$DATA/_cleanup_marked_log.jsonl"
TRASH="$DATA/_trash/$(date +%F)"
mkdir -p "$TRASH"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
echo "[$(ts)] cleanup-marked-files start workspace=$WS apply=$APPLY grace=${GRACE_H}h max_files=$MAX_FILES max_gb=$MAX_GB" | tee -a "$LOG"

n=0
freedKB=0
skipped_nomarker=0
skipped_nokey=0
skipped_open=0
skipped_fresh=0
skipped_path=0

is_protected_catalog_state() {  # $1=file -> 0 if file is durable catalog/discovery state
  local f="$1"
  case "$f" in
    "$DATA"/google_shopping_merchants.jsonl|\
    "$DATA"/shopify_validated_merchants.jsonl|\
    "$DATA"/known_shopify_domains.txt)
      return 0
      ;;
  esac
  return 1
}

# Iterate markers directly. For each one, find its data file sibling.
# The data file is <marker_basename> with .ingested.json stripped.
#
# We do this with find so the entire data/ tree is scanned efficiently
# (one walk, in parallel with the marker pass).
#
# A two-pass approach is simpler and just as fast:
#   pass 1: list all *.ingested.json markers with a "key" field
#   pass 2: for each, derive the data file path and run the gate

while IFS= read -r marker; do
  [ $n -ge $MAX_FILES ] && { echo "  cap: MAX_FILES reached"; break; }
  [ $(( freedKB/1048576 )) -ge $MAX_GB ] && { echo "  cap: MAX_GB reached"; break; }

  # Skip markers in excluded directories
  case "$marker" in
    */_trash/*|*/checkpoints/*|*/ingest_ready/*|*/merchants/*)
      skipped_path=$((skipped_path+1))
      continue
      ;;
  esac

  # Extract the data file path (strip .ingested.json)
  f="${marker%.ingested.json}"

  # Marker must exist and have non-zero size
  [ ! -s "$marker" ] && { skipped_nomarker=$((skipped_nomarker+1)); continue; }

  # Marker must have a "key" field
  key=$(grep -oE '"key"[[:space:]]*:[[:space:]]*"[^"]+"' "$marker" 2>/dev/null | head -1 | sed 's/.*"key"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  [ -z "$key" ] && { skipped_nokey=$((skipped_nokey+1)); continue; }

  # Data file must exist
  [ ! -f "$f" ] && continue
  if is_protected_catalog_state "$f"; then
    skipped_path=$((skipped_path+1))
    continue
  fi

  # Path exclusions on the data file
  case "$f" in
    */_trash/*|*/checkpoints/*|*/ingest_ready/*|*/merchants/*)
      skipped_path=$((skipped_path+1))
      continue
      ;;
  esac

  # Gate A1: mtime stability — don't trash a file the active ingester
  # is still rotating
  if [ -n "$(find "$f" -mmin -$((GRACE_H*60)) 2>/dev/null)" ]; then
    skipped_fresh=$((skipped_fresh+1))
    continue
  fi

  # Gate A2: open handle check
  if lsof -- "$f" >/dev/null 2>&1; then
    skipped_open=$((skipped_open+1))
    continue
  fi

  kb=$(du -k "$f" | cut -f1)
  rec=$(wc -l < "$f" 2>/dev/null || echo 0)
  action=$([ $APPLY = 1 ] && echo trash || echo dryrun)
  printf '{"ts":"%s","file":"%s","kb":%s,"records":%s,"r2_key":"%s","action":"%s"}\n' \
    "$(date -uIs)" "$f" "$kb" "$rec" "$key" "$action" >> "$LOG"

  if [ $APPLY = 1 ]; then
    rel="${f#$DATA/}"
    mkdir -p "$TRASH/$(dirname "$rel")"
    mv "$f" "$TRASH/$rel"
    # Also move the marker so we don't reprocess it on the next run
    mkdir -p "$TRASH/$(dirname "$rel")"
    mv "$marker" "$TRASH/$rel.ingested.json" 2>/dev/null || true
  fi

  n=$((n+1))
  freedKB=$((freedKB+kb))
  echo "  $action [D1:marker] $(awk "BEGIN{printf \"%.2fMB\",$kb/1024}") $f"
done < <(find "$DATA" -type f -name '*.ingested.json' 2>/dev/null)

# Phase-2 trash purge: keep _trash recovery window
#   - non-raw: 48h (BUY-32838)
#   - raw buy*: 7-day (BUY-32838 hardening — R2 marker recovery needs longer)
find "$DATA/_trash" -type f -mmin +2880 ! -path "*/buy[0-9]*/*" -delete 2>/dev/null
find "$DATA/_trash" -type f -mmin +10080 -path "*/buy[0-9]*/*" -delete 2>/dev/null
find "$DATA/_trash" -type d -empty -delete 2>/dev/null

end_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "[$end_ts] cleanup-marked-files done files=$n freed=$(awk "BEGIN{printf \"%.2fGB\",$freedKB/1048576}") skipped_nomarker=$skipped_nomarker skipped_nokey=$skipped_nokey skipped_open=$skipped_open skipped_fresh=$skipped_fresh skipped_path=$skipped_path apply=$APPLY" | tee -a "$LOG"
