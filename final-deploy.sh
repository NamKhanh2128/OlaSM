#!/bin/bash
# Final deployment script with all fixes

set -e  # Exit on error

echo "🚀 Starting final deployment..."
echo ""

cd /root/P-160

# 1. Stop and remove old containers + volumes
echo "⏸️  Stopping and removing old containers..."
docker compose -f docker-compose.prod.yml down -v

# 2. Remove old bind mount data directory
echo "🗑️  Removing old data directory..."
rm -rf ./data

# 3. Rebuild backend with new Dockerfile
echo "🔨 Rebuilding backend image (this may take 2-3 minutes)..."
docker compose -f docker-compose.prod.yml build --no-cache backend

# 4. Start all services
echo "🚀 Starting all services..."
docker compose -f docker-compose.prod.yml up -d

# 5. Wait for services to stabilize
echo "⏳ Waiting 20 seconds for services to start..."
sleep 20

# 6. Check service status
echo ""
echo "📊 Service Status:"
docker compose -f docker-compose.prod.yml ps

# 7. Check backend logs
echo ""
echo "📋 Backend Logs (last 30 lines):"
docker compose -f docker-compose.prod.yml logs --tail=30 backend

# 8. Check database file in volume
echo ""
echo "💾 Database Files in Volume:"
docker compose -f docker-compose.prod.yml exec backend ls -la /app/data/ || echo "❌ Could not list /app/data/"

# 9. Test health endpoint
echo ""
echo "🏥 Testing Health Endpoint:"
sleep 2
curl -s http://localhost:8000/health | head -n 5 || echo "❌ Health check failed"

# 10. Test bookings endpoint
echo ""
echo "📚 Testing Bookings Endpoint:"
curl -s http://localhost:8000/api/v1/bookings | head -n 5 || echo "❌ Bookings endpoint failed"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 To view logs: docker compose -f docker-compose.prod.yml logs -f backend"
echo "🔍 To check volume: docker volume inspect p-160_app-data"
echo "🌐 Access frontend: http://149.28.131.104"
