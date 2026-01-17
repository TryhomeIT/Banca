#!/bin/bash

# Jornais - Quick Start Script

echo "📰 Starting Jornais Digital Newsstand..."
echo ""

# Check for poppler
if ! command -v pdftoppm &> /dev/null; then
    echo "⚠️  poppler-utils not found. Installing..."
    sudo apt-get update && sudo apt-get install -y poppler-utils
fi

# Start backend
echo "🔧 Starting backend server..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend running on http://localhost:8000 (PID: $BACKEND_PID)"

cd ..

# Start frontend
echo "🎨 Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend running on http://localhost:5173 (PID: $FRONTEND_PID)"

echo ""
echo "✅ Jornais is ready!"
echo "   Open http://localhost:5173 in your browser"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
