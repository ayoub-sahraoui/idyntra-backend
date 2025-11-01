# API Endpoints Review & Documentation

## 📋 Complete Endpoint List

### **Public Endpoints (No Authentication)**

#### 1. **Root Endpoint**
```
GET /
```
- **Purpose**: API information and entry point
- **Response**: Service name, version, status, links to docs
- **Use**: Quick API identification

#### 2. **Basic Health Check**
```
GET /health
```
- **Purpose**: Fast health check without loading models
- **Response**: Status, version, device info
- **Use**: Load balancer health checks, monitoring
- **Performance**: ~50ms response time

#### 3. **Detailed Health Check**
```
GET /health/detailed
```
- **Purpose**: Verify all ML models are loaded and functional
- **Response**: Status + detailed component verification
- **Use**: Deep health verification, troubleshooting
- **Performance**: ~100ms (models already loaded at startup)

#### 4. **Readiness Probe**
```
GET /ready
```
- **Purpose**: Kubernetes/Docker readiness probe
- **Response**: `{"status": "ready"}`
- **Use**: Container orchestration to know when to route traffic
- **Note**: For Coolify/Kubernetes deployments

#### 5. **Liveness Probe**
```
GET /live
```
- **Purpose**: Kubernetes/Docker liveness probe
- **Response**: `{"status": "alive"}`
- **Use**: Container orchestration to detect if process is alive
- **Note**: Used to restart unhealthy containers

---

### **Protected Endpoints (Require X-API-Key Header)**

#### 6. **Identity Verification**
```
POST /api/v1/verify
```
- **Purpose**: Complete identity verification
- **Headers**: `X-API-Key: your_api_key`
- **Body**: 
  - `id_document` (file): ID card/passport/driver's license
  - `selfie` (file): Live selfie photo
- **Process**:
  1. Liveness detection (anti-spoofing)
  2. Face matching (document vs selfie)
  3. Document authenticity check
  4. Deepfake detection
- **Response**: Verification result with confidence scores
- **Performance**: 2-5 seconds
- **Rate Limit**: 60 requests/minute

#### 7. **MRZ Text Extraction**
```
POST /api/v1/extract-text
```
- **Purpose**: Extract Machine Readable Zone data from documents
- **Headers**: `X-API-Key: your_api_key`
- **Body**: 
  - `document` (file): Document image with MRZ
- **Supports**:
  - Passports
  - ID cards
  - Visas
  - Other MRZ documents
- **Response**: Extracted structured data (name, DOB, nationality, etc.)
- **Performance**: 1-3 seconds
- **Rate Limit**: 60 requests/minute

---

## 🔍 Endpoint Purpose Analysis

### Why do we have `/live`, `/ready`, and `/health`?

These serve **different purposes** for different systems:

1. **`/health`** - **Application-level health**
   - Used by: Monitoring tools, dashboards, load balancers
   - Checks: API is running and configured
   - Fast: No model loading

2. **`/health/detailed`** - **Deep verification**
   - Used by: Troubleshooting, post-deployment verification
   - Checks: All ML models functional
   - Slower: Verifies all components

3. **`/ready`** - **Kubernetes Readiness Probe**
   - Used by: Kubernetes, Docker Swarm, Coolify
   - Indicates: Container is ready to receive traffic
   - Load balancers won't route until this returns success

4. **`/live`** - **Kubernetes Liveness Probe**
   - Used by: Kubernetes, Docker Swarm, Coolify
   - Indicates: Process is alive (not deadlocked/crashed)
   - If this fails, container is restarted

**Best Practice**: Keep all these endpoints. They serve different orchestration needs.

---

## 🔐 Authentication

### API Key Authentication

All verification and extraction endpoints require:
```
X-API-Key: your_api_key_here
```

**Example**:
```bash
curl -X POST https://api.idyntra.space/api/v1/verify \
  -H "X-API-Key: api_1d7b6f4e8c404c0fb2e6b1aa90122379" \
  -F "id_document=@doc.jpg" \
  -F "selfie=@selfie.jpg"
```

### Rate Limiting

