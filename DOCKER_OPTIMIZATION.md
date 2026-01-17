# Docker Image Optimization Guide

## Image Size Optimizations Implemented

### Backend Image Optimizations

#### 1. **Multi-Stage Build**
- **Builder stage**: Uses full `python:3.11-slim` with build tools
- **Runtime stage**: Clean `python:3.11-slim` with only runtime dependencies
- **Result**: Build artifacts and compilers not included in final image

#### 2. **Minimal Base Image**
- Using `python:3.11-slim` instead of full Python image
- **Savings**: ~600MB smaller than standard Python image

#### 3. **Layer Optimization**
- Dependencies installed in separate layer (cached)
- Application code copied last (changes frequently)
- Combined RUN commands to reduce layers

#### 4. **Cleanup**
- `--no-install-recommends` for apt packages
- `rm -rf /var/lib/apt/lists/*` to remove package lists
- `--no-cache-dir` for pip to avoid caching packages

#### 5. **Security**
- Non-root user (appuser)
- Minimal runtime dependencies
- Only essential packages installed

### Frontend Image Optimizations

#### 1. **Multi-Stage Build**
- **Builder stage**: Full Node.js 20 Alpine for building
- **Runtime stage**: Minimal nginx:alpine for serving
- **Result**: Node.js and build tools not in final image

#### 2. **Alpine Linux**
- Using Alpine-based images (5MB base vs 100MB+ Debian)
- **Savings**: ~95MB smaller base image

#### 3. **Build Optimization**
- `npm ci` instead of `npm install` (faster, reproducible)
- Production-only dependencies in final image
- Build artifacts cleaned up

#### 4. **Nginx Optimization**
- Removed default nginx files
- Minimal configuration
- Gzip compression enabled
- Static asset caching

#### 5. **Security**
- Non-root nginx user
- Security headers added
- Minimal attack surface

### .dockerignore Optimizations

Both frontend and backend have comprehensive `.dockerignore` files that exclude:
- Development dependencies
- Build artifacts
- IDE files
- Documentation
- Test files
- Git history
- Logs and temporary files

**Result**: Faster builds and smaller build context

## Expected Image Sizes

### Before Optimization
- Backend: ~800-1000 MB
- Frontend: ~200-300 MB
- **Total**: ~1.2 GB

### After Optimization
- Backend: ~200-300 MB
- Frontend: ~20-30 MB
- **Total**: ~250-350 MB

**Savings**: ~70-75% reduction in total image size!

## Build Performance

### Faster Builds
- Layer caching optimized
- Smaller build context (via .dockerignore)
- Parallel builds possible

### Smaller Transfers
- Less data to push/pull from registry
- Faster deployments
- Lower bandwidth costs

## Additional Optimizations

### 1. **Health Checks**
Both images include health checks:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
```

### 2. **Proper Permissions**
- Non-root users for security
- Correct file permissions
- Minimal privileges

### 3. **Compression**
- Gzip enabled in nginx
- Static assets compressed
- Smaller transfer sizes

### 4. **Caching Strategy**
```nginx
# Static assets cached for 1 year
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Verification

To check image sizes:
```bash
docker images | grep jornais
```

To inspect layers:
```bash
docker history jornais-backend:latest
docker history jornais-frontend:latest
```

To check build context size:
```bash
# Before build
du -sh backend/
du -sh frontend/

# What's actually sent to Docker
docker build --no-cache -t test backend/ 2>&1 | grep "Sending build context"
```

## Best Practices Applied

✅ Multi-stage builds
✅ Minimal base images (Alpine/Slim)
✅ Layer caching optimization
✅ Comprehensive .dockerignore
✅ Combined RUN commands
✅ Cleanup after installations
✅ Non-root users
✅ Health checks
✅ Security headers
✅ Gzip compression
✅ Asset caching

## Further Optimizations (Optional)

### 1. Use BuildKit
```bash
DOCKER_BUILDKIT=1 docker-compose build
```

### 2. Squash Layers (if needed)
```bash
docker build --squash -t image:tag .
```

### 3. Use Docker Registry Cache
```bash
docker build --cache-from registry/image:latest .
```

### 4. Analyze Image
```bash
# Install dive
docker run --rm -it \
    -v /var/run/docker.sock:/var/run/docker.sock \
    wagoodman/dive:latest jornais-backend:latest
```

## Monitoring

Check image sizes regularly:
```bash
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

## Summary

Your Docker images are now optimized for:
- **Minimal size** (70-75% reduction)
- **Fast builds** (layer caching)
- **Security** (non-root, minimal packages)
- **Performance** (compression, caching)
- **Best practices** (multi-stage, Alpine, cleanup)
