#!/bin/bash

# Banca - Build and Deploy to Server
# Builds the Docker image locally, saves it, transfers to server, and loads it

set -e

SERVER="192.168.1.252"
SERVER_USER="administrator"
SERVER_PASS="Diana2018"
IMAGE_NAME="banca:latest"
ARCHIVE_NAME="banca-image.tar"

echo "🔨 Building Banca Docker Image..."
echo ""

# 0. Deploy Convex Functions
echo "☁️  Deploying Convex Schema & Functions..."
cd frontend
npx convex deploy --yes
if [ $? -ne 0 ]; then
    echo "❌ Convex deployment failed! Check your login status."
    exit 1
fi
cd ..
echo "✅ Convex deployed successfully"
echo ""

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "⚠️  sshpass not found. Installing..."
    sudo apt-get update && sudo apt-get install -y sshpass
fi

# Build the image
echo "📦 Building ${IMAGE_NAME}..."
docker build -t ${IMAGE_NAME} .

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Image built successfully"
echo ""

# Show image size
echo "📊 Image Size:"
docker images | grep banca
echo ""

# Save image to tar file
echo "💾 Saving image to ${ARCHIVE_NAME}..."
docker save ${IMAGE_NAME} -o ${ARCHIVE_NAME}

if [ $? -ne 0 ]; then
    echo "❌ Failed to save image!"
    exit 1
fi

echo "✅ Image saved ($(du -h ${ARCHIVE_NAME} | cut -f1))"
echo ""

# Transfer to server
echo "📤 Transferring image to ${SERVER}..."
sshpass -p "${SERVER_PASS}" scp -o StrictHostKeyChecking=no ${ARCHIVE_NAME} ${SERVER_USER}@${SERVER}:/tmp/

if [ $? -ne 0 ]; then
    echo "❌ Transfer failed!"
    rm ${ARCHIVE_NAME}
    exit 1
fi

echo "✅ Image transferred successfully"
echo ""

# Transfer docker-compose.yml
echo "📄 Transferring docker-compose.yml to ${SERVER}..."
sshpass -p "${SERVER_PASS}" scp -o StrictHostKeyChecking=no docker-compose.yml ${SERVER_USER}@${SERVER}:/tmp/docker-compose.yml

if [ $? -ne 0 ]; then
    echo "⚠️  Failed to transfer docker-compose.yml (Non-fatal)"
else
    echo "✅ docker-compose.yml transferred to /tmp/"
fi

echo ""

# Load image on server
echo "📥 Loading image on server..."
sshpass -p "${SERVER_PASS}" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER} "docker load -i /tmp/${ARCHIVE_NAME}"

if [ $? -ne 0 ]; then
    echo "❌ Failed to load image on server!"
    rm ${ARCHIVE_NAME}
    exit 1
fi

echo "✅ Image loaded on server"
echo ""

# Cleanup
echo "🧹 Cleaning up local archive..."
rm ${ARCHIVE_NAME}

# Cleanup on server
echo "🧹 Cleaning up server archive..."
sshpass -p "${SERVER_PASS}" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER} "rm /tmp/${ARCHIVE_NAME}"

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📋 Image is loaded on server but NOT applied"
echo ""
echo "To apply on server:"
echo "  ssh ${SERVER_USER}@${SERVER}"
echo "  cd /path/to/banca"
echo "  docker-compose down"
echo "  docker-compose up -d"
echo ""
