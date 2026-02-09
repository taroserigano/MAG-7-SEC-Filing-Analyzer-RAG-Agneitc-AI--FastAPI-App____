#!/bin/bash

# Script to start backend server in a robust way
# This ensures the backend keeps running even if terminal is closed

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/backend"

echo "🚀 Starting backend server..."

# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Check if venv exists, if not, create it
if [ ! -d "venv" ]; then
    echo "⚙️  Creating virtual environment..."
    python3 -m venv venv
    echo "📦 Installing dependencies..."
    ./venv/bin/pip install -r requirements.txt
fi

# Start backend with nohup using the virtual environment Python
nohup ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env > /tmp/backend.log 2>&1 &

BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"
echo $BACKEND_PID > /tmp/backend.pid

# Wait for backend to start (increased wait time for model loading)
sleep 10

if lsof -i:8000 > /dev/null 2>&1; then
    echo "✅ Backend is running on http://localhost:8000"
    echo "📝 Logs: tail -f /tmp/backend.log"
    echo "🛑 Stop: kill \$(cat /tmp/backend.pid)"
else
    echo "❌ Backend failed to start. Check /tmp/backend.log for errors"
    tail -50 /tmp/backend.log
    exit 1
fi
