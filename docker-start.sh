#!/bin/bash

# Banca Docker Startup Script

set -e

echo "🚀 Starting Banca..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install docker-compose."
    exit 1
fi

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data

# Check if image exists
if ! docker images | grep -q "^banca "; then
    echo "🔨 Image not found. Building..."
    ./docker-build.sh
else
    echo "✅ Image found. Skipping build."
    echo "   To rebuild, run: ./docker-build.sh"
fi

echo ""
echo "🚀 Starting container..."
docker-compose up -d

# Wait for service to be healthy
echo "⏳ Waiting for service to start..."
sleep 5

# Check status
echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "✅ Banca is running!"
echo ""
echo "🌐 Access the application:"
echo "   http://localhost"
echo ""
echo "⚙️  First time setup:"
echo "   1. Create an account"
echo "   2. Go to Settings"
echo "   3. Add your Gemini API key"
echo ""
echo "📋 Useful commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop: docker-compose down"
echo "   Restart: docker-compose restart"
echo "   Rebuild: ./docker-build.sh && docker-compose restart"
echo ""
