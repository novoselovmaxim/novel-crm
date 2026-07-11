#!/bin/bash
set -eo pipefail

echo "🚀 Deploying Novel CRM to VPS..."

VPS_USER="root"
VPS_HOST="80.87.111.142"
VPS_KEY="/tmp/novel_vps_key"
VPS_DIR="/opt/novel-crm"
SSH_CMD="ssh -i $VPS_KEY -o StrictHostKeyChecking=no $VPS_USER@$VPS_HOST"

echo "📦 Building frontend..."
cd frontend && npm run build 2>&1 | tail -3
cd ..

echo "📤 Pushing to GitHub..."
git add -A
git commit -m "deploy: $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || echo "No changes to commit"
git push

echo "🔄 Pulling on VPS..."
$SSH_CMD "cd $VPS_DIR && git pull origin main 2>&1"

echo "📦 Copying frontend dist to VPS..."
tar czf /tmp/frontend-dist.tar.gz -C frontend dist
scp -i $VPS_KEY -o StrictHostKeyChecking=no /tmp/frontend-dist.tar.gz $VPS_USER@$VPS_HOST:/tmp/
$SSH_CMD "
cd $VPS_DIR
mkdir -p frontend/dist
tar xzf /tmp/frontend-dist.tar.gz -C frontend/
rm -f /tmp/frontend-dist.tar.gz
"

echo "🖼️ Copying media files (logos) to VPS..."
$SSH_CMD "mkdir -p $VPS_DIR/backend/app/media"
scp -i $VPS_KEY -o StrictHostKeyChecking=no backend/app/media/* $VPS_USER@$VPS_HOST:$VPS_DIR/backend/app/media/

echo "🐳 Rebuilding backend..."
$SSH_CMD "cd $VPS_DIR && docker compose build backend 2>&1 | tail -5"

echo "🔄 Restarting services..."
$SSH_CMD "cd $VPS_DIR && docker compose up -d 2>&1 | tail -3"

echo "⏳ Waiting for startup..."
sleep 5

echo "🗄️ Running database migrations..."
$SSH_CMD "docker exec novel_crm_backend python3 /app/migrate_pipeline.py 2>&1 || true"

echo "✅ Testing deployment..."
$SSH_CMD "
echo '--- Frontend ---'
curl -sk https://novel.maxnov.ru/ | head -1
echo ''
echo '--- API ---'
curl -sk https://novel.maxnov.ru/api/health
echo ''
echo '--- Assets ---'
curl -sk -o /dev/null -w 'JS: %{http_code} | CSS: %{http_code}\n' \
  https://novel.maxnov.ru/assets/index-*.js \
  https://novel.maxnov.ru/assets/index-*.css
"

echo "🎉 Deployment complete!"
