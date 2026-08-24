#!/bin/bash
# Final deployment script with Docker volume fix

echo "🚀 Deploying with fixed database volume..."

cd /root/P-160

# Stop all services
echo "⏸️  Stopping all services..."
docker compose -f docker-compose.prod.yml down

# Remove old bind mount data if exists
echo "🗑️  Cleaning old bind mount..."
rm -rf ./data

# Start with new Docker volume
echo "🚀 Starting services with Docker volume..."
docker compose -f docker-compose.prod.yml up -d

# Wait for services to stabilize
echo "⏳ Waiting 15 seconds for services to start..."
sleep 15

# Check status
echo ""
echo "📊 Service status:"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "📋 Backend logs (last 30 lines):"
docker compose -f docker-compose.prod.yml logs --tail=30 backend

echo ""
echo "✅ Deployment complete!"
echo ""
echo "To check logs: docker compose -f docker-compose.prod.yml logs -f backend"
echo "To check volume: docker volume inspect p-160_app-data"
