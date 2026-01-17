#!/bin/bash

# Banca Backend Entrypoint
# Starts both FastAPI and Telegram Bot

set -e

echo "🚀 Starting Banca Backend..."

# Start Telegram bot in background
echo "🤖 Starting Telegram bot..."
python telegram_bot/telegram_downloader.py &

# Start FastAPI server in foreground
echo "🔧 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
