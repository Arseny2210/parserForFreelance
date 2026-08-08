#!/usr/bin/env bash
# Production: build React frontend and serve it from FastAPI backend.
set -e

echo "▶️  Installing Python deps (if needed)..."
pip install -r requirements.txt fastapi >/dev/null 2>&1 || true

echo "▶️  Building frontend..."
cd frontend
npm install >/dev/null 2>&1 || true
npm run build
cd ..

echo "▶️  Starting server on :${PORT:-8000}..."
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
