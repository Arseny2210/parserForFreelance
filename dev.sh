#!/usr/bin/env bash
# Dev: run FastAPI backend (8000) + Vite dev server (5173) with hot reload.
set -e

python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements.txt fastapi >/dev/null 2>&1

echo "▶️  Backend:  http://localhost:8000  (uvicorn)"
echo "▶️  Frontend: http://localhost:5173  (vite, hot reload)"
trap "kill 0" EXIT

(uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload) &
(cd frontend && npm install >/dev/null 2>&1 && npm run dev) &

wait
