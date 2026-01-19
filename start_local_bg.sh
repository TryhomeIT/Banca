#!/bin/bash

# Directory setup
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$SCRIPT_DIR/logs/local_dev"
mkdir -p "$LOG_DIR"

echo "🛑 Stopping any existing local instances..."
pkill -f "uvicorn app.main:app"
pkill -f "vite"
pkill -f "convex dev"

echo "🚀 Starting Banca in LOCAL DEV MODE (Background)..."

# 1. Backend
echo "   Starting Backend (FastAPI)..."
cd "$SCRIPT_DIR/backend"
# Ensure venv exists
if [ ! -d ".venv" ]; then
    echo "   Creating Python virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Run with reload enabled
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   ✅ Backend running (PID: $BACKEND_PID) -> http://localhost:8000"

# 2. Convex (Cloud Database)
echo "   Starting Convex..."
cd "$SCRIPT_DIR/frontend"
nohup npx convex dev > "$LOG_DIR/convex.log" 2>&1 &
CONVEX_PID=$!
echo "   ✅ Convex running (PID: $CONVEX_PID)"

cd "$SCRIPT_DIR/frontend"
# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "   Installing Frontend dependencies..."
    npm install > "$LOG_DIR/npm_install.log" 2>&1
fi

echo "   Starting Frontend (Vite with setsid)..."
setsid ./node_modules/.bin/vite --host > "$LOG_DIR/frontend.log" 2>&1 < /dev/null &
FRONTEND_PID=$!
echo "   ✅ Frontend running (PID: $FRONTEND_PID) -> http://localhost:5173"

# Save PIDs for stopping later
echo "$BACKEND_PID $CONVEX_PID $FRONTEND_PID" > "$SCRIPT_DIR/local_pids.txt"

echo ""
echo "🎉 Development Server is LIVE!"
echo "   ---------------------------------------"
echo "   🌐 App URL:    http://localhost:5173"
echo "   📄 Logs:       $LOG_DIR/"
echo "   💾 PIDs Saved: $SCRIPT_DIR/local_pids.txt"
echo "   ---------------------------------------"
echo "   📝 Edit files locally and the app will auto-update!"
echo ""
