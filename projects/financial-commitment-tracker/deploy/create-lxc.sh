#!/usr/bin/env bash
# create-lxc.sh — Run on the Proxmox host to create and bootstrap the LXC.
#
# Usage:
#   bash create-lxc.sh [CT_ID] [STORAGE]
#
# Defaults: CT_ID=200, STORAGE=local-lvm
# Requires a Debian 12 (Bookworm) template — downloads it if missing.

set -euo pipefail

CT_ID="${1:-200}"
STORAGE="${2:-local-lvm}"
CT_HOSTNAME="fin-tracker"
CT_MEMORY=512
CT_CORES=1
CT_DISK="4"
CT_TEMPLATE="debian-12-standard_12.7-1_amd64.tar.zst"

echo "==> Creating LXC $CT_ID ($CT_HOSTNAME) on storage $STORAGE"

# Download template if not present
if ! pveam list local | grep -q "$CT_TEMPLATE"; then
    echo "==> Downloading Debian 12 template..."
    pveam download local "$CT_TEMPLATE"
fi

TEMPLATE_PATH="local:vztmpl/$CT_TEMPLATE"

# Create the container
pct create "$CT_ID" "$TEMPLATE_PATH" \
    --hostname "$CT_HOSTNAME" \
    --storage "$STORAGE" \
    --rootfs "$STORAGE:$CT_DISK" \
    --memory "$CT_MEMORY" \
    --cores "$CT_CORES" \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --unprivileged 1 \
    --features nesting=1 \
    --onboot 1 \
    --start 1

echo "==> Waiting for container to start..."
sleep 5

# Push the install script into the container and run it
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
pct push "$CT_ID" "$SCRIPT_DIR/install.sh" /root/install.sh
pct exec "$CT_ID" -- chmod +x /root/install.sh
pct exec "$CT_ID" -- bash /root/install.sh

echo ""
echo "==> LXC $CT_ID created and app installed."
echo "    Get the container IP:  pct exec $CT_ID -- hostname -I"
echo "    The app is served on port 80 (nginx → uvicorn :8000)."
echo ""
echo "    Next steps:"
echo "      1. pct exec $CT_ID -- nano /opt/fin-tracker/.env   # set Telegram creds"
echo "      2. pct exec $CT_ID -- systemctl restart fin-tracker"
