#!/usr/bin/env bash
# Quick installation script for systemd auto-boot service on Raspberry Pi

SERVICE_NAME="campus-helpdesk-robot.service"
TARGET_DIR="/etc/systemd/system/${SERVICE_NAME}"

echo "=== Installing Campus Helpdesk Robot Systemd Service ==="

if [ ! -f "${SERVICE_NAME}" ]; then
    echo "Error: ${SERVICE_NAME} not found in current directory."
    exit 1
fi

sudo cp "${SERVICE_NAME}" "${TARGET_DIR}"
sudo chmod 644 "${TARGET_DIR}"

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

echo "=== Service Status ==="
sudo systemctl status "${SERVICE_NAME}" --no-pager

echo ""
echo "Installation complete!"
echo "View live logs: sudo journalctl -u ${SERVICE_NAME} -f"
echo "Restart service: sudo systemctl restart ${SERVICE_NAME}"
echo "Stop service:    sudo systemctl stop ${SERVICE_NAME}"
