#!/bin/bash
# Final deployment script - Fix policy catalog issue

set -e

echo "🚀 Starting deployment with policy catalog fix..."
echo ""

cd /root/P-160

# 1. Stop and remove old containers + volumes
echo "⏸️  Stopping containers..."
docker compose -f docker-compose.prod.yml down -v

# 2. Remove old data directory (not needed anymore)
echo "🗑️  Cleaning old data..."
rm -rf ./data

# 3. Rebuild backend with fixed Dockerfile
echo "🔨 Rebuilding backend image..."
docker compose -f docker-compose.prod.yml build --no-cache backend

# 4. Start all services
echo "🚀 Starting services..."
docker compose -f docker-compose.prod.yml up -d

# 5. Wait for startup
echo "⏳ Waiting 20 seconds..."
sleep 20

# 6. Check service status
echo ""
echo "📊 Service Status:"
docker compose -f docker-compose.prod.yml ps

# 7. Check logs
echo ""
echo "📋 Backend Logs:"
docker compose -f docker-compose.prod.yml logs --tail=40 backend

# 8. Verify policy files
echo ""
echo "📁 Checking policy files in container:"
docker compose -f docker-compose.prod.yml exec backend ls -la /app/config/policies/ || echo "❌ Policy files not found"

# 9. Verify database
echo ""
echo "💾 Checking database:"
docker compose -f docker-compose.prod.yml exec backend ls -la /app/data/ || echo "❌ Data directory not found"

# 10. Test endpoints
echo ""
echo "🏥 Testing endpoints..."
sleep 5
curl -s http://localhost:8000/health | head -n 3 || echo "❌ Health check failed"
echo ""
curl -s http://localhost:8000/api/v1/bookings | head -n 3 || echo "❌ Bookings failed"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 View logs: docker compose -f docker-compose.prod.yml logs -f backend"
echo "🌐 Frontend: http://149.28.131.104"
