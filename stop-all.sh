#!/bin/bash

# Script to stop all services

echo "🛑 Stopping all services..."

# Stop backend
if [ -f /tmp/backend.pid ]; then
    BACKEND_PID=$(cat /tmp/backend.pid)
    kill $BACKEND_PID 2>/dev/null && echo "✅ Backend stopped (PID: $BACKEND_PID)" || echo "⚠️  Backend not running"
    rm /tmp/backend.pid
else
    # Fallback: kill by port
    lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ Backend stopped" || echo "⚠️  No backend on port 8000"
fi

# Stop frontend
if [ -f /tmp/frontend.pid ]; then
    FRONTEND_PID=$(cat /tmp/frontend.pid)
    kill $FRONTEND_PID 2>/dev/null && echo "✅ Frontend stopped (PID: $FRONTEND_PID)" || echo "⚠️  Frontend not running"
    rm /tmp/frontend.pid
else
    # Fallback: kill by port
    lsof -ti:5173 | xargs kill -9 2>/dev/null
    lsof -ti:5174 | xargs kill -9 2>/dev/null
    echo "✅ Frontend stopped"
fi

echo ""
echo "✅ All services stopped"