- **Default**: 60 requests per minute per API key
- **Configurable**: Via `MAX_REQUESTS_PER_MINUTE` env variable
- **429 Response**: When limit exceeded
  - Includes `Retry-After` header
  - JSON response with retry time

---

## 🐛 Enhanced Error Logging

### What Changed

All endpoints now have **comprehensive error logging**:

1. **Verification Endpoint (`/api/v1/verify`)**
   ```
   [verification_id] === VERIFICATION REQUEST START ===
   [verification_id] ID Document: filename.jpg, Content-Type: image/jpeg
   [verification_id] Selfie: selfie.jpg, Content-Type: image/jpeg
   [verification_id] Service available, starting validation...
   [verification_id] ✓ File validation passed: ID (1920x1080), Selfie (1280x720)
   [verification_id] Reading images...
   [verification_id] ✓ ID document image read, shape: (1080, 1920, 3)
   [verification_id] ✓ Selfie image read, shape: (720, 1280, 3)
   [verification_id] Starting verification process...
   [verification_id] ✓ Verification process completed
   [verification_id] === VERIFICATION COMPLETE: approved ===
   ```

2. **Extraction Endpoint (`/api/v1/extract-text`)**
   ```
   === MRZ EXTRACTION REQUEST START ===
   Document: passport.jpg, Content-Type: image/jpeg
   Reading document image...
   ✓ Document image read, shape: (1080, 1920, 3)
   Starting MRZ extraction...
   ✓ MRZ extraction completed
   === MRZ EXTRACTION COMPLETE: 15 fields ===
   ```

3. **Health Endpoints**
   - All health endpoints log access and errors
   - Startup logs each model initialization separately
   - Clear success/failure indicators

### Error Detection

**If endpoint returns 502**, check logs for:
- `CRITICAL: VerificationService is None!` - Service not initialized
- `FAILED to load` - Model initialization failed
- `File validation failed` - Invalid image format/size
- `Image reading failed` - Corrupted image
- `Verification process failed` - Internal processing error

---

## 📊 API Testing Guide

### 1. Test Health Check
```bash
curl https://api.idyntra.space/health
```
**Expected**: `200 OK` with status "healthy"

### 2. Test Detailed Health
```bash
curl https://api.idyntra.space/health/detailed
```
**Expected**: `200 OK` with all components true

### 3. Test Verification (with valid API key)
```bash
curl -X POST https://api.idyntra.space/api/v1/verify \
  -H "X-API-Key: your_api_key" \
  -F "id_document=@test_id.jpg" \
  -F "selfie=@test_selfie.jpg"
```
**Expected**: `200 OK` with verification result

### 4. Test Without API Key (should fail)
```bash
curl -X POST https://api.idyntra.space/api/v1/verify \
  -F "id_document=@test_id.jpg" \
  -F "selfie=@test_selfie.jpg"
```
**Expected**: `403 Forbidden` - "API key is required"

### 5. Test Rate Limiting
```bash
# Run this 65 times rapidly
for i in {1..65}; do
  curl -X POST https://api.idyntra.space/api/v1/verify \
    -H "X-API-Key: your_api_key" \
    -F "id_document=@test_id.jpg" \
    -F "selfie=@test_selfie.jpg"
done
```
**Expected**: First 60 succeed, 61+ return `429 Too Many Requests`

---

## 🚀 Deployment Checklist

After deploying the new changes:

### 1. **Pull and Rebuild**
```bash
cd /your/deployment/path
git pull origin main
docker-compose -f docker-compose.coolify.yml build api
docker-compose -f docker-compose.coolify.yml up -d
```

### 2. **Monitor Startup Logs**
```bash
docker-compose -f docker-compose.coolify.yml logs -f api
```

**Look for**:
```
🚀 Starting ID Verification API v2.0.0
Loading ML models...
✓ Liveness detector loaded
✓ Face matcher loaded
✓ MRZ extractor loaded
✓ Document authenticator loaded
✓ Deepfake detector loaded
✓ ALL COMPONENTS INITIALIZED SUCCESSFULLY
```

### 3. **Test Each Endpoint**

