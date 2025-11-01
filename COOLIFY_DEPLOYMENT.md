# Coolify Deployment Guide

## Issue: Network Conflict Error

```
failed to create network: numerical result out of range
```

**Root Cause**: Your `docker-compose.yml` has hardcoded subnet configurations (`172.20.0.0/16`, etc.) that conflict with Coolify's dynamic network management.

## Solution: Use Coolify-Compatible Configuration

### Option 1: Use the Coolify-Optimized Compose File

```bash
# Rename your current compose file
mv docker-compose.yml docker-compose.original.yml

# Use the Coolify-compatible version
cp docker-compose.coolify.yml docker-compose.yml

# Deploy in Coolify
git add .
git commit -m "Use Coolify-compatible docker-compose"
git push
```

### Option 2: Fix Your Existing docker-compose.yml

Remove the hardcoded network configurations:

**Remove this:**
```yaml
networks:
  backend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16  # ❌ Remove
    driver_opts:
      com.docker.network.bridge.name: idyntra-backend  # ❌ Remove
```

**Replace with:**
```yaml
networks:
  backend:
    driver: bridge
    # Let Coolify manage IP allocation dynamically
```

## Coolify-Specific Configuration

### 1. Environment Variables
Set these in Coolify's environment variables section:

**Required:**
```bash
POSTGRES_PASSWORD=<generate-strong-password>
REDIS_PASSWORD=<generate-strong-password>
SECRET_KEY=<generate-secret-key>
API_KEY_HASH_SALT=<generate-salt>
```

**Optional:**
```bash
VERSION=2.0.0
WORKERS=4
LOG_LEVEL=INFO
CPU_ONLY=1
```

### 2. Domain Configuration
In Coolify:
1. Go to your application → **Domains**
2. Add your domain: `api.yourdomain.com`
3. Enable **SSL/TLS** (Coolify handles this automatically)
4. No need for nginx - Coolify provides reverse proxy

### 3. Port Configuration
- **Internal Port**: `8000` (API listens on this)
- **External Port**: Let Coolify manage (usually 80/443)
- Remove nginx service - Coolify handles SSL termination

### 4. Persistent Storage
Coolify automatically manages volumes. The following volumes are created:
- `postgres_data` - Database storage
- `redis_data` - Cache storage
- `model_cache` - ML models (persists between deployments)
- `api_logs` - Application logs

### 5. Services to Remove for Coolify

Remove these services from your compose file (Coolify handles them):
- ❌ `nginx` - Coolify provides reverse proxy
- ❌ `prometheus` - Use Coolify's built-in monitoring
- ❌ `grafana` - Use Coolify's dashboard
- ❌ `log-cleanup` - Coolify manages log rotation

**Keep only:**
- ✅ `postgres`
- ✅ `redis`
- ✅ `api`

## Minimal Coolify docker-compose.yml

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-idverification}
      POSTGRES_USER: ${POSTGRES_USER:-idv_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-idv_user}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - backend
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  api:
    build:
      context: .
      dockerfile: Dockerfile.production
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-idv_user}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-idverification}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      API_KEY_HASH_SALT: ${API_KEY_HASH_SALT}
      CPU_ONLY: 1
    volumes:
      - model_cache:/root/.cache
      - api_logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    networks:
      - backend
    healthcheck:
      test: ["CMD", "/app/healthcheck.sh"]
      interval: 30s
      timeout: 10s
      start_period: 60s

volumes:
  postgres_data:
  redis_data:
  model_cache:
  api_logs:

networks:
  backend:
    driver: bridge
```

## Deployment Steps in Coolify

### Step 1: Create New Application
1. Go to Coolify Dashboard
2. Click **"+ New Resource"**
3. Select **"Docker Compose"**
4. Connect your Git repository: `https://github.com/ayoub-sahraoui/idyntra-backend`

### Step 2: Configure Build
1. **Branch**: `main`
2. **Base Directory**: `/backend/v1` (if applicable)
3. **Docker Compose File**: `docker-compose.yml` or `docker-compose.coolify.yml`
4. **Build Command**: (leave default)

### Step 3: Set Environment Variables
In Coolify → Your App → Environment Variables:

```bash
# Generate these securely
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)
API_KEY_HASH_SALT=$(openssl rand -base64 16)

# Configuration
POSTGRES_DB=idverification
POSTGRES_USER=idv_user
VERSION=2.0.0
WORKERS=4
LOG_LEVEL=INFO
CPU_ONLY=1
DEBUG=false
```

### Step 4: Configure Domain
1. Add your domain in Coolify
2. Enable **Auto SSL** (Let's Encrypt)
3. Coolify will handle SSL termination

### Step 5: Deploy
1. Click **"Deploy"**
2. Monitor logs in real-time
3. Wait for health checks to pass

### Step 6: Verify Deployment
```bash
# Check health endpoint
curl https://api.yourdomain.com/health

# Should return:
{"status": "healthy"}
```

## Troubleshooting in Coolify

### Check Logs
In Coolify Dashboard:
1. Go to your application
2. Click **"Logs"** tab
3. Select service: `api`, `postgres`, or `redis`

### Restart Services
```bash
# In Coolify, just click "Restart" button
# Or via CLI on your server:
docker-compose restart api
```

### Check Running Containers
```bash
docker ps
docker logs <container-name>
```

### Network Issues
```bash
# Clean up old networks
docker network prune -f

# List networks
docker network ls

# Redeploy in Coolify
```

## Performance Optimization for Coolify

### 1. Enable BuildKit
In your Dockerfile, BuildKit is already used for faster builds.

### 2. Use Coolify's Build Cache
Coolify automatically caches Docker layers between builds.

### 3. Resource Limits
Set in docker-compose.yml:
```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 6G
```

### 4. Health Checks
Already configured - Coolify will monitor and restart unhealthy containers.

## Common Coolify Errors & Fixes

### Error: "Network already exists"
```bash
docker network prune -f
# Redeploy in Coolify
```

### Error: "Port already in use"
- Coolify manages port mapping
- Don't expose ports externally except 8000
- Remove `ports` section or use Coolify's port mapping

### Error: "Volume mount failed"
- Coolify creates volumes automatically
- Don't use `bind` mounts in production
- Use named volumes instead

## Migration Checklist

- [ ] Remove hardcoded network subnets from docker-compose.yml
- [ ] Remove nginx service (Coolify handles reverse proxy)
- [ ] Remove prometheus/grafana (use Coolify monitoring)
- [ ] Set all environment variables in Coolify
- [ ] Configure domain and SSL in Coolify
- [ ] Test health endpoint after deployment
- [ ] Monitor logs for model download (first startup may take 5 min)
- [ ] Verify API endpoints work correctly

## Next Steps

1. **Commit changes:**
   ```bash
   git add docker-compose.coolify.yml COOLIFY_DEPLOYMENT.md
   git commit -m "Add Coolify-compatible configuration"
   git push
   ```

2. **Deploy in Coolify:**
   - Point Coolify to your repository
   - Set environment variables
   - Click Deploy

3. **Monitor first deployment:**
   - Watch logs for model downloads
   - First request may take 2-5 minutes
   - Subsequent requests will be instant

## Support

If you encounter issues:
1. Check Coolify logs
2. Check Docker logs: `docker logs <container>`
3. Verify environment variables are set
4. Ensure domain DNS is configured
5. Check Coolify Discord/Documentation

Your build is working! This is just a network configuration issue specific to Coolify. 🚀
