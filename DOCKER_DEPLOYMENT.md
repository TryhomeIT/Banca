# Banca - Docker Deployment Guide

## Quick Start

### Prerequisites
- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

### Setup

1. **Copy the environment file:**
   ```bash
   cp .env.docker .env
   ```

2. **Edit the `.env` file and add your Gemini API key:**
   ```bash
   nano .env
   # Update GEMINI_API_KEY with your actual key
   ```

3. **Build the Docker images:**
   ```bash
   ./docker-build.sh
   ```

4. **Start the application:**
   ```bash
   docker-compose up -d
   ```

   **OR use the all-in-one script:**
   ```bash
   ./docker-start.sh
   ```

5. **Access the application:**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Container Architecture

The application consists of 3 containers:

1. **banca-backend** - FastAPI backend (Port 8000)
2. **banca-telegram-bot** - Telegram bot service
3. **banca-frontend** - React frontend with Nginx (Port 80)

All containers communicate through the `banca-network` bridge network.

## Image Management

### Building Images

Build both images:
```bash
./docker-build.sh
```

Build individually:
```bash
# Backend
docker build -t banca-backend:latest ./backend

# Frontend
docker build -t banca-frontend:latest ./frontend
```

### Checking Images

View all Banca images:
```bash
docker images | grep banca
```

Check image sizes:
```bash
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep banca
```

## Common Commands

### Start the application
```bash
docker-compose up -d
```

### Stop the application
```bash
docker-compose down
```

### View logs
```bash
# All containers
docker-compose logs -f

# Specific container
docker-compose logs -f banca-backend
docker-compose logs -f banca-telegram-bot
docker-compose logs -f banca-frontend
```

### Restart services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart banca-backend
docker-compose restart banca-telegram-bot
docker-compose restart banca-frontend
```

### Rebuild and restart
```bash
./docker-build.sh && docker-compose restart
```

### Access container shell
```bash
docker exec -it banca-backend bash
docker exec -it banca-telegram-bot bash
docker exec -it banca-frontend sh
```

### Check container status
```bash
docker-compose ps
```

## Data Persistence

The following directories are mounted as volumes:
- `./backend/data` - Database and downloaded files
- `./backend/uploads` - Uploaded publications
- `./backend/thumbnails` - Generated thumbnails
- `./backend/logs` - Application logs

**Important**: These directories persist even when containers are stopped or removed.

## Environment Variables

Key environment variables in `.env`:

```bash
# Gemini AI API Key (Required)
GEMINI_API_KEY=your_api_key_here

# Database URL (Optional - defaults to SQLite)
DATABASE_URL=sqlite:///app/data/jornais.db
```

## Updating

To update the application:

1. **Pull latest code:**
   ```bash
   git pull
   ```

2. **Rebuild images:**
   ```bash
   ./docker-build.sh
   ```

3. **Restart containers:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Troubleshooting

### Images not found
```bash
# Build the images first
./docker-build.sh
```

### Container won't start
```bash
# Check logs
docker-compose logs banca-backend

# Rebuild from scratch
docker-compose down
./docker-build.sh
docker-compose up -d
```

### Permission issues
```bash
# Fix data directory permissions
sudo chown -R $USER:$USER backend/data
sudo chmod -R 755 backend/data
```

### Database issues
```bash
# Access the backend container
docker exec -it banca-backend bash

# Check database
ls -la /app/data/
```

### Telegram bot not connecting
```bash
# Check bot logs
docker-compose logs -f banca-telegram-bot

# Restart the bot
docker-compose restart banca-telegram-bot
```

### Port conflicts
If ports 80 or 8000 are already in use, edit `docker-compose.yml`:
```yaml
ports:
  - "8080:80"    # Change frontend port
  - "8001:8000"  # Change backend port
```

## Production Deployment

For production deployment:

1. **Use a reverse proxy with SSL:**
   ```bash
   # Example with nginx
   server {
       listen 443 ssl;
       server_name yourdomain.com;
       
       location / {
           proxy_pass http://localhost:80;
       }
   }
   ```

2. **Set up automated backups:**
   ```bash
   # Backup script
   #!/bin/bash
   tar -czf backup-$(date +%Y%m%d).tar.gz backend/data
   ```

3. **Monitor containers:**
   ```bash
   # Check health
   docker-compose ps
   
   # Watch logs
   docker-compose logs -f
   ```

4. **Use Docker secrets** for sensitive data instead of environment variables

5. **Set resource limits** in docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1'
         memory: 1G
   ```

## Cleanup

Remove containers (keeps data):
```bash
docker-compose down
```

Remove containers and volumes (deletes data):
```bash
docker-compose down -v
```

Remove images:
```bash
docker rmi banca-backend:latest
docker rmi banca-frontend:latest
```

Clean up unused Docker resources:
```bash
docker system prune -a
```

## Health Checks

Both backend and frontend have built-in health checks:

- **Backend**: `http://localhost:8000/api/health`
- **Frontend**: `http://localhost:80/health`

Check health status:
```bash
docker inspect banca-backend | grep -A 10 Health
docker inspect banca-frontend | grep -A 10 Health
```

## Performance Monitoring

Monitor resource usage:
```bash
docker stats
```

View specific container stats:
```bash
docker stats banca-backend banca-frontend banca-telegram-bot
```

## Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Verify images are built: `docker images | grep banca`
3. Check container status: `docker-compose ps`
4. Review environment variables: `cat .env`
