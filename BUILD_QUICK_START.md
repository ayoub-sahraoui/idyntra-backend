# Quick Start: Building After Model Download Fix

## What Was Fixed?
The Docker build was failing when downloading HuggingFace deepfake detection models. We've implemented:
- ✅ Automatic retry logic (2 attempts with timeout)
- ✅ Graceful fallback (models download at runtime if build fails)
- ✅ Enhanced build scripts with error checking
- ✅ Comprehensive troubleshooting documentation

## How to Build Now

### Option 1: Use Enhanced Build Script (Recommended)

**Windows (PowerShell):**
```powershell
.\build-production.ps1
```

**Linux/Mac:**
```bash
chmod +x build-production.sh
./build-production.sh
```

### Option 2: Direct Docker Build

```bash
docker build -f Dockerfile.production -t idyntra/id-verification-api:2.0.0 .
```

### Option 3: Using Docker Compose

```bash
docker-compose -f docker-compose.yml build api
```

## What to Expect

### Successful Build
```
📥 Downloading deepfake detection model (attempt 1/2)...
✅ Models cached successfully!
```
- **Build time**: 10-15 minutes
- **Image size**: ~3-4 GB
- **First request**: < 1 second

### Build with Failed Model Download
```
⚠️ Attempt 2 failed: Connection timeout
⚠️ Model download failed - will download at runtime on first use
```
- **Build time**: 3-5 minutes
- **Image size**: ~2-3 GB
- **First request**: 2-5 minutes (downloading models)
- **Subsequent requests**: < 1 second

## Troubleshooting

### Build Still Failing?

1. **Check Internet Connection:**
   ```powershell
   Test-NetConnection huggingface.co -Port 443
   ```

2. **Increase Docker Memory:**
   - Docker Desktop → Settings → Resources
   - Set memory to at least 6GB

3. **Clean Docker Cache:**
   ```bash
   docker builder prune -af
   ```

4. **Use Network Host Mode:**
   ```bash
   docker build --network=host -f Dockerfile.production .
   ```

5. **Read Full Troubleshooting Guide:**
   See `DOCKER_BUILD_TROUBLESHOOTING.md`

## Running the Container

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api

# Test health endpoint
curl http://localhost:8000/health
```

## Important Notes

⚠️ **First Request Delay**: If models weren't cached during build, the first API request will take 2-5 minutes while models download at runtime. This is normal and only happens once.

✅ **Subsequent Requests**: After models are loaded, all requests will be fast (< 1 second).

🔄 **Model Persistence**: Models are cached in a Docker volume and persist between container restarts.

## Need Help?

1. Check logs: `docker-compose logs -f api`
2. Read troubleshooting guide: `DOCKER_BUILD_TROUBLESHOOTING.md`
3. Check Docker version: `docker --version`
4. Verify Docker memory: `docker info | grep -i memory`

## Files Modified

- ✅ `Dockerfile.production` - Enhanced model download with retry logic
- ✅ `build-production.ps1` - Windows build script
- ✅ `build-production.sh` - Linux/Mac build script
- ✅ `DOCKER_BUILD_TROUBLESHOOTING.md` - Detailed troubleshooting
- ✅ `DOCKER_BUILD_FIXES.md` - Updated with latest fixes
- ✅ `BUILD_QUICK_START.md` - This file

## Success Indicators

✅ Build completes without errors
✅ Health check returns 200 OK
✅ Models load (check logs for "Models cached" or "Model loaded")
✅ API responds to verification requests

Happy building! 🚀
