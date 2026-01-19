#!/bin/bash
echo "🛑 Stopping Banca Local Servers..."
pkill -f "uvicorn app.main:app"
pkill -f "vite"
pkill -f "convex dev"
echo "✅ All local servers stopped."
