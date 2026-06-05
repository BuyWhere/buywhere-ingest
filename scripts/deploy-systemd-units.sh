#!/bin/bash
# deploy-systemd-units.sh — Install and activate systemd units for long-running lanes.
# BUY-31185: Must be run with root privileges (sudo).
#
# Usage:
#   sudo bash scripts/deploy-systemd-units.sh
#
set -euo pipefail

UNIT_DIR="/etc/systemd/system"
SRC_DIR="/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/systemd"

UNITS=(
  paperclip-loop-supervisor.service
  paperclip-buy30331-sustained-loop.service
  paperclip-buy30590-deep-page-loop.service
  paperclip-buy30727-lane-supervisor.service
  paperclip-lane-keep-alive.service
)

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: This script must be run as root (use sudo)."
  exit 1
fi

echo "=== BUY-31185: Deploying systemd units for long-running lanes ==="
echo ""

# Install unit files
echo "--- Installing unit files ---"
for unit in "${UNITS[@]}"; do
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

# Enable and start each unit
echo ""
echo "--- Enabling and starting units ---"
for unit in "${UNITS[@]}"; do
  if [[ -f "$UNIT_DIR/$unit" ]]; then
    echo ""
    echo ">> $unit"
    systemctl enable "$unit" 2>&1 || true
    systemctl start "$unit" 2>&1 || true
    systemctl status "$unit" --no-pager -l 2>&1 | head -15 || true
  fi
done

echo ""
echo "=== Deployment complete ==="
echo "Run 'systemctl status paperclip-loop-supervisor paperclip-buy30331-sustained-loop paperclip-buy30590-deep-page-loop paperclip-buy30727-lane-supervisor paperclip-lane-keep-alive' to verify."
