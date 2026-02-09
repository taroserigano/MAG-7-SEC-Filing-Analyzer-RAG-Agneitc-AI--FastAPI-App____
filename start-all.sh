#!/bin/bash

# Master script to start both backend and frontend

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Starting Test App (Backend + Frontend)..."
echo "============================================"

# Check if backend .env exists
if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
    echo "⚠️  Backend .env file not found!"
    echo "📝 Creating from .env.example..."
    cp "$SCRIPT_DIR/backend/.env.example" "$SCRIPT_DIR/backend/.env"
    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env and add your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - PINECONE_API_KEY"
    echo "   - PINECONE_INDEX_NAME"
    echo "   - PINECONE_ENVIRONMENT"
    echo ""
    read -p "Press Enter after you've configured backend/.env..."
fi

# Start backend
bash "$SCRIPT_DIR/start-backend.sh"
if [ $? -ne 0 ]; then
    echo "❌ Failed to start backend"
    exit 1
fi

echo ""

# Start frontend
bash "$SCRIPT_DIR/start-frontend.sh"
if [ $? -ne 0 ]; then
    echo "❌ Failed to start frontend"
    exit 1
fi

echo ""
echo "============================================"
echo "✅ All services started successfully!"
echo ""
echo "📱 Open: http://localhost:5173"
echo "🔧 Backend: http://localhost:8000"
echo ""
echo "📝 View logs:"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Frontend: tail -f /tmp/frontend.log"
echo ""
echo "🛑 Stop services:"
echo "   kill \$(cat /tmp/backend.pid)"
echo "   kill \$(cat /tmp/frontend.pid)"
echo "   Or: bash stop-all.sh"
