#!/bin/bash
# =============================================================================
# Stop Script - BillAgent Pro
# =============================================================================

# Colors
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}Stopping BillAgent Pro servers...${NC}"
echo ""

# Kill backend
pkill -f "uvicorn app.main:app" 2>/dev/null && echo -e "${GREEN}✓ Backend stopped${NC}" || echo "  No backend process found"

# Kill frontend
pkill -f "vite" 2>/dev/null && echo -e "${GREEN}✓ Frontend stopped${NC}" || echo "  No frontend process found"

echo ""
echo -e "${GREEN}All servers stopped.${NC}"
echo ""
