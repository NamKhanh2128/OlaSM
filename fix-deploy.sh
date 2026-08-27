#!/bin/bash

# Script to fix deployment issues on VPS

echo "🔧 Fixing deployment issues..."

# 1. Create data directory with proper permissions
echo "📁 Creating data directory..."
mkdir -p ./data
chmod -R 777 ./data

# 2. Stop all services
echo "🛑 Stopping services..."
docker compose -f docker-compose.prod.yml down

# 3. Rebuild backend with new Dockerfile
echo "🔨 Rebuilding backend..."
docker compose -f docker-compose.prod.yml build --no-cache backend

# 4. Start all services
echo "🚀 Starting services..."
docker compose -f docker-compose.prod.yml up -d

# 5. Wait a bit and show logs
echo "⏳ Waiting for services to start..."
sleep 10

echo "📋 Backend logs:"
docker compose -f docker-compose.prod.yml logs --tail=20 backend

echo ""
echo "✅ Done! Check the logs above."
echo "To follow logs: docker compose -f docker-compose.prod.yml logs -f backend"
