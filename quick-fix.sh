#!/bin/bash
# Quick fix for database permission issue

mkdir -p ./data && chmod -R 777 ./data
docker compose -f docker-compose.prod.yml restart backend
echo "✅ Done! Checking logs..."
sleep 3
docker compose -f docker-compose.prod.yml logs --tail=20 backend
