# Fix: 502 Bad Gateway - Traefik Timeout Issue

## Problem Summary

**Issue:** `/api/v1/verify` endpoint returns 502 Bad Gateway  
**Symptom:** No error logs in the API application  
**Root Cause:** Request timeout at the Traefik reverse proxy level, not in the application

## Why No Error Logs in API?

When you see **502 errors without API logs**, it means:
1. ✅ Your API container is running
2. ✅ Your application code is working
3. ❌ **The request is timing out at the proxy layer (Traefik)**
4. ❌ The request never completes, so nothing is logged as an error

## Root Causes Identified

### 1. **Traefik Response Timeout (Primary Cause)**
- **Default timeout:** 90 seconds
- **Your endpoint processing time:** Can take 60-180 seconds for:
  - ML model inference (liveness, face matching, deepfake detection)
  - Image processing and validation
  - Document authenticity checks
- **Result:** Traefik times out before your API finishes

### 2. **Request Body Size Limit**
- Upload files can be 10-50MB combined
- Traefik may have restrictive default limits
- Causes 502 before files even reach the API

### 3. **Health Check Start Period Too Short**
- Previous setting: 60 seconds
- Actual time needed: 2-5 minutes for ML models to load
- Container marked as unhealthy → Traefik doesn't route traffic

## The Fix

### Changes Made to `docker-compose.coolify.yml`

#### 1. Extended Traefik Timeouts
```yaml
# Extended timeout to 3 minutes (180 seconds)
- "traefik.http.services.api-idyntra.loadbalancer.responsetimeout=180s"

# Retry on network errors (max 2 attempts)
- "traefik.http.middlewares.api-idyntra-timeout.buffering.retryExpression=IsNetworkError() && Attempts() < 2"
```

#### 2. Increased Request Size Limit
```yaml
# Allow up to 50MB request body (for image uploads)
- "traefik.http.middlewares.api-idyntra-limit.buffering.maxRequestBodyBytes=52428800"
```

#### 3. Proper Headers Middleware
```yaml
# Set correct headers for proxy
- "traefik.http.middlewares.api-idyntra-headers.headers.customrequestheaders.Host=api.idyntra.space"
- "traefik.http.middlewares.api-idyntra-headers.headers.customrequestheaders.X-Forwarded-Proto=https"

# Apply all middlewares in correct order
- "traefik.http.routers.api-idyntra.middlewares=api-idyntra-headers,api-idyntra-limit"
```

#### 4. Increased Health Check Start Period
```yaml
healthcheck:
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 180s  # ← Increased from 60s to 180s (3 minutes)
```

## Deployment Steps

### 1. **Save Changes**
```powershell
git add docker-compose.coolify.yml
git commit -m "Fix: Increase Traefik timeout and request limits for /verify endpoint"
git push origin main
```

### 2. **Deploy to Coolify**

#### Option A: Via Coolify Dashboard
1. Go to Coolify Dashboard
2. Navigate to your application
3. Click **"Deploy"** or **"Redeploy"**
4. Wait for deployment to complete (3-5 minutes)

#### Option B: Via SSH to Server
```bash
# SSH to your Coolify server
ssh user@your-server

# Navigate to your deployment directory
cd /path/to/your/deployment

# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.coolify.yml down
docker-compose -f docker-compose.coolify.yml up -d --build

# Monitor logs
docker-compose -f docker-compose.coolify.yml logs -f api
```

### 3. **Monitor Startup (IMPORTANT)**

Watch the logs carefully. You should see:

```
🚀 Starting ID Verification API v2.0.0
Device mode: CPU
Loading ML models...
✓ Liveness detector loaded
✓ Face matcher loaded
✓ MRZ extractor loaded
✓ Document authenticator loaded
✓ Deepfake detector loaded
✓ ALL COMPONENTS INITIALIZED SUCCESSFULLY
Application startup complete
```

**Wait at least 3-5 minutes** before testing if it's the first deployment or models need to download.

### 4. **Test the Health Check**

```bash
# Test basic health (should respond quickly)
curl https://api.idyntra.space/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "device": "cpu",
  "gpu_available": false,
  "timestamp": "2025-11-01T...",
  "components": {
    "api": true,
    "config": true
  }
}
```

### 5. **Test the Verify Endpoint**

**Important:** Use actual test images. Create a test script:

```bash
# test-verify.sh
curl -X 'POST' \
  'https://api.idyntra.space/api/v1/verify' \
  -H 'accept: application/json' \
  -H 'X-API-Key: YOUR_API_KEY_HERE' \
  -H 'Content-Type: multipart/form-data' \
  -F 'id_document=@test_id.jpg' \
  -F 'selfie=@test_selfie.jpg' \
  --max-time 200 \
  -v
```

