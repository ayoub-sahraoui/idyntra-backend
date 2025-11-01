# Docker Build Troubleshooting Guide

## Issue: Model Download Failure During Build

### Problem Description
The Docker build fails when trying to download HuggingFace models at line 283 in `Dockerfile.production`:

```
failed to solve: process "/bin/sh -c python -c \"from transformers import AutoImageProcessor...
```

### Root Causes

1. **Network Connectivity Issues**
   - HuggingFace servers may be temporarily unreachable
   - Corporate firewall blocking external connections
   - DNS resolution problems
   - Rate limiting from HuggingFace

2. **Timeout Issues**
   - Large model files taking too long to download
   - Slow internet connection
   - Docker build timeout

3. **Memory Constraints**
   - Insufficient memory allocated to Docker
   - Model loading requires more RAM than available

4. **Authentication Issues**
   - Some models require HuggingFace authentication token
   - Missing `HUGGING_FACE_HUB_TOKEN` environment variable

### Solutions Implemented

#### 1. Retry Logic with Timeouts
The Dockerfile now includes automatic retry logic with configurable timeouts:

```dockerfile
RUN python -c "from transformers import AutoImageProcessor, AutoModelForImageClassification; \
    import sys; \
    import time; \
    max_retries = 2; \
    retry_delay = 5; \
    for attempt in range(max_retries): \
        try: \
            processor = AutoImageProcessor.from_pretrained('...', resume_download=True, timeout=60); \
            model = AutoModelForImageClassification.from_pretrained('...', resume_download=True, timeout=60); \
            break; \
        except Exception as e: \
            if attempt < max_retries - 1: \
                time.sleep(retry_delay); \
            else: \
                raise SystemExit(0)"
```

#### 2. Graceful Fallback
If model download fails during build, the application will download models at runtime on first use. The deepfake detector has built-in fallback logic:

```python
def _load_model(self):
    try:
        self.processor = AutoImageProcessor.from_pretrained(self.model_name)
        self.model = AutoModelForImageClassification.from_pretrained(self.model_name)
        self.available = True
    except Exception as e:
        self.available = False
        print(f"Deepfake model loading failed: {e}")
```

#### 3. Cache Directory Configuration
Explicitly set HuggingFace cache directories to ensure proper model caching:

```dockerfile
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface/transformers
```

### Quick Fixes

#### Fix 1: Use Build Script with Enhanced Error Handling

**For PowerShell (Windows):**
```powershell
.\build-production.ps1
```

**For Bash (Linux/Mac):**
```bash
chmod +x build-production.sh
./build-production.sh
```

#### Fix 2: Build Without Model Pre-download

You can skip model download during build by commenting out the model stage:

```bash
# Build only the necessary stages
docker build -f Dockerfile.production --target runtime -t idyntra/id-verification-api:2.0.0 .
```

#### Fix 3: Use Docker BuildKit with Network Configuration

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build with network mode
docker build --network=host -f Dockerfile.production -t idyntra/id-verification-api:2.0.0 .
```

#### Fix 4: Configure Proxy Settings

If behind a corporate proxy:

**Linux/Mac:**
```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
docker build --build-arg http_proxy=$HTTP_PROXY --build-arg https_proxy=$HTTPS_PROXY -f Dockerfile.production .
```

**Windows PowerShell:**
```powershell
$env:HTTP_PROXY = "http://proxy.example.com:8080"
$env:HTTPS_PROXY = "http://proxy.example.com:8080"
docker build --build-arg http_proxy=$env:HTTP_PROXY --build-arg https_proxy=$env:HTTPS_PROXY -f Dockerfile.production .
```

#### Fix 5: Increase Docker Memory

Ensure Docker has sufficient memory allocated:

1. Open Docker Desktop Settings
2. Go to Resources → Advanced
3. Increase Memory to at least 6GB
4. Click "Apply & Restart"

#### Fix 6: Pre-download Models Locally

Download models on host machine and copy to container:

```bash
# On host machine
python3 -c "from transformers import AutoImageProcessor, AutoModelForImageClassification; \
    AutoImageProcessor.from_pretrained('dima806/deepfake_vs_real_image_detection'); \
    AutoModelForImageClassification.from_pretrained('dima806/deepfake_vs_real_image_detection')"

# Then mount cache in docker-compose.yml
volumes:
  - ~/.cache/huggingface:/root/.cache/huggingface:ro
```

#### Fix 7: Use Docker BuildKit Cache Mount

Update Dockerfile to use BuildKit cache mounts:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/huggingface \
    python -c "from transformers import AutoImageProcessor, AutoModelForImageClassification; \
    AutoImageProcessor.from_pretrained('dima806/deepfake_vs_real_image_detection'); \
    AutoModelForImageClassification.from_pretrained('dima806/deepfake_vs_real_image_detection')"
```

### Verification Steps

After implementing fixes, verify the build:

1. **Check Docker build logs:**
   ```bash
   docker build -f Dockerfile.production --progress=plain . 2>&1 | tee build.log
   ```

2. **Verify models are cached:**
   ```bash
   docker run --rm idyntra/id-verification-api:2.0.0 ls -la /root/.cache/huggingface/
   ```

3. **Test application startup:**
   ```bash
   docker run -d -p 8000:8000 idyntra/id-verification-api:2.0.0
   docker logs -f <container-id>
   ```

4. **Check health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

### Runtime Model Download

If models weren't cached during build, they'll be downloaded on first API call. Monitor with:

```bash
docker logs -f <container-id> | grep -i "model\|download"
```

First request may take 2-5 minutes while models download.

### Performance Impact

| Scenario | Build Time | First Request | Subsequent Requests |
|----------|-----------|---------------|---------------------|
| Models cached in image | 10-15 min | < 1 sec | < 1 sec |
| Models download at runtime | 3-5 min | 2-5 min | < 1 sec |

### Additional Resources

- **HuggingFace Model Page:** https://huggingface.co/dima806/deepfake_vs_real_image_detection
- **Transformers Documentation:** https://huggingface.co/docs/transformers
- **Docker BuildKit:** https://docs.docker.com/build/buildkit/

### Still Having Issues?

1. Check Docker daemon logs:
   ```bash
   # Linux
   sudo journalctl -u docker.service
   
   # Windows (PowerShell as Admin)
   Get-EventLog -LogName Application -Source Docker
   ```

2. Clean Docker build cache:
   ```bash
   docker builder prune -af
   ```

3. Verify network connectivity:
   ```bash
   curl -I https://huggingface.co
   curl -I https://cdn-lfs.huggingface.co
   ```

4. Try building with verbose output:
   ```bash
   docker build -f Dockerfile.production --progress=plain --no-cache . 2>&1 | tee build-verbose.log
   ```

5. Contact support with:
   - Build logs
   - Docker version: `docker --version`
   - System info: `docker info`
   - Network test results
