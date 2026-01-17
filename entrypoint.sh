#!/bin/bash
set -e

echo "🚀 Starting Banca..."

# 1. Generate runtime config for Frontend
echo "⚙️  Generating frontend config..."
echo "window.ENV = { CONVEX_URL: \"${CONVEX_URL}\" };" > /usr/share/nginx/html/config.js
echo "📝 Generated config.js content:"
cat /usr/share/nginx/html/config.js

# 2. Initialize database
echo "🗄️  Initializing database..."
python init_db.py

# 3. Create default data files if missing
if [ ! -f /app/storage/publications.json ]; then
    echo "📝 Creating default publications.json..."
    echo "{\"jornais\":[],\"revistas\":[],\"keywords\":[],\"topics\":[]}" > /app/storage/publications.json
fi

# DEBUG: Check paths
echo "🕵️ Running Encoding Diagnostics..."
python diagnose_encoding.py

# 4. Start Nginx (Frontend)
echo "🌐 Starting Nginx..."
nginx

# 5. Start FastAPI server (Backend)
echo "🔧 Starting FastAPI server..."
# We bind to 127.0.0.1 because Nginx proxies to it
exec uvicorn app.main:app --host 127.0.0.1 --port 8000
