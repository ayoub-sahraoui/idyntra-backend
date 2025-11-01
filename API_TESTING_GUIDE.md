# API Testing Guide - Post Deployment

## ✅ Good News!

Getting "no available server" instead of 504 Gateway Timeout means **Traefik is successfully routing to your container**! This is just a Swagger UI configuration issue, which has been fixed.

## Deployment Steps

### 1. Redeploy in Coolify

Since we updated `app/main.py`, you need to rebuild and redeploy:

1. Go to **Coolify Dashboard** → Your Application
2. Click **Redeploy** button
3. Wait for build to complete (watch logs for "Application startup complete")

### 2. Test Endpoints After Deployment

#### Test 1: Health Check ✅
```bash
curl https://api.idyntra.space/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-11-01T12:34:56.789012"
}
```

#### Test 2: Swagger Documentation 📚
Open in browser:
```
https://api.idyntra.space/docs
```

**Expected:** Interactive Swagger UI with "Production server" selected in the server dropdown.

#### Test 3: ReDoc Documentation 📖
```
https://api.idyntra.space/redoc
```

**Expected:** Clean ReDoc API documentation.

#### Test 4: OpenAPI Schema 📋
```bash
curl https://api.idyntra.space/openapi.json
```

**Expected:** JSON schema of your API.

#### Test 5: Verification Endpoint (Full Test) 🔍

```bash
curl -X POST 'https://api.idyntra.space/api/v1/verify' \
  -H 'accept: application/json' \
  -H 'X-API-Key: api_1d7b6f4e8c404c0fb2e6b1aa90122379' \
  -F 'id_document=@/path/to/id_card.jpg' \
  -F 'selfie=@/path/to/selfie.jpg'
```

**Expected Responses:**

✅ **Success (200 OK):**
```json
{
  "verification_id": "uuid-here",
  "timestamp": "2025-11-01T12:34:56.789012",
  "status": "approved",
  "confidence_score": 0.92,
  "liveness_score": 0.87,
  "face_match_confidence": 0.91,
  "deepfake_probability": 0.03,
  "document_authenticity_score": 0.95,
  "mrz_data": {...},
  "warnings": [],
  "processing_time_seconds": 2.45
}
```

❌ **Invalid API Key (401 Unauthorized):**
```json
{
  "detail": "Invalid API key"
}
```

❌ **Invalid Files (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "id_document"],
      "msg": "File too large or invalid format",
      "type": "value_error"
    }
  ]
}
```

❌ **Rate Limited (429 Too Many Requests):**
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

## Testing from Swagger UI

1. Go to `https://api.idyntra.space/docs`
2. Click **Authorize** button (top right)
3. Enter API Key: `api_1d7b6f4e8c404c0fb2e6b1aa90122379`
4. Click **Authorize**
5. Navigate to **/api/v1/verify** endpoint
6. Click **Try it out**
7. Upload your files:
   - `id_document`: Your ID card/passport image
   - `selfie`: Your selfie image
8. Click **Execute**
9. Check the response

## Valid API Key Format

Your environment must have this set in Coolify:

```env
VALID_API_KEYS=api_1d7b6f4e8c404c0fb2e6b1aa90122379,api_another_key_here
```

Multiple keys separated by commas.

## Performance Expectations

| Operation | Expected Time |
|-----------|---------------|
| `/health` | < 100ms |
| `/health/detailed` | 2-5 seconds (loads models) |
| `/api/v1/verify` | 2-8 seconds (AI processing) |
| `/api/v1/extract` | 1-3 seconds |

**Note:** First request after deployment may take longer (model loading).

## Common Issues & Solutions

### Issue: Still getting "no available server"
**Cause:** Old container still running, changes not deployed  
**Fix:** Redeploy in Coolify to rebuild with new code

### Issue: 401 Unauthorized
**Cause:** Invalid or missing API key  
**Fix:** 
1. Check `VALID_API_KEYS` environment variable in Coolify
2. Ensure you're using the exact key from the environment
3. Check the header is `X-API-Key` (case-sensitive)

### Issue: 422 Unprocessable Entity
**Cause:** Invalid file format or size  
**Fix:**
- Use JPEG, PNG, or WebP images
- File size < 10MB
- Image resolution between 640x480 and 4096x4096

### Issue: 429 Rate Limited
**Cause:** Exceeded rate limit (default: 60 requests/minute)  
**Fix:** Wait 60 seconds or increase `MAX_REQUESTS_PER_MINUTE` in environment

### Issue: 504 Gateway Timeout on /verify
**Cause:** AI processing taking too long  
**Fix:** Already configured! We set response timeout to 60s in Traefik labels

## Monitoring

### Check Application Logs
Coolify Dashboard → Your Application → **Logs**

Look for:
```
🚀 Starting ID Verification API v2.0.0
✓ All components initialized
Started server process [X]
Uvicorn running on http://0.0.0.0:8000
```

### Check Request Logs
Every request is logged:
```
[uuid] Verification request: id_card.jpg, selfie.jpg
[uuid] File validation passed: ID (1920x1080), Selfie (1280x720)
[uuid] Verification complete: approved
```

### Check Traefik Routing
Coolify Dashboard → **Server** → **Proxy** → Logs

Look for:
```
api.idyntra.space -> api-idyntra@docker
```

## Troubleshooting Commands

### Inside Container (via Coolify terminal)
```bash
# Check if app is running
ps aux | grep uvicorn

# Check health internally
curl http://localhost:8000/health

# Check Python environment
python --version

# Check models loaded
ls -lh /root/.cache/huggingface/hub/
```

### From Your Machine
```bash
# Verbose health check
curl -v https://api.idyntra.space/health

# Check SSL certificate
curl -vI https://api.idyntra.space/health 2>&1 | grep -i ssl

# Check response time
time curl https://api.idyntra.space/health

# Check headers
curl -I https://api.idyntra.space/health
```

## Success Checklist

- [ ] Health endpoint returns 200 OK
- [ ] Swagger UI loads at /docs
- [ ] Server dropdown shows "Production server"
- [ ] Can authorize with API key in Swagger
- [ ] Verification endpoint accepts requests (not 504)
- [ ] Returns proper JSON responses (200/401/422, not 504)
- [ ] Response time < 10 seconds for verification
- [ ] SSL certificate valid (no warnings)

## Next Steps

Once all tests pass:
1. ✅ API is fully deployed and functional
2. 📱 Integrate with your frontend application
3. 🔑 Generate production API keys (different from test key)
4. 📊 Set up monitoring/alerting (optional)
5. 💾 Configure database backups (if not already done)
6. 📈 Monitor usage and performance

## Support Files

- `TROUBLESHOOTING_504_GATEWAY_TIMEOUT.md` - If still getting 504
- `COOLIFY_HEALTH_CHECK.md` - Health check configuration
- `docker-compose.coolify.yml` - Deployment configuration
- `app/api/v1/endpoints/verification.py` - Verification endpoint logic
