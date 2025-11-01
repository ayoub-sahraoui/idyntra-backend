# Quick Fix: 502 Error on /verify Endpoint

## Current Status

✅ **Application is running**  
✅ **Health endpoint works**  
✅ **Swagger docs work**  
❌ **/verify returns 502**

## Root Cause

From your logs, I can see:
```
INFO:     Application startup complete.
```

But there's **NO output** for:
```
Loading ML models...
✓ Liveness detector loaded
✓ Face matcher loaded
...
```

**This means models are NOT loading at startup!** They're loading on the first `/verify` request, causing timeout and 502.

## Why Models Aren't Loading

With `WORKERS=4`, Uvicorn spawns 4 worker processes. The lifespan function runs in EACH worker, causing:

1. **4x memory usage** (each worker loads 2-4GB of models)
2. **Slower startup** (all workers loading simultaneously)
3. **Race conditions** (workers competing for resources)
4. **Log confusion** (multiple processes logging)

## The Fix

### 1. Reduce Workers (Applied)

Changed from 4 workers to 2 workers:
```yaml
WORKERS: ${WORKERS:-2}  # Each worker loads ~4GB of models
```

**Benefits:**
- ✅ Less memory pressure (8GB instead of 16GB)
- ✅ Faster startup
- ✅ More reliable model loading
- ✅ Still handles concurrent requests well

### 2. Set API Key in Coolify

Your `/verify` endpoint requires authentication. Set this in Coolify:

**In Coolify Dashboard → Environment Variables:**
```bash
VALID_API_KEYS=your-secret-api-key-here
```

**Or generate a secure key:**
```bash
# Generate a random API key
openssl rand -hex 32
```

Then use it in requests:
```bash
curl -X POST https://api.idyntra.space/api/v1/verify \
  -H "X-API-Key: your-secret-api-key-here" \
  -F "id_document=@test.jpg" \
  -F "selfie=@selfie.jpg"
```

### 3. Deploy and Test

```powershell
# Commit changes
git add -A
git commit -m "Fix: Reduce workers to 2 for better ML model loading stability"
git push

# Deploy in Coolify
# Wait 3-5 minutes for models to load

# Check logs for model loading
docker logs <container-name> 2>&1 | grep -E "Loading ML|detector loaded|ALL COMPONENTS"
```

## Expected Logs After Fix

You should see (in logs for EACH of the 2 workers):

```
==========================================
🚀 Starting ID Verification API v2.0.0 [PID: 28]
Device mode: CPU
Debug mode: False
==========================================
Loading ML models...
✓ Liveness detector loaded
✓ Face matcher loaded
✓ MRZ extractor loaded
✓ Document authenticator loaded
✓ Deepfake detector loaded
==========================================
✓ ALL COMPONENTS INITIALIZED SUCCESSFULLY
==========================================
INFO:     Application startup complete.
```

## Testing Sequence

### 1. Test Health (should work immediately)
```bash
curl https://api.idyntra.space/health
```

### 2. Test with API Key (after 5 minutes)
```bash
curl -X POST https://api.idyntra.space/api/v1/verify \
  -H "X-API-Key: your-secret-api-key-here" \
  -H "Content-Type: multipart/form-data" \
  -F "id_document=@test_id.jpg" \
  -F "selfie=@test_selfie.jpg" \
  -v
```

### 3. Without API Key (should get 403, not 502)
```bash
curl -X POST https://api.idyntra.space/api/v1/verify \
  -F "id_document=@test_id.jpg" \
  -F "selfie=@selfie.jpg"

# Expected: {"detail":"API key is required"}
```

## Troubleshooting

### Still Getting 502?

**Check 1: Are models actually loading?**
```bash
docker logs <container-name> 2>&1 | grep "Loading ML models"
```

If you don't see this message, the lifespan function isn't running properly.

**Check 2: Memory usage**
```bash
docker stats <container-name>
```

Each worker needs ~4GB. With 2 workers, you need 8GB+ total.

**Check 3: Container health**
```bash
docker ps | grep api
```

Should show: `(healthy)` not `(unhealthy)` or `(health: starting)`

### Getting 403 Forbidden?

✅ **This is GOOD!** It means:
- Request reached your API
- Models are loaded
- Just need to add API key

Set `VALID_API_KEYS` in Coolify environment variables.

### Still No Model Loading Logs?

The issue might be with how Uvicorn handles workers. Try:

**Option A: Use single worker temporarily**
```yaml
WORKERS: 1  # Forces single process, easier debugging
```

**Option B: Use preload**

Modify the startup script in Dockerfile to add `--preload`:
```bash
uvicorn app.main:app --preload --workers 2 ...
```

This loads the app before forking workers.

## Memory Considerations

| Workers | Memory per Worker | Total Memory Needed |
|---------|-------------------|---------------------|
| 1 | 4GB | 5GB (with OS overhead) |
| 2 | 4GB | 9GB (recommended) |
| 4 | 4GB | 17GB (too much!) |

Your Coolify deployment has a 6GB limit. With 2 workers (8GB needed), it's tight but should work if models share memory efficiently.

## Alternative Solution: Use Gunicorn

If Uvicorn workers continue causing issues, consider using Gunicorn with Uvicorn workers:

```bash
gunicorn app.main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --preload \
  --bind 0.0.0.0:8000
```

The `--preload` flag ensures the app (and models) load ONCE before forking workers.

## Summary of Changes

1. ✅ **Reduced workers from 4 to 2** (less memory, more stable)
2. ✅ **Added PID logging** (debug which worker is running)
3. 📝 **Need to set VALID_API_KEYS** (in Coolify environment)
4. ⏰ **Wait 5 minutes after deployment** (models take time to load)

## Next Step

**Deploy the changes and check logs carefully for model loading messages!**

If you still don't see "Loading ML models..." in the logs, the lifespan function isn't executing, and we'll need to switch to a different initialization strategy.
