# Deployment Diagnostics Guide for Coolify

## 502 Bad Gateway Error

Your API is deployed but returning 502 errors. This typically means:

### Possible Causes:

1. **Container keeps restarting** - Application crashes on startup
2. **Health check failing** - Container unhealthy
3. **Port mismatch** - App not listening on expected port
4. **Memory/CPU limits** - Container being killed

## Check These in Coolify:

### 1. Check Container Logs
In Coolify Dashboard → Your Application → Logs:

Look for:
- ❌ Python exceptions/tracebacks
- ❌ "Address already in use" errors
- ❌ Import errors
- ❌ Configuration errors
- ✅ "🚀 Starting ID Verification API"

### 2. Check Container Status
```bash
# In Coolify logs or SSH to server
docker ps | grep api

# Should show: Up X minutes (healthy)
# If showing "Restarting" or "Unhealthy" - there's a problem
```

### 3. Check Health Endpoint
```bash
# SSH to your server and run:
docker exec <api-container-name> curl http://localhost:8000/health

# Expected: {"status":"healthy"}
# If this fails, health check is failing
```

### 4. Check Resource Limits
In docker-compose.coolify.yml:
```yaml
deploy:
  resources:
    limits:
      memory: 6G  # Make sure you have enough RAM
      cpus: '4'
```

## Common Issues & Fixes:

### Issue 1: Models Not Loading
**Symptom:** Container starts but crashes when accessing API

**Fix:** Models are being downloaded at runtime (first request takes 2-5 minutes)
```bash
# Check if models are downloading in logs
docker logs <container-name> | grep -i "model\|download"
```

### Issue 2: Database Connection Failed
**Symptom:** Container can't connect to PostgreSQL

**Fix:** Ensure PostgreSQL container is healthy first
```bash
docker ps | grep postgres
# Should show: Up X minutes (healthy)
```

### Issue 3: Port Already in Use
**Symptom:** "Address already in use" error

**Fix:** Make sure no port mappings conflict. In Coolify-compatible compose, use `expose` not `ports`.

### Issue 4: Missing Environment Variables
**Symptom:** Config parsing errors

**Fix:** Set required variables in Coolify:
```bash
POSTGRES_PASSWORD=<your-password>
REDIS_PASSWORD=<your-password>
SECRET_KEY=<your-secret>
API_KEY_HASH_SALT=<your-salt>
```

## Quick Diagnostic Commands

### On Your Server (SSH):

```bash
# 1. Check all containers
docker-compose ps

# 2. View API logs (last 100 lines)
docker logs <api-container-name> --tail 100

# 3. Check if API is listening
docker exec <api-container-name> netstat -tlnp | grep 8000

# 4. Test health endpoint internally
docker exec <api-container-name> curl -v http://localhost:8000/health

# 5. Check container resources
docker stats <api-container-name>

# 6. Inspect container
docker inspect <api-container-name> | grep -A 10 "Health"
```

## Expected Startup Sequence:

1. ✅ Container starts
2. ✅ "🚀 Starting ID Verification API v2.0.0"
3. ✅ "✓ All components initialized"
4. ⏳ Models downloading (first time: 2-5 minutes)
5. ✅ Uvicorn listening on 0.0.0.0:8000
6. ✅ Health check passes

## If Models Are Downloading:

During first startup, you'll see:
```
📥 Loading face recognition models...
✅ Face recognition models loaded
```

This is **normal** and can take 2-5 minutes. The API will return 502 during this time.

**Solution:** Wait 5 minutes and try again!

## Testing Steps:

### 1. Wait for Startup
```bash
# Watch logs in real-time
docker logs -f <api-container-name>

# Wait until you see:
# "Application startup complete"
```

### 2. Test Health Endpoint
```bash
curl https://api.idyntra.space/health

# Expected: {"status":"healthy"}
```

### 3. Test API Endpoint
```bash
curl https://api.idyntra.space/docs

# Expected: Swagger UI HTML
```

### 4. Test Verification (with valid API key)
```bash
curl -X POST https://api.idyntra.space/api/v1/verify \
  -H "X-API-Key: your-api-key" \
  -F "id_document=@id.jpg" \
  -F "selfie=@selfie.jpg"
```

## Most Likely Issue:

Based on your 502 error, the most likely causes are:

1. **Models still downloading** (first startup)
   - Solution: Wait 5 minutes and retry

2. **Container restarting due to crash**
   - Check logs for Python exceptions
   - Look for import errors or missing dependencies

3. **Health check failing**
   - Health check script might be failing
   - App not responding on port 8000

## Immediate Actions:

1. **Check Coolify logs RIGHT NOW** - Look for Python errors
2. **Wait 5 minutes** - If models are downloading
3. **Verify environment variables** - Ensure all required vars are set
4. **Check container status** - Should be "Up" and "healthy"

## Need Help?

Share the following information:
1. Container logs (last 50 lines from Coolify)
2. Container status: `docker ps | grep api`
3. Health check result: `curl http://localhost:8000/health` (from inside container)
4. Time since last deployment (if < 5 minutes, models might still be downloading)

## Pro Tip:

Add this to your Coolify environment variables for better debugging:
```bash
LOG_LEVEL=DEBUG
```

Then redeploy and check logs for detailed information.
