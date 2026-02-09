#!/bin/bash

# Script to start frontend server in a robust way

cd "$(dirname "$0")/frontend"

echo "🎨 Starting frontend server..."

# Kill any existing process on ports 5173/5174
lsof -ti:5173 | xargs kill -9 2>/dev/null
lsof -ti:5174 | xargs kill -9 2>/dev/null

# Check if node_modules exists, if not, install dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
fi

# Start frontend with nohup
nohup npm run dev > /tmp/frontend.log 2>&1 &

FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"
echo $FRONTEND_PID > /tmp/frontend.pid

# Wait for frontend to start
sleep 5

if lsof -i:5173 > /dev/null 2>&1 || lsof -i:5174 > /dev/null 2>&1; then
    PORT=$(lsof -ti:5173 > /dev/null 2>&1 && echo "5173" || echo "5174")
    echo "✅ Frontend is running on http://localhost:$PORT"
    echo "📝 Logs: tail -f /tmp/frontend.log"
    echo "🛑 Stop: kill \$(cat /tmp/frontend.pid)"
else
    echo "❌ Frontend failed to start. Check /tmp/frontend.log for errors"
    cat /tmp/frontend.log
    exit 1
fi
