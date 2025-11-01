# Troubleshooting 504 Gateway Timeout in Coolify

## Problem
API returns 504 Gateway Timeout when accessed via `https://api.idyntra.space`, but works internally on `localhost:8000`.

## Root Cause Analysis

504 Gateway Timeout means Traefik (Coolify's reverse proxy) cannot reach your container or the request times out.

## Diagnostic Steps

### Step 1: Verify Container is Running
In Coolify Dashboard:
1. Go to your application
2. Check **Status** - should show **Running** with green indicator
3. Click **Logs** - should see:
   ```
   🚀 Starting ID Verification API v2.0.0
   Started server process [X]
   Waiting for application startup.
   Application startup complete.
   Uvicorn running on http://0.0.0.0:8000
   ```

### Step 2: Check Container Health
In Coolify Dashboard → **Logs** tab, run:
```bash
curl http://localhost:8000/health
```

Expected output:
```json
{"status":"healthy","version":"2.0.0","timestamp":"..."}
```

### Step 3: Verify Traefik Can See the Container
In Coolify Dashboard → **Advanced** → **Docker Compose** → check the API service has:
- `expose: ["8000"]` ✅
- Correct labels (see below) ✅

### Step 4: Check Traefik Configuration in Coolify

#### In Coolify Dashboard:
1. Go to **Settings** → **Domains**
2. Verify `api.idyntra.space` shows:
   - Status: **Active** ✅
   - SSL: **Enabled** ✅
   - Certificate: **Valid** ✅

#### Check Port Configuration:
1. Go to **Advanced** → **General**
2. Find **Port/Ports Exposes** field
3. **Must be set to: `8000`** ⚠️
4. If empty or different, update it to `8000` and redeploy

### Step 5: Verify Network Configuration

Check that the API service is on the correct networks:
```yaml
api:
  networks:
    - backend      # For postgres/redis communication
    - default      # For Traefik to reach the container
```

### Step 6: Check Traefik Labels

Your `docker-compose.coolify.yml` should have these labels:
```yaml
labels:
  # Coolify Management
  - "coolify.managed=true"
  - "coolify.port=8000"
  
  # Traefik Enable
  - "traefik.enable=true"
  
  # Router Configuration
  - "traefik.http.routers.api-idyntra.rule=Host(`api.idyntra.space`)"
  - "traefik.http.routers.api-idyntra.entrypoints=websecure"
  - "traefik.http.routers.api-idyntra.tls.certresolver=letsencrypt"
  
  # Service Configuration
  - "traefik.http.services.api-idyntra.loadbalancer.server.port=8000"
  - "traefik.http.services.api-idyntra.loadbalancer.server.scheme=http"
  
  # Timeout Configuration (AI processing needs time)
  - "traefik.http.services.api-idyntra.loadbalancer.responseforwardingtimeouts.dialtimeout=30s"
  - "traefik.http.services.api-idyntra.loadbalancer.responseforwardingtimeouts.responseheadertimeout=60s"
  
  # Host Header Middleware
  - "traefik.http.middlewares.api-host.headers.customrequestheaders.Host=api.idyntra.space"
  - "traefik.http.routers.api-idyntra.middlewares=api-host"
```

## Solutions

### Solution 1: Set Port in Coolify UI ⭐ **MOST COMMON FIX**

1. Coolify Dashboard → Your Application
2. **Advanced** → **General** (or **Settings**)
3. Find **Port** or **Ports Exposes** field
4. Set to: **`8000`**
5. **Save** and **Redeploy**

### Solution 2: Update Docker Compose in Coolify

1. Coolify Dashboard → Your Application
2. **Advanced** → **Docker Compose** → **Raw Compose Deployment**
3. Click **Edit**
4. Replace entire content with updated `docker-compose.coolify.yml` from this repo
5. **Save**
6. **Redeploy**

### Solution 3: Force Traefik to Recognize the Service

In Coolify terminal (or SSH into server), run:
```bash
# Find your container ID
docker ps | grep idyntra

# Check if Traefik labels are applied
docker inspect <container_id> | grep -A 20 Labels

# Restart Traefik (if you have access)
docker restart coolify-proxy
```

### Solution 4: Check Firewall/Network Rules

In your server:
```bash
# Check if port 8000 is listening
netstat -tlnp | grep 8000

# Check if Traefik network exists
docker network ls | grep coolify

# Check if container is on Traefik network
docker network inspect coolify_default | grep idyntra
```

## Testing After Fix

### Test 1: Health Check
```bash
curl -v https://api.idyntra.space/health
```

Expected:
- Status: **200 OK**
- Response: `{"status":"healthy",...}`

### Test 2: API Documentation
Open in browser:
```
https://api.idyntra.space/docs
```

Should show FastAPI Swagger UI.

### Test 3: Verification Endpoint (Your Original Request)
```bash
curl -X POST \
  'https://api.idyntra.space/api/v1/verify' \
  -H 'X-API-Key: api_1d7b6f4e8c404c0fb2e6b1aa90122379' \
  -F 'id_document=@id_card.jpg' \
  -F 'selfie=@selfie.jpg'
```

Expected:
- Status: **200 OK** (if valid request)
- Status: **401 Unauthorized** (if API key is invalid - but NOT 504!)
- Status: **422 Unprocessable Entity** (if files invalid - but NOT 504!)

## Common Mistakes

❌ **Using `ports` instead of `expose`**
```yaml
# WRONG for Coolify
ports:
  - "8000:8000"

# CORRECT for Coolify
expose:
  - "8000"
```

❌ **Not setting port in Coolify UI**
- Even with labels, Coolify UI port field must be set to 8000

❌ **Wrong router name in labels**
- Must use consistent name: `api-idyntra` in all labels
- Example: `traefik.http.routers.api-idyntra.rule=...`

❌ **Missing default network**
- Container must be on both `backend` (for DB/Redis) and `default` (for Traefik)

## Still Not Working?

### Check Traefik Logs in Coolify
1. Coolify Dashboard → **Server** → **Proxy**
2. Click **Logs**
3. Look for errors mentioning `api.idyntra.space` or `api-idyntra`

### Check Application Logs
1. Your Application → **Logs**
2. Look for incoming requests - if you see them, Traefik IS reaching your app
3. If no requests appear when you curl, Traefik is NOT routing to your container

### Nuclear Option: Recreate Application
If nothing works:
1. **Export** your environment variables
2. **Delete** the application in Coolify
3. **Create new** application with:
   - Type: **Docker Compose**
   - Repository: Your git repo
   - Docker Compose file: `docker-compose.coolify.yml`
   - **Port: 8000** ⚠️
4. Import environment variables
5. Deploy

## Reference Files

- `docker-compose.coolify.yml` - Updated compose with all fixes
- `Dockerfile.production` - Container build configuration
- `COOLIFY_HEALTH_CHECK.md` - Health check configuration
- `app/api/v1/endpoints/health.py` - Health endpoint implementation

## Contact/Debug Info to Share

If asking for help, provide:
```bash
# Container status
docker ps | grep idyntra

# Container logs (last 50 lines)
docker logs <container_id> --tail 50

# Container inspect (labels section)
docker inspect <container_id> | grep -A 30 Labels

# Traefik network
docker network inspect coolify_default | grep -A 10 idyntra

# Coolify port configuration
# Screenshot of: Advanced → General → Port field
```
