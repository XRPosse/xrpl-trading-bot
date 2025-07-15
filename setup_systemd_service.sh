#!/bin/bash

# Setup systemd service for XRPL real-time collector

SERVICE_NAME="xrpl-realtime-collector"
SERVICE_FILE="${SERVICE_NAME}.service"
SYSTEMD_PATH="/etc/systemd/system"

echo "Setting up XRPL Real-time Collector as systemd service..."

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo: sudo ./setup_systemd_service.sh"
    exit 1
fi

# Copy service file
echo "Copying service file to systemd..."
cp "$SERVICE_FILE" "$SYSTEMD_PATH/"

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"

# Start the service
echo "Starting the service..."
systemctl start "$SERVICE_NAME"

# Check status
echo "Checking service status..."
systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "Setup complete! Useful commands:"
echo "  - View status: sudo systemctl status $SERVICE_NAME"
echo "  - View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "  - Stop service: sudo systemctl stop $SERVICE_NAME"
echo "  - Start service: sudo systemctl start $SERVICE_NAME"
echo "  - Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  - Disable autostart: sudo systemctl disable $SERVICE_NAME"