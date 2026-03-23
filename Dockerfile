# All-in-one Banca container
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Frontend build stage
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy frontend package files
COPY frontend/package*.json ./
RUN npm ci --only=production=false

# Build arguments for Frontend
# (No build args needed for runtime config!)

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Final runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    nginx \
    procps \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*

# Copy Python packages from backend builder
COPY --from=backend-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy backend application
COPY backend/ /app/

# Copy built frontend to nginx directory
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY frontend/nginx.conf /etc/nginx/sites-available/default
COPY frontend/nginx.conf /etc/nginx/sites-enabled/default

# Create necessary directories
RUN mkdir -p /app/storage/data /app/storage/uploads /app/storage/thumbnails /app/storage/logs \
    && chmod -R 755 /app/storage

# Copy and set up the entrypoint script
COPY entrypoint.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose only port 80
EXPOSE 80

# Start everything
CMD ["/app/start.sh"]
