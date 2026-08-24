#!/bin/bash
# Fix database permission issue on VPS

echo "🔧 Fixing database permissions..."

cd /root/P-160

# Stop backend
echo "⏸️  Stopping backend..."
docker compose -f docker-compose.prod.yml stop backend

# Create data directory with full permissions
echo "📁 Creating data directory..."
mkdir -p ./data
chmod -R 777 ./data

# Create empty database file
echo "📄 Creating database file..."
touch ./data/app.db
chmod 666 ./data/app.db

# Verify permissions
echo "✅ Verifying permissions..."
ls -la ./data/

# Start backend
echo "🚀 Starting backend..."
docker compose -f docker-compose.prod.yml start backend

# Wait and check logs
echo "⏳ Waiting 10 seconds..."
sleep 10

echo "📋 Backend logs (last 30 lines):"
docker compose -f docker-compose.prod.yml logs --tail=30 backend

echo ""
echo "✅ Done! Check if database error is gone."
echo ""
echo "To verify database was created:"
echo "  ls -la ./data/"
echo ""
echo "To test the API:"
echo "  curl http://localhost:8000/api/v1/bookings"
