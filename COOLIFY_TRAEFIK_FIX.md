# 🔧 Coolify/Traefik Troubleshooting Guide

## Issue: "No available server" Error

### Symptoms
- Accessing `https://api.idyntra.space/docs` shows "no available server"
- No errors in API logs
- Application container is running and healthy

### Root Causes

The "no available server" error in Coolify with Traefik typically means:

1. **Traefik cannot reach your container** (network isolation issue)
2. **Health check is failing** (wrong endpoint or timeout)
3. **Port configuration mismatch** (Traefik looking at wrong port)
4. **Middleware syntax errors** (using `@file` in container labels)
5. **Missing network connection** (container not on Traefik's network)

---

## ✅ Fixes Applied

### 1. Fixed Traefik Labels

**BEFORE (Wrong):**
```yaml
- "traefik.http.routers.api-idyntra.middlewares=api-timeouts@file,api-keepalive@file"
- "traefik.http.middlewares.api-timeouts.transport.respondingtimeouts.readtimeout=300s"
```

**AFTER (Correct):**
```yaml
- "traefik.http.routers.api-idyntra.middlewares=api-headers"
- "traefik.http.middlewares.api-headers.headers.customrequestheaders.Connection=keep-alive"
```

**Why**: 
- `@file` syntax only works with Traefik static configuration files, not Docker labels
- `transport.respondingtimeouts` is not valid in Docker label format
- Middleware must be defined inline in labels

### 2. Fixed Health Check Path

**BEFORE:**
```yaml
- "traefik.http.services.api-idyntra.loadbalancer.healthcheck.path=/health"
```

**AFTER:**
```yaml
- "traefik.http.services.api-idyntra.loadbalancer.healthcheck.path=/api/v1/health"
- "traefik.http.services.api-idyntra.loadbalancer.healthcheck.scheme=http"
- "traefik.http.services.api-idyntra.loadbalancer.healthcheck.interval=30s"
- "traefik.http.services.api-idyntra.loadbalancer.healthcheck.timeout=10s"
```

**Why**:
- Your API health endpoint is at `/api/v1/health`, not `/health`
- Must specify `scheme=http` for internal container communication
- Increased timeout to allow ML models to load

### 3. Added Network Configuration

**ADDED:**
```yaml
networks:
  - backend
  - default  # Connect to default network for Traefik access
```

**Why**:
- Coolify's Traefik runs on the default network
- Your container was isolated in the `backend` network only
- Must be on both networks: your internal + Coolify's default

### 4. Added Port Exposure

**ADDED:**
```yaml
ports:
  - "8000"  # Expose for Coolify/Traefik discovery
```

**Why**:
- `expose` only makes port available within Docker networks
- Coolify needs `ports` for service discovery
- Doesn't bind to host (no security risk)

---

## 🧪 How to Test

### 1. Check Container Status
```bash
# SSH into your Coolify server
cd /path/to/your/deployment

# Check if containers are running
docker-compose ps

# Check API container logs
docker-compose logs api --tail=50 -f

# Look for:
# ✓ "ALL COMPONENTS INITIALIZED SUCCESSFULLY"
# ✓ "Application startup complete"
```

### 2. Test Health Endpoint Internally
```bash
# Get container name
docker ps | grep api

# Test health endpoint from inside container network
docker exec <api-container-name> curl -v http://localhost:8000/api/v1/health

# Should return: {"status": "healthy", ...}
```

### 3. Check Traefik Can Reach Container
```bash
# Find Traefik container
docker ps | grep traefik

# Check Traefik logs
docker logs <traefik-container> --tail=100 | grep idyntra

# Look for:
# - No errors about "no server available"
# - Health check passing
# - Route registered
```

### 4. Test From Outside
```bash
# Test health endpoint externally
curl -v https://api.idyntra.space/api/v1/health

# Should return 200 OK with JSON
```

### 5. Test Docs Endpoint
```bash
# Test docs
curl -v https://api.idyntra.space/docs

# Should return HTML page, not "no available server"
```

---

## 🔍 Debugging Commands

### Check Network Connectivity
```bash
# List networks
docker network ls

# Inspect backend network
docker network inspect <project>_backend

# Inspect default network
docker network inspect <project>_default

# Check if API container is on both
docker inspect <api-container> | grep -A 10 Networks
```

### Check Traefik Configuration
```bash
# Check Traefik dashboard (if enabled)
# Usually at: https://traefik.yourdomain.com/dashboard/

# Or check Traefik API
curl http://localhost:8080/api/http/routers | jq
curl http://localhost:8080/api/http/services | jq
```

### Check Container Labels
```bash
# Verify labels are applied
docker inspect <api-container> | jq '.[0].Config.Labels'

# Should show all traefik.* labels
```

---

## 🚀 Deployment Steps

### 1. Update Configuration
```bash
# Pull latest changes with fixes
git pull origin main
```

### 2. Rebuild & Restart
```bash
# In Coolify dashboard:
# 1. Go to your application
# 2. Click "Redeploy"
# 3. Wait for build to complete

# OR via CLI:
cd /path/to/deployment
docker-compose down
docker-compose up -d --build
```

### 3. Verify Health
```bash
# Wait 60 seconds for ML models to load
sleep 60

# Check health
curl https://api.idyntra.space/api/v1/health

# Should return:
# {
#   "status": "healthy",
#   "version": "2.0.0",
#   "timestamp": "...",
#   ...
# }
```

### 4. Test API
```bash
# Test docs page
curl https://api.idyntra.space/docs

# Should return HTML, not "no available server"

# Test verification endpoint
curl -X POST https://api.idyntra.space/api/v1/verify \
  -H "X-API-Key: your-key" \
  -F "id_document=@test.jpg" \
  -F "selfie=@test.jpg"

# Should return JSON response
```

---

## ⚠️ Common Issues & Solutions

### Issue 1: "Gateway Timeout"
**Symptom**: 504 Gateway Timeout after 60 seconds

**Cause**: ML models taking too long to load, Traefik timing out

**Solution**: Increase startup period
```yaml
healthcheck:
  start_period: 120s  # Increase from 60s to 120s
```

### Issue 2: "Bad Gateway"
**Symptom**: 502 Bad Gateway error

**Cause**: Container crashed or not listening on port 8000

**Solution**: Check logs
```bash
docker-compose logs api --tail=100
# Look for errors during startup
```

### Issue 3: Health Check Failing
**Symptom**: Traefik logs show "health check failed"

**Cause**: Wrong health check path or container not ready

**Solution**: 
1. Verify health endpoint works:
```bash
docker exec <api-container> curl http://localhost:8000/api/v1/health
```

2. If fails, check if app is running:
```bash
docker exec <api-container> ps aux | grep uvicorn
```

### Issue 4: Still "No Available Server"
**Symptom**: After all fixes, still getting error

**Solution**: Check Traefik routing:
```bash
# 1. Verify Traefik is seeing your service
docker logs <traefik-container> | grep api-idyntra

# 2. Check if route is registered
# Visit Traefik dashboard or check API

# 3. Restart Traefik if needed
docker restart <traefik-container>

# 4. Check Coolify proxy settings
# In Coolify UI: Settings > Proxy
```

---

## 📋 Checklist

After deploying fixes, verify:

- [ ] Container is running: `docker ps | grep api`
- [ ] Container is healthy: `docker inspect <api-container> | grep -A 5 Health`
- [ ] ML models loaded: Check logs for "ALL COMPONENTS INITIALIZED"
- [ ] Health endpoint works internally: `docker exec <api-container> curl localhost:8000/api/v1/health`
- [ ] Container is on both networks: `docker inspect <api-container> | grep -A 10 Networks`
- [ ] Traefik labels are correct: `docker inspect <api-container> | jq '.[0].Config.Labels'`
- [ ] Traefik can reach service: Check Traefik logs
- [ ] Health endpoint works externally: `curl https://api.idyntra.space/api/v1/health`
- [ ] Docs page loads: `curl https://api.idyntra.space/docs`
- [ ] API responds: Test /verify endpoint

---

## 🔗 Additional Resources

### Coolify Documentation
- Traefik Configuration: https://coolify.io/docs/knowledge-base/traefik
- Docker Labels: https://coolify.io/docs/knowledge-base/docker/labels

### Traefik Documentation
- Docker Provider: https://doc.traefik.io/traefik/providers/docker/
- Health Checks: https://doc.traefik.io/traefik/routing/services/#health-check
- Middleware: https://doc.traefik.io/traefik/middlewares/overview/

### FastAPI + Traefik
- Reverse Proxy Setup: https://fastapi.tiangolo.com/deployment/docker/#traefik

---

## 💡 Prevention Tips

1. **Always test health endpoint first** before exposing to Traefik
2. **Use inline middleware** in Docker labels (never `@file`)
3. **Connect to default network** for Coolify/Traefik access
4. **Increase start_period** for apps with heavy ML models
5. **Monitor Traefik logs** during deployment
6. **Keep health check simple** - just return 200 OK, don't test ML models

---

## 🆘 Still Having Issues?

1. **Check Coolify Logs**
   ```bash
   # On Coolify server
   docker logs coolify -f
   ```

2. **Check Traefik Logs**
   ```bash
   docker logs <traefik-container> -f | grep -i error
   ```

3. **Restart Everything**
   ```bash
   # Nuclear option - restart all services
   docker-compose down
   docker system prune -f
   docker-compose up -d --build
   ```

4. **Contact Support**
   - Coolify Discord: https://coolify.io/discord
   - Traefik Community: https://community.traefik.io/
   - Check GitHub Issues: https://github.com/coollabsio/coolify/issues

---

**Last Updated**: November 2, 2025  
**Status**: ✅ Fixed  
**Version**: 2.1.0
