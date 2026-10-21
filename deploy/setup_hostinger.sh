#!/usr/bin/env bash
# ==============================================================================
# Cognitive CanSat - Hostinger VPS Automated Setup Script
# ==============================================================================
# Usage on fresh Hostinger Ubuntu 22.04 / 24.04 VPS:
#   chmod +x deploy/setup_hostinger.sh
#   sudo ./deploy/setup_hostinger.sh
# ==============================================================================

set -e

echo "=== 1. Updating System Packages ==="
apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx libgl1 libglib2.0-0 libgomp1 curl

echo "=== 2. Setting Up Application Directory ==="
INSTALL_DIR="/var/www/cansat"
mkdir -p "$INSTALL_DIR"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing repository..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo "Copying repository files to $INSTALL_DIR..."
    cp -r . "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo "=== 3. Configuring Python Virtual Environment ==="
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    python3 -m venv "$INSTALL_DIR/.venv"
fi

"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

echo "=== 4. Setting Permissions ==="
mkdir -p "$INSTALL_DIR/data"
chmod -R 775 "$INSTALL_DIR/data"

echo "=== 5. Installing Systemd Service ==="
cp "$INSTALL_DIR/deploy/cansat.service" /etc/systemd/system/cansat.service
systemctl daemon-reload
systemctl enable cansat.service
systemctl restart cansat.service

echo "=== 6. Configuring Nginx Reverse Proxy ==="
cp "$INSTALL_DIR/deploy/cansat.nginx.conf" /etc/nginx/sites-available/cansat
ln -sf /etc/nginx/sites-available/cansat /etc/nginx/sites-enabled/cansat
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "=============================================================================="
echo "Deployment Complete!"
echo "Status check:"
echo "  systemctl status cansat.service"
echo ""
echo "To attach your domain and enable SSL (HTTPS + WSS):"
echo "  sudo certbot --nginx -d your-domain.com -d www.your-domain.com"
echo "=============================================================================="
