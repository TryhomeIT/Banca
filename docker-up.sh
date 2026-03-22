#!/bin/bash

# Banca - Docker Management Script
# Starts the application in a production-ready container

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

show_help() {
    echo "Usage:"
    echo "  ./docker-up.sh            - Start Banca using Docker Compose"
    echo "  ./docker-up.sh --build    - Force rebuild the image before starting"
    echo "  ./docker-up.sh --stop     - Stop and remove the container"
    echo "  ./docker-up.sh --logs     - Follow container logs"
    echo "  ./docker-up.sh --status   - Show container status"
}

check_dependencies() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ docker-compose not found. Please install it.${NC}"
        exit 1
    fi
}

build_image() {
    echo -e "${BLUE}🔨 Building Banca Docker Image...${NC}"
    docker build -t banca:latest .
    echo -e "${GREEN}✅ Image built successfully.${NC}"
}

case "$1" in
    --build)
        check_dependencies
        build_image
        docker-compose up -d
        ;;
    --stop)
        docker-compose down
        ;;
    --logs)
        docker-compose logs -f
        ;;
    --status)
        docker-compose ps
        ;;
    --help|-h)
        show_help
        ;;
    "")
        check_dependencies
        mkdir -p data
        if ! docker images | grep -q "^banca "; then
            build_image
        fi
        docker-compose up -d
        echo -e "${GREEN}🚀 Banca is running at http://localhost${NC}"
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        show_help
        exit 1
        ;;
esac
