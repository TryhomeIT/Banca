#!/bin/bash
set -e

echo "🚀 Starting Banca..."

# 1. Generate runtime config for Frontend
echo "⚙️  Generating frontend config..."
echo "window.ENV = { };" > /usr/share/nginx/html/config.js

# 2. Initialize database
echo "🗄️  Initializing database..."
python init_db.py

# 3. Create default data files if missing
if [ ! -f /app/storage/publications.json ]; then
    echo "📝 Creating default publications.json..."
    echo "{\"jornais\":[],\"revistas\":[],\"keywords\":[],\"topics\":[]}" > /app/storage/publications.json
fi


# 4. Start Nginx (Frontend)
echo "🌐 Checking Nginx configuration..."
nginx -t
echo "🌐 Starting Nginx..."
nginx -g "daemon on;"

# 5. Start FastAPI server (Backend)
echo "🔧 Starting FastAPI server..."
# We use exec so uvicorn becomes PID 1 and receives signals
exec uvicorn app.main:app --host 127.0.0.1 --port 8000
