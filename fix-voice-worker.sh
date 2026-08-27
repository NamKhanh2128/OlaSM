#!/bin/bash
# Fix voice worker - rebuild with rapidfuzz

set -e

echo "🔧 Fixing voice worker..."

cd /root/P-160

# Rebuild voice-worker with updated requirements.txt
echo "📦 Rebuilding voice-worker image..."
docker compose -f docker-compose.prod.yml build --no-cache voice-worker

# Restart voice-worker
echo "🚀 Starting voice-worker..."
docker compose -f docker-compose.prod.yml up -d voice-worker

# Wait for startup
echo "⏳ Waiting 20 seconds..."
sleep 20

# Check logs
echo ""
echo "📋 Voice worker logs:"
docker compose -f docker-compose.prod.yml logs --tail=50 voice-worker

echo ""
echo "📊 Services status:"
docker compose -f docker-compose.prod.yml ps