```bash
# 1. Basic health
curl https://api.idyntra.space/health

# 2. Detailed health
curl https://api.idyntra.space/health/detailed

# 3. Verification
curl -X POST https://api.idyntra.space/api/v1/verify \
  -H "X-API-Key: your_key" \
  -F "id_document=@test_id.jpg" \
  -F "selfie=@test_selfie.jpg"
```

### 4. **Check Logs for Errors**
```bash
# View detailed logs
docker-compose -f docker-compose.coolify.yml logs api | grep -i "error\|failed\|critical"
```

---

## 🔧 Troubleshooting 502 Errors

### Possible Causes & Solutions

#### 1. **Models Not Loaded**
**Symptom**: `/health` works, `/verify` returns 502

**Check logs for**:
```
CRITICAL: VerificationService is None!
```

**Solution**: Verify all models loaded at startup:
```bash
docker-compose logs api | grep "✓.*loaded"
```

#### 2. **Timeout During Request**
**Symptom**: Request takes >60 seconds

**Check logs for**:
```
Starting verification process...
(no completion message)
```

**Solution**: 
- Increase nginx timeout in `nginx.production.conf`
- Check CPU/memory resources
- Verify models are preloaded (not loading on-demand)

#### 3. **Service Dependency Failure**
**Symptom**: Intermittent 502 errors

**Check**:
```bash
docker-compose ps  # Check if all containers are healthy
docker-compose logs postgres  # Check database
docker-compose logs redis  # Check cache
```

#### 4. **Image Processing Error**
**Check logs for**:
```
Image reading failed: ...
File validation failed: ...
```

**Solution**: Verify image format and size constraints

---

## 📝 Environment Variables

### Required for Production

```bash
# Security
SECRET_KEY=your-secret-key
API_KEY_HASH_SALT=your-salt
POSTGRES_PASSWORD=your-db-password
REDIS_PASSWORD=your-redis-password

# Valid API Keys (comma-separated)
VALID_API_KEYS=api_1d7b6f4e8c404c0fb2e6b1aa90122379,api_another_key

# Rate Limiting
MAX_REQUESTS_PER_MINUTE=60

# Allowed Origins (comma-separated or *)
ALLOWED_ORIGINS=*
ALLOWED_HOSTS=api.idyntra.space,*.idyntra.space
```

---

## 📊 API Response Formats

### Verification Response
```json
{
  "verification_id": "uuid",
  "timestamp": "2025-11-01T15:06:51",
  "status": "approved|rejected|manual_review",
  "overall_confidence": 92.5,
  "message": "✅ Identity verified (confidence: 92.5%)",
  "liveness_check": {
    "passed": true,
    "liveness_score": 0.95
  },
  "face_match": {
    "passed": true,
    "confidence": 95.2
  },
  "document_authenticity": {
    "passed": true,
    "authenticity_score": 88.0
  },
  "deepfake_check": {
    "passed": true,
    "confidence": 0.92
  }
}
```

### Extraction Response
```json
{
  "success": true,
  "mrz_detected": true,
  "fields_extracted": 15,
  "message": "✅ MRZ detected - 15 fields extracted",
  "structured_data": {
    "document_type": "P",
    "country_code": "USA",
    "surname": "DOE",
    "given_names": "JOHN",
    "passport_number": "123456789",
    "nationality": "USA",
    "date_of_birth": "1990-01-01",
    "sex": "M",
    "expiration_date": "2030-01-01"
  },
  "timestamp": "2025-11-01T15:06:51"
}
```

---

## 🎯 Summary

### Endpoints Overview
- ✅ **5 public endpoints** (no auth required)
- ✅ **2 protected endpoints** (API key required)
- ✅ **All endpoints** have comprehensive error logging
- ✅ **All ML models** preloaded at startup
- ✅ **Rate limiting** active on protected endpoints

### What to Monitor
1. Startup logs - verify all models load
2. Request logs - track verification flow
3. Error logs - catch failures early
4. Performance metrics - response times

### Next Steps
1. Deploy to production
2. Monitor logs for errors
3. Test all endpoints
4. Verify 502 errors are resolved
