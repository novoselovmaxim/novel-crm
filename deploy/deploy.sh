#!/bin/bash
set -e

echo "=== Novel CRM Deployment ==="

if [ ! -d "/opt/novel-crm" ]; then
    echo "Error: /opt/novel-crm not found."
    exit 1
fi

cd /opt/novel-crm

if [ ! -f ".env" ]; then
    echo "Error: .env not found. Copy from .env.example and fill in values."
    exit 1
fi

echo "Building and starting containers..."
docker compose down
docker compose up -d --build

echo "Waiting for PostgreSQL..."
sleep 5

echo "=== Deployment complete ==="
echo "Application running at: https://novel.maxnov.ru"
echo "Backend API: http://localhost:3020/api/docs"
