#!/bin/bash
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root. Use sudo." >&2
    exit 1
fi
echo "Removing servers-temp..."
if systemctl is-active --quiet servers-temp; then
    echo "Stopping the servers-temp service..."
    systemctl stop servers-temp
fi
if systemctl is-enabled --quiet servers-temp; then
    echo "Disabling autostart of the servers-temp service..."
    systemctl disable servers-temp
fi
echo "Deleting service files..."
rm -f /etc/systemd/system/servers-temp.service
rm -f /usr/local/bin/servers-temp.sh
rm -f "$(dirname "$0")/servers-temp.sh"
echo "Restarting systemd..."
systemctl daemon-reload
rm -f "$0"
echo "Removal complete!" 