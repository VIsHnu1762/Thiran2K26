#!/bin/bash
# =============================================================================
# BillAgent Pro - Development Server Script
# =============================================================================
# Run both frontend and backend in development mode.
# Run: chmod +x run-dev.sh && ./run-dev.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "========================================"
echo -e "  ${BLUE}BillAgent Pro - Development Server${NC}"
echo "========================================"
echo ""

# Check if containers are running
check_containers() {
    echo -n "Checking database containers... "
    if ! docker ps | grep -q "billagent-postgres"; then
        echo -e "${YELLOW}Starting containers...${NC}"
        docker-compose up -d postgres redis
        sleep 3
    else
        echo -e "${GREEN}Running${NC}"
    fi
}

# Start backend
start_backend() {
    echo ""
    echo -e "${BLUE}Starting Backend Server...${NC}"
    cd backend
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Start uvicorn in background
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    cd ..
    echo -e "${GREEN}Backend started on http://localhost:8000${NC}"
    echo -e "${GREEN}API Docs: http://localhost:8000/docs${NC}"
}

# Start frontend
start_frontend() {
    echo ""
    echo -e "${BLUE}Starting Frontend Server...${NC}"
    
    # Install deps if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi
    
    # Start vite in background
    npm run dev &
    FRONTEND_PID=$!
    
    echo -e "${GREEN}Frontend started on http://localhost:5173${NC}"
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill any remaining uvicorn processes
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    
    echo -e "${GREEN}Servers stopped.${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT SIGTERM

# Main
main() {
    check_containers
    start_backend
    start_frontend
    
    echo ""
    echo "========================================"
    echo -e "  ${GREEN}All servers running!${NC}"
    echo "========================================"
    echo ""
    echo "  Frontend: http://localhost:5173"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop all servers."
    echo ""
    
    # Wait forever until Ctrl+C
    wait
}

main "$@"
