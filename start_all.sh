#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🚀 Starting Banca Project Stack (Background Mode)..."

# Function to kill processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    kill $BACKEND_PID $FRONTEND_PID $CONVEX_PID 2>/dev/null
    exit
}

# Trap Ctrl+C (SIGINT)
trap cleanup INT

# 1. Start Backend (FastAPI) using uv
echo "Starting Backend..."
cd "$SCRIPT_DIR/backend"
# using uv as requested
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# 2. Start Convex (Real-time Database)
echo "Starting Convex..."
cd "$SCRIPT_DIR/frontend"
npx convex dev &
CONVEX_PID=$!
echo "✅ Convex started (PID: $CONVEX_PID)"

# 3. Start Frontend (Vite)
echo "Starting Frontend..."
# cd "$SCRIPT_DIR/frontend" # Already in frontend dir
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "🎉 All services are running in the background."
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   Convex:   (Managed by npx convex dev)"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for processes
wait