#!/usr/bin/env bash
set -euo pipefail

# Simple dev helper to start the backend cleanly.
# 1) Kills anything already on port 8000
# 2) Starts uvicorn with the project venv and env file

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/backend"

# Kill any existing backend on 8000 so we don't get address-in-use errors
lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true

# Start backend
exec "$ROOT_DIR/.venv/bin/python" -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --env-file "$ROOT_DIR/backend/.env"
