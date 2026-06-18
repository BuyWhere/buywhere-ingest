#!/bin/bash
# install-safe-data-cleanup.sh — Install safe-data-cleanup.sh into every
# scraping/ingestion workspace and symlink data/.catalog_db_url where missing.
# Idempotent: re-running on a populated workspace is a no-op.
#
# BUY-33094: prerequisites for the data-cleanup.service + .timer units to be
# effective. deploy-systemd-units.sh assumes this script has run.
#
# Usage:
#   sudo bash scripts/install-safe-data-cleanup.sh
#
set -euo pipefail

REF="/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/safe-data-cleanup.sh"
R2_HEAD="/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/scripts/r2_head.py"
CANON_CATALOG="/paperclip/instances/default/workspaces/3ec8f6dd-1735-4479-9825-a2c42edac34c/data/.catalog_db_url"

# Workspaces that scrape or ingest into the catalog. Order doesn't matter.
TARGETS=(
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

if [[ ! -f "$REF" ]]; then
  echo "ERROR: reference script not found at $REF" >&2
  exit 1
fi
if [[ ! -f "$R2_HEAD" ]]; then
  echo "ERROR: r2_head.py not found at $R2_HEAD (Gate D requires it)" >&2
  exit 1
fi
if [[ ! -f "$CANON_CATALOG" ]]; then
  echo "ERROR: canonical catalog URL file not found at $CANON_CATALOG" >&2
  exit 1
fi

echo "=== BUY-33094: Installing safe-data-cleanup.sh into scraping workspaces ==="
echo ""

for id in "${TARGETS[@]}"; do
  ws="/paperclip/instances/default/workspaces/$id"
  if [[ ! -d "$ws/data" ]]; then
    echo "SKIP: $id (no data/ directory — not a scrape workspace)"
    continue
  fi
  if [[ ! -f "$ws/data/.catalog_db_url" ]]; then
    ln -sf "$CANON_CATALOG" "$ws/data/.catalog_db_url"
    echo "LINKED .catalog_db_url: $id"
  fi
  if [[ ! -f "$ws/safe-data-cleanup.sh" ]]; then
    install -m 0755 "$REF" "$ws/safe-data-cleanup.sh"
    echo "INSTALLED safe-data-cleanup.sh: $id"
  else
    if [[ "$(readlink -f "$REF")" == "$(readlink -f "$ws/safe-data-cleanup.sh")" ]]; then
      echo "SKIP refresh safe-data-cleanup.sh: $id (canonical source)"
    else
    # Refresh the copy in case the protocol was updated.
      install -m 0755 "$REF" "$ws/safe-data-cleanup.sh"
      echo "REFRESHED safe-data-cleanup.sh: $id"
    fi
  fi
  # Gate D in the cleanup script depends on r2_head.py being next to it.
  mkdir -p "$ws/scripts"
  if [[ ! -f "$ws/scripts/r2_head.py" ]] || [[ "$ws/scripts/r2_head.py" -ot "$R2_HEAD" ]]; then
    install -m 0755 "$R2_HEAD" "$ws/scripts/r2_head.py"
    echo "INSTALLED scripts/r2_head.py: $id"
  fi
done

echo ""
echo "=== Installation complete ==="
echo "Now run: sudo bash scripts/deploy-systemd-units.sh to enable the 6-hourly timers."
