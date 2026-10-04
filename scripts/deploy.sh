#!/usr/bin/env bash
# ==============================================================================
# OlaSM - Standard Production Deployment Script
# Single Source of Truth for deploying OlaSM services with Docker Compose
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "======================================================"
echo "🚀 Deploying OlaSM (Voice Agent + Backend + Frontend)"
echo "======================================================"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"

if [ ! -f "${ENV_FILE}" ]; then
  if [ -f ".env" ]; then
    echo "⚠️  ${ENV_FILE} not found; falling back to .env"
    ENV_FILE=".env"
  else
    echo "❌ Error: Neither .env.production nor .env found."
    exit 1
  fi
fi

# Ensure data directory exists with write permissions
mkdir -p ./data

echo "📦 Building and starting containers via ${COMPOSE_FILE}..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --build

echo "⏳ Waiting for services to become healthy..."
MAX_RETRIES=30
RETRY_COUNT=0
HEALTHY=0

while [ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]; do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    HEALTHY=1
    break
  fi
  printf "."
  sleep 2
  RETRY_COUNT=$((RETRY_COUNT + 1))
done
echo ""

if [ ${HEALTHY} -eq 1 ]; then
  echo "✅ Backend is healthy and responding!"
  docker compose -f "${COMPOSE_FILE}" ps
  echo ""
  echo "🎉 OlaSM deployment succeeded!"
  echo "   - Backend:  http://localhost:8000/health"
  echo "   - Docs:     http://localhost:8000/docs"
else
  echo "❌ Error: Health check timed out after 60s."
  echo "📋 Backend logs:"
  docker compose -f "${COMPOSE_FILE}" logs --tail=50 backend
  exit 1
fi
