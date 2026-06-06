#!/bin/bash
# deploy-systemd-units.sh — Install and activate systemd units for long-running lanes.
# BUY-31185: Must be run with root privileges (sudo).
# BUY-33094: Adds the paperclip-data-cleanup@.{service,timer} templates + per-workspace
#            timer enablement.
#
# Usage:
#   sudo bash scripts/deploy-systemd-units.sh
#
set -euo pipefail

UNIT_DIR="/etc/systemd/system"
SRC_DIR="/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/systemd"

# Plain units — installed + enabled unconditionally.
PLAIN_UNITS=(
  paperclip-loop-supervisor.service
  paperclip-buy30331-sustained-loop.service
  paperclip-buy30590-deep-page-loop.service
  paperclip-buy30727-lane-supervisor.service
  paperclip-lane-keep-alive.service
)

# Templated units — installed once, instantiated per workspace via the
# SCRAPING_WORKSPACES list below.
TEMPLATE_UNITS=(
  paperclip-data-cleanup@.service
  paperclip-data-cleanup@.timer
)

# Workspaces that get a 6-hourly cleanup timer. Keep in sync with the install
# list in scripts/install-safe-data-cleanup.sh.
SCRAPING_WORKSPACES=(
  "0ed653ab-62ba-4deb-8348-3086ab46961c"   # Shelf  — Shopify Scraper
  "2e68d8a0-9b0e-4573-8185-323edaabb186"   # Crate  — Shopify Ingestion Agent #3
  "3ec8f6dd-1735-4479-9825-a2c42edac34c"   # Oracle — Chief Data Officer
  "4df23039-272b-4621-9d77-7cf9b7121242"   # Stock  — Shopify Ingestion Agent #2
  "5bc984ee-e2d2-4312-9e6c-b2864524a21f"   # Shopper — Merchant Ingestion Lead
  "708a8ce4-96dd-409d-94e7-a91d5032e4e0"   # Hunt 2 — Other Merchants Scraper
  "7fb55262-e658-45e2-88c0-b0e8ccc5ad6c"   # Hex    — Scraping & Data Engineer
  "a29ac9dc-cf0a-455b-964c-e75bd2f5fc47"   # Dash   — Platform Ingestion Lead
  "bf810416-2f4c-4c4b-b27c-1270ea6f20b3"   # Probe  — Affiliates Scraping Engineer
  "c2850c54-3396-420a-b7c3-92faae3137c1"   # Probe 2 — Affiliates Scraping Engineer
  "d70ff7b3-e26b-4d23-8e05-bfc5d6f7a342"   # Crew   — Platform Scraping Engineer
  "f6a39f3c-210b-479b-a8e7-c78491c120e9"   # Hunt   — Other Merchants Scraper
)

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: This script must be run as root (use sudo)."
  exit 1
fi

echo "=== BUY-31185 / BUY-33094: Deploying systemd units ==="
echo ""

# Install plain unit files
echo "--- Installing plain unit files ---"
for unit in "${PLAIN_UNITS[@]}"; do
  if [[ -f "$SRC_DIR/$unit" ]]; then
    cp -v "$SRC_DIR/$unit" "$UNIT_DIR/$unit"
    chmod 644 "$UNIT_DIR/$unit"
  else
    echo "WARNING: $unit not found in $SRC_DIR — skipping"
  fi
done

# Install templated unit files
echo ""
echo "--- Installing templated unit files (BUY-33094) ---"
for unit in "${TEMPLATE_UNITS[@]}"; do
  if [[ -f "$SRC_DIR/$unit" ]]; then
    cp -v "$SRC_DIR/$unit" "$UNIT_DIR/$unit"
    chmod 644 "$UNIT_DIR/$unit"
  else
    echo "WARNING: $unit not found in $SRC_DIR — skipping"
  fi
done

# Reload systemd
echo ""
echo "--- Reloading systemd daemon ---"
systemctl daemon-reload

# Enable and start plain units
echo ""
echo "--- Enabling and starting plain units ---"
for unit in "${PLAIN_UNITS[@]}"; do
  if [[ -f "$UNIT_DIR/$unit" ]]; then
    echo ""
    echo ">> $unit"
    systemctl enable "$unit" 2>&1 || true
    systemctl start "$unit" 2>&1 || true
    systemctl status "$unit" --no-pager -l 2>&1 | head -15 || true
  fi
done

# Enable the per-workspace data-cleanup timers (BUY-33094)
echo ""
echo "--- Enabling per-workspace 6-hourly data-cleanup timers (BUY-33094) ---"
for ws in "${SCRAPING_WORKSPACES[@]}"; do
  timer="paperclip-data-cleanup@${ws}.timer"
  echo ""
  echo ">> $timer"
  systemctl enable "$timer" 2>&1 || true
  systemctl start "$timer" 2>&1 || true
done

echo ""
echo "=== Deployment complete ==="
echo "Verify with:"
echo "  systemctl list-timers paperclip-data-cleanup@*"
echo "  systemctl status paperclip-data-cleanup@<workspace>"
echo "  tail -f /paperclip/.../logs/data-cleanup-*.log"
