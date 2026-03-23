#!/bin/bash

# Banca - Unified Local Development Script
# Starts Backend (FastAPI) and Frontend (Vite)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$SCRIPT_DIR/logs/local_dev"
PID_FILE="$SCRIPT_DIR/.local_pids.txt"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${BLUE}Banca Local Development Management${NC}"
    echo "Usage:"
    echo "  ./dev.sh          - Start all services in foreground (Interactive)"
    echo "  ./dev.sh --bg     - Start all services in background (Logs to ./logs/)"
    echo "  ./dev.sh --stop   - Stop all running local services"
    echo "  ./dev.sh --logs   - Show logs from background services"
    echo "  ./dev.sh --setup  - Install all local dependencies"
}

check_dependencies() {
    echo -e "${BLUE}🔍 Checking dependencies...${NC}"
    
    # 1. Frontend
    if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
        echo -e "${YELLOW}⚠️  node_modules not found in frontend. Installing...${NC}"
        cd "$SCRIPT_DIR/frontend" && npm install
    fi

    # 2. Backend
    # Check if using uv or traditional venv
    if command -v uv > /dev/null 2>&1; then
        if [ ! -f "$SCRIPT_DIR/backend/pyproject.toml" ] && [ ! -d "$SCRIPT_DIR/backend/.venv" ]; then
            echo -e "${YELLOW}⚠️  Backend virtual environment not found. Initializing with uv...${NC}"
            cd "$SCRIPT_DIR/backend"
            uv init --no-workspace
            uv add -r requirements.txt
        fi
    else
        if [ ! -d "$SCRIPT_DIR/backend/.venv" ]; then
             echo -e "${YELLOW}⚠️  Backend virtual environment not found and uv not installed. Creating venv...${NC}"
             python3 -m venv "$SCRIPT_DIR/backend/.venv"
             source "$SCRIPT_DIR/backend/.venv/bin/activate"
             pip install -r "$SCRIPT_DIR/backend/requirements.txt"
        fi
    fi
    

    # 4. Check for pdftoppm (Poppler)
    if ! command -v pdftoppm &> /dev/null; then
        echo -e "${RED}⚠️  pdftoppm not found. Please install poppler for PDF processing.${NC}"
        echo "   On macOS (Homebrew): brew install poppler"
    fi

    echo -e "${GREEN}✅ Dependencies look good.${NC}"
}

stop_services() {
    echo -e "${YELLOW}🛑 Stopping all Banca services...${NC}"
    
    # 1. Kill via PID file if it exists
    if [ -f "$PID_FILE" ]; then
        pids=$(cat "$PID_FILE")
        for pid in $pids; do
            if ps -p $pid > /dev/null; then
                kill $pid 2>/dev/null
            fi
        done
        rm "$PID_FILE"
    fi

    # 2. Safety kill via pkill for matching processes
    pkill -f "uvicorn app.main:app" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    
    echo -e "${GREEN}✅ All services stopped.${NC}"
}

start_foreground() {
    check_dependencies
    echo -e "${BLUE}🚀 Starting Banca in Interactive Mode...${NC}"
    
    # Trap Ctrl+C to stop services
    trap "stop_services; exit" INT

    # 1. Start Backend
    echo -e "${BLUE}   Initializing Database...${NC}"
    cd "$SCRIPT_DIR/backend"
    if command -v uv > /dev/null 2>&1; then
        uv run python init_db.py
        echo -e "${BLUE}   Starting Backend...${NC}"
        uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    else
        source .venv/bin/activate
        python init_db.py
        echo -e "${BLUE}   Starting Backend...${NC}"
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    fi
    BACKEND_PID=$!

    # 2. Start Frontend
    echo -e "${BLUE}   Starting Frontend (Vite)...${NC}"
    cd "$SCRIPT_DIR/frontend"
    npm run dev &
    FRONTEND_PID=$!

    echo -e "${GREEN}🎉 All services are running!${NC}"
    echo -e "   Backend:  http://localhost:8000"
    echo -e "   Frontend: http://localhost:5173"
    echo ""
    echo "Press Ctrl+C to stop everything."

    wait
}

start_background() {
    check_dependencies
    echo -e "${BLUE}🚀 Starting Banca in Background Mode...${NC}"
    mkdir -p "$LOG_DIR"
    
    # Stop existing first to avoid port conflicts
    stop_services > /dev/null 2>&1

    # 1. Backend
    echo -e "${BLUE}   Initializing Database...${NC}"
    cd "$SCRIPT_DIR/backend"
    if command -v uv > /dev/null 2>&1; then
        uv run python init_db.py
        echo -e "${BLUE}   Starting Backend...${NC}"
        nohup uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend.log" 2>&1 &
    else
        source .venv/bin/activate
        python init_db.py
        echo -e "${BLUE}   Starting Backend...${NC}"
        nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend.log" 2>&1 &
    fi
    BACKEND_PID=$!

    # 3. Frontend
    echo -e "${BLUE}   Starting Frontend...${NC}"
    cd "$SCRIPT_DIR/frontend"
    nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!

    # Save PIDs
    echo "$BACKEND_PID $FRONTEND_PID" > "$PID_FILE"

    echo -e "${GREEN}✅ Services started in background.${NC}"
    echo -e "   Logs: $LOG_DIR/"
    echo -e "   URL:  http://localhost:5173"
    echo ""
    echo "Use './dev.sh --stop' to shut down."
}

# Main routing
case "$1" in
    --setup)
        check_dependencies
        ;;
    --bg)
        start_background
        ;;
    --stop)
        stop_services
        ;;
    --status)
        # Reusing stop_services logic to check if PIDs exist or processes run
        pgrep -f "uvicorn app.main:app" > /dev/null && echo "Backend is RUNNING" || echo "Backend is STOPPED"
        pgrep -f "vite" > /dev/null && echo "Frontend is RUNNING" || echo "Frontend is STOPPED"
        ;;
    --logs)
        tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
        ;;
    --help|-h)
        show_help
        ;;
    "")
        start_foreground
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        show_help
        exit 1
        ;;
esac
