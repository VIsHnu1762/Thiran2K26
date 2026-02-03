#!/bin/bash
# =============================================================================
# Quick Start Script - BillAgent Pro
# =============================================================================
# Usage: ./start.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "=========================================="
echo -e "  ${BLUE}Starting BillAgent Pro${NC}"
echo "=========================================="
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Kill any existing processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 1

# Start backend
echo -e "${BLUE}Starting Backend Server...${NC}"
cd "$SCRIPT_DIR/backend"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Start frontend
echo -e "${BLUE}Starting Frontend Server...${NC}"
cd "$SCRIPT_DIR"
npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"

# Wait a moment and check if processes are still running
sleep 3

if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Backend is running on http://localhost:8000${NC}"
else
    echo -e "${YELLOW}⚠ Backend may have issues. Check backend.log${NC}"
fi

if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Frontend is running on http://localhost:5173${NC}"
else
    echo -e "${YELLOW}⚠ Frontend may have issues. Check frontend.log${NC}"
fi

echo ""
echo "=========================================="
echo -e "  ${GREEN}Servers Started!${NC}"
echo "=========================================="
echo ""
echo "  Frontend:  http://localhost:5173"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "  Backend logs: tail -f backend.log"
echo "  Frontend logs: tail -f frontend.log"
echo ""
echo "To stop servers run: ./stop.sh"
echo ""
