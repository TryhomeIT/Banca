#!/bin/bash

# Banca Docker Image Build Script

set -e

echo "🔨 Building Banca All-in-One Image..."
echo ""

# Build the single image
echo "📦 Building banca:latest..."
docker build -t banca:latest .
echo "✅ Image built successfully"
echo ""

# Show image size
echo "📊 Image Size:"
docker images | grep banca
echo ""

echo "✅ Build complete!"
echo ""
echo "To start the application:"
echo "  docker-compose up -d"
echo ""
echo "To rebuild and start:"
echo "  ./docker-build.sh && docker-compose up -d"
