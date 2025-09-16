#!/bin/bash

# Docker run script for NLWeb Crawler
# Usage: ./docker-run.sh [mode] [args...]
# Modes: dev, prod, test, shell

set -e

# Default mode
MODE=${1:-dev}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}NLWeb Crawler Docker Runner${NC}"
echo "Mode: $MODE"

# Check if .env file exists and load it
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

case $MODE in
    "dev")
        echo -e "${YELLOW}Starting development environment...${NC}"
        docker-compose -f docker-compose.dev.yml up --build
        ;;
    "prod")
        echo -e "${YELLOW}Starting production environment...${NC}"
        docker-compose up --build -d
        ;;
    "test")
        echo -e "${YELLOW}Running tests...${NC}"
        docker-compose -f docker-compose.dev.yml run --rm crawler-dev python test_database_loading.py
        ;;
    "shell")
        echo -e "${YELLOW}Opening shell in development container...${NC}"
        docker-compose -f docker-compose.dev.yml run --rm crawler-dev bash
        ;;
    "crawl")
        echo -e "${YELLOW}Running crawler with site: ${2:-example.com}${NC}"
        shift # Remove 'crawl' from arguments
        docker-compose -f docker-compose.dev.yml run --rm crawler-dev python code/crawler.py "$@"
        ;;
    "clean")
        echo -e "${YELLOW}Cleaning up Docker resources...${NC}"
        docker-compose -f docker-compose.dev.yml down
        docker-compose down
        docker system prune -f
        ;;
    "logs")
        echo -e "${YELLOW}Showing logs...${NC}"
        docker-compose -f docker-compose.dev.yml logs -f
        ;;
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Available modes:"
        echo "  dev    - Start development environment"
        echo "  prod   - Start production environment"
        echo "  test   - Run tests"
        echo "  shell  - Open shell in container"
        echo "  crawl  - Run crawler with arguments"
        echo "  clean  - Clean up Docker resources"
        echo "  logs   - Show container logs"
        exit 1
        ;;
esac
