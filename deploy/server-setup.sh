#!/bin/bash
set -e

echo "=== Novel CRM Server Setup ==="

mkdir -p /opt/novel-crm
cd /opt/novel-crm

# Get SSL certificate if not exists
if [ ! -d "/etc/letsencrypt/live/novel.maxnov.ru" ]; then
    echo "Obtaining SSL certificate..."
    certbot --nginx -d novel.maxnov.ru
fi

echo "=== Server setup complete ==="
echo "Next: copy project files to /opt/novel-crm and run deploy.sh"
