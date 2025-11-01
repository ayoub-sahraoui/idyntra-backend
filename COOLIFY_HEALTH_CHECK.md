# Coolify Health Check Configuration

## Health Check Settings in Coolify Dashboard

Configure these settings in **Coolify Dashboard → Advanced → General (or Settings) → Health Check**:

| Field | Value |
|-------|-------|
| **Path** | `/health` |
| **Port** | `8000` |
| **Interval** | `10` (seconds) |
| **Timeout** | `5` (seconds) |
| **Healthy threshold** | `2` |

## What This Does

- **Path: `/health`** - Uses the lightweight health check endpoint (no model loading)
- **Port: 8000** - The internal port your FastAPI app listens on
- **Interval: 10s** - Checks health every 10 seconds
- **Timeout: 5s** - Waits up to 5 seconds for response
- **Healthy threshold: 2** - Needs 2 consecutive successful checks to mark as healthy

## Why These Settings?

1. **`/health` instead of `/health/detailed`**: The basic endpoint returns immediately without loading ML models, preventing 502 timeouts during startup
2. **Port 8000**: Matches the exposed port in docker-compose and uvicorn configuration
3. **10s interval**: Frequent enough to catch issues quickly without overwhelming the service
4. **5s timeout**: Generous enough for container startup but catches hanging requests
5. **Threshold 2**: Prevents false positives from transient network issues

## Testing Health Checks

### Inside Container
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-11-01T10:30:45.123456"
}
```

### From Outside (after Traefik routing fixed)
```bash
curl https://api.idyntra.space/health
```

## Troubleshooting

### Health Check Fails with 502
- **Cause**: Using `/health/detailed` which loads models
- **Fix**: Use `/health` instead (already configured in docker-compose.coolify.yml)

### Health Check Times Out
- **Cause**: Port mismatch or service not started
- **Fix**: Verify port is set to 8000 in Coolify settings

### Health Check Returns 404
- **Cause**: Wrong path or routing issue
- **Fix**: Ensure path is exactly `/health` (case-sensitive)

## Related Files

- `docker-compose.coolify.yml` - Contains container health check configuration
- `Dockerfile.production` - Creates `/app/healthcheck.sh` script
- `app/api/v1/endpoints/health.py` - Health check endpoint implementation

## Next Steps After Configuration

1. Save health check settings in Coolify
2. Redeploy the application
3. Monitor the health check status in Coolify dashboard
4. Test external access: `curl https://api.idyntra.space/health`