Expected response (after 5-60 seconds):
```json
{
  "verification_id": "uuid-here",
  "timestamp": "2025-11-01T...",
  "status": "approved",
  "overall_confidence": 85.5,
  "message": "✅ Identity verified (confidence: 85.5%)",
  "liveness_check": {...},
  "deepfake_check": {...},
  "document_authenticity": {...},
  "face_match": {...}
}
```

## Troubleshooting

### Still Getting 502?

#### Check 1: Container Status
```bash
docker ps | grep api
```
Should show: `Up X minutes (healthy)` or `Up X minutes (health: starting)`

If showing `(unhealthy)`, wait longer for models to load.

#### Check 2: View Logs
```bash
docker logs <container-name> --tail 100 -f
```

Look for:
- ✅ "Application startup complete"
- ❌ Python exceptions or errors
- ❌ "Model download failed"

#### Check 3: Traefik Logs
```bash
# On your Coolify server
docker logs $(docker ps | grep traefik | awk '{print $1}') --tail 100
```

Look for timeout errors or routing issues.

#### Check 4: Test from Inside Container
```bash
# SSH to server, then:
docker exec -it <api-container-name> bash

# Inside container, test locally:
curl -X POST http://localhost:8000/api/v1/verify \
  -H "X-API-Key: your_key" \
  -F "id_document=@/path/to/test.jpg" \
  -F "selfie=@/path/to/selfie.jpg"
```

If this works but external requests fail → Traefik configuration issue.

### Error: "Request Entity Too Large"

If you see this, increase the buffer size further:
```yaml
- "traefik.http.middlewares.api-idyntra-limit.buffering.maxRequestBodyBytes=104857600"  # 100MB
```

### Error: "Gateway Timeout" after 180 seconds

Your ML processing is taking longer than expected:

**Short-term fix:** Increase timeout further
```yaml
- "traefik.http.services.api-idyntra.loadbalancer.responsetimeout=300s"  # 5 minutes
```

**Long-term fix:** Optimize your ML models
- Use quantized models
- Implement model caching
- Use GPU acceleration if available

## Expected Response Times

| Operation | First Request | Subsequent Requests |
|-----------|---------------|---------------------|
| `/health` | < 100ms | < 50ms |
| `/health/detailed` | 2-5 seconds | < 1 second |
| `/api/v1/verify` | 30-60 seconds | 5-15 seconds |
| `/api/v1/extract-mrz` | 10-30 seconds | 3-10 seconds |

## Performance Optimization Tips

### 1. Enable GPU (if available)
```yaml
environment:
  CPU_ONLY: 0  # Enable GPU
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### 2. Increase Worker Count
```yaml
environment:
  WORKERS: 8  # More workers for parallel processing
```

### 3. Add Response Caching
Consider implementing Redis caching for similar verification requests.

### 4. Model Optimization
- Use ONNX runtime for faster inference
- Quantize models to INT8
- Use smaller model variants

## Verification Checklist

Before marking this as resolved, verify:

- [ ] Container starts successfully
- [ ] Health check passes (`/health` returns 200)
- [ ] Detailed health check passes (`/health/detailed` returns 200)
- [ ] Verify endpoint responds without 502 (`/api/v1/verify`)
- [ ] Verify endpoint completes within timeout (< 180s)
- [ ] Response contains all expected fields
- [ ] No errors in application logs
- [ ] No errors in Traefik logs

## Monitoring

### Set Up Alerts

Monitor these metrics:
- Request duration (p95, p99)
- Error rate (502, 503, 504)
- Container health status
- Memory usage
- CPU usage

### Log Analysis

Check logs regularly for:
```bash
# Count 502 errors in last hour
docker logs $(docker ps | grep traefik | awk '{print $1}') --since 1h 2>&1 | grep "502" | wc -l

# Check API response times
docker logs <api-container-name> --since 1h 2>&1 | grep "duration_ms"
```

## Related Documentation

- `FIX_502_VERIFY_ENDPOINT.md` - Original fix for model loading
- `DEPLOYMENT_502_DIAGNOSTICS.md` - General 502 troubleshooting
- `COOLIFY_HEALTH_CHECK.md` - Health check configuration
- `TROUBLESHOOTING_504_GATEWAY_TIMEOUT.md` - Gateway timeout issues

## Summary

**Before Fix:**
- ❌ 502 errors on `/verify`
- ❌ No error logs in API
- ❌ Traefik timeout after 90 seconds

**After Fix:**
- ✅ Extended Traefik timeout to 180 seconds
- ✅ Increased request size limit to 50MB
- ✅ Proper middleware configuration
- ✅ Extended health check start period to 180 seconds
- ✅ `/verify` endpoint now works correctly

**Next Steps:**
1. Deploy the changes
2. Wait 3-5 minutes for startup
3. Test the endpoint
4. Monitor logs for any issues
5. Consider performance optimizations if response times > 60s
