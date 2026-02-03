#!/bin/bash
# =============================================================================
# BillAgent Pro - Setup Script
# =============================================================================
# This script sets up the development environment for BillAgent Pro.
# Run: chmod +x setup.sh && ./setup.sh

set -e

echo ""
echo "========================================"
echo "  BillAgent Pro - Setup Script"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
check_docker() {
    echo -n "Checking Docker... "
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Docker is not running!${NC}"
        echo "Please start Docker Desktop and try again."
        exit 1
    fi
    echo -e "${GREEN}OK${NC}"
}

# Start PostgreSQL and Redis containers
start_containers() {
    echo ""
    echo "Starting PostgreSQL and Redis containers..."
    docker-compose up -d postgres redis
    
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Check if PostgreSQL is accepting connections
    for i in {1..30}; do
        if docker exec billagent-postgres pg_isready -U billagent > /dev/null 2>&1; then
            echo -e "${GREEN}PostgreSQL is ready!${NC}"
            break
        fi
        echo "Waiting for PostgreSQL... ($i/30)"
        sleep 1
    done
}

# Setup Python environment
setup_python() {
    echo ""
    echo "Setting up Python environment..."
    
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    
    cd ..
    echo -e "${GREEN}Python environment ready!${NC}"
}

# Setup environment variables
setup_env() {
    echo ""
    echo "Setting up environment variables..."
    
    if [ ! -f "backend/.env" ]; then
        cp backend/.env.example backend/.env
        echo -e "${YELLOW}Created backend/.env from template.${NC}"
        echo "Please edit backend/.env to add your API keys."
    else
        echo -e "${GREEN}backend/.env already exists.${NC}"
    fi
}

# Run database migrations
run_migrations() {
    echo ""
    echo "Running database migrations..."
    
    cd backend
    source venv/bin/activate
    
    # Run Alembic migrations
    alembic upgrade head
    
    cd ..
    echo -e "${GREEN}Migrations complete!${NC}"
}

# Seed the database
seed_database() {
    echo ""
    echo "Seeding database with initial data..."
    
    cd backend
    source venv/bin/activate
    
    python -m app.scripts.seed_db
    
    cd ..
    echo -e "${GREEN}Database seeded!${NC}"
}

# Main execution
main() {
    check_docker
    start_containers
    setup_python
    setup_env
    run_migrations
    seed_database
    
    echo ""
    echo "========================================"
    echo -e "  ${GREEN}Setup Complete!${NC}"
    echo "========================================"
    echo ""
    echo "Next steps:"
    echo "  1. Edit backend/.env with your API keys"
    echo "  2. Run the backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo "  3. Run the frontend: npm run dev"
    echo ""
    echo "API Documentation: http://localhost:8000/docs"
    echo "pgAdmin (optional): http://localhost:5050"
    echo ""
}

main "$@"
