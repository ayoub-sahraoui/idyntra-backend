# Docker Build Fixes Applied

## Latest Update: Model Download Resilience (Nov 1, 2025)

### HuggingFace Model Download Failure
**Problem**: Build failing at model download stage with exit code 1:
```
failed to solve: process "/bin/sh -c python -c \"from transformers import AutoImageProcessor...
exit code: 1
```

**Root Causes**:
- Network connectivity issues to HuggingFace servers
- Model download timeouts
- Potential rate limiting

**Solutions Implemented**:
1. **Retry Logic**: Added automatic retry mechanism (2 attempts with 5-second delay)
2. **Timeout Configuration**: Set explicit 60-second timeout for downloads
3. **Graceful Fallback**: If build-time download fails, models download at runtime
4. **Cache Environment Variables**: Set `HF_HOME` and `TRANSFORMERS_CACHE` explicitly
5. **Enhanced Scripts**: Created `build-production.ps1` and `build-production.sh` with error handling

**Files Changed**:
- `Dockerfile.production` (lines 105-131): Enhanced model download with retry logic
- `build-production.ps1` (new): PowerShell build script with network checks
- `build-production.sh` (new): Bash build script with prerequisites validation
- `DOCKER_BUILD_TROUBLESHOOTING.md` (new): Comprehensive troubleshooting guide

**Quick Fix**:
```powershell
# Use the enhanced build script
.\build-production.ps1
```

---

## Previous Issues Fixed

### 1. Dockerfile Syntax Error (Heredoc)
**Problem**: Docker heredoc syntax (`<< 'EOF'`) was not parsing correctly, causing:
```
failed to solve: dockerfile parse error on line 467: unknown instruction: set
```

**Solution**: Replaced all heredoc blocks with `printf` statements for better compatibility.

**Files Changed**:
- `Dockerfile.production` (lines with entrypoint.sh, healthcheck.sh, cleanup_logs.sh)

---

### 2. Tesseract Traineddata Download Failure
**Problem**: curl was failing with exit code 22 (HTTP error) when trying to download:
```
exit code: 22
```

**Root Cause**: 
- GitHub URLs for tesseract traineddata files were no longer accessible
- The repository `alex-raw/tesseract_mrz` appears to be unavailable

**Solution**: 
- Use the system-installed tesseract traineddata files instead
- The `tesseract-ocr-eng` package already includes `eng.traineddata`
- Added fallback logic to find traineddata in multiple locations
- MRZ-specific traineddata can be added later if needed

---

### 3. Environment Variable Warning
**Problem**: Warning about undefined variable `k8r1p7f`:
```
WARNING: The "k8r1p7f" variable is not set. Defaulting to a blank string.
```

**Note**: This appears to be from docker-compose and doesn't affect the build. If needed, ensure all required variables are defined in `.env.production`.

---

## How to Build Now

```bash
# Build the production image
docker-compose -f docker-compose.production.yml build api

# Or build directly
docker build -f Dockerfile.production \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VERSION=2.0.0 \
  -t idyntra/id-verification-api:2.0.0 \
  .
```

---

## Additional Notes

### Tesseract Configuration
The Dockerfile now:
1. Uses system-installed tesseract traineddata from the `tesseract-ocr-eng` package
2. Sets up proper symlinks and directory structure
3. Has fallback logic to locate traineddata in various system locations
4. Copies traineddata to readmrz package with error handling

### MRZ Traineddata
If you need MRZ-specific traineddata later, you can:

1. **Option A**: Download at runtime in the application
2. **Option B**: Add it manually to the image after build
3. **Option C**: Host it on a reliable CDN and download during build

Example for Option C:
```dockerfile
RUN curl -fsSL -o /usr/share/tesseract-ocr/4.00/tessdata/mrz.traineddata \
    https://your-cdn.com/mrz.traineddata
```

---

## Testing the Build

After the build completes successfully, verify:

```bash
# Check if the image was created
docker images | grep idyntra

# Test run the container
docker run --rm -it idyntra/id-verification-api:2.0.0 bash

# Inside container, verify tesseract
tesseract --version
ls -la /usr/share/tesseract-ocr/*/tessdata/
```

---

**Status**: ✅ Ready to build  
**Last Updated**: 2025-11-01  
**Version**: 2.0.0
