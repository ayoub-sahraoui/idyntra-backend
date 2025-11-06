# Threshold Tuning Guide

## Current Test Results (Before Redeploy)

### Issues Identified:
1. ❌ **Document Detection Too Strict**: 7/8 tests rejected with "No document detected"
2. ❌ **Valid IDs Being Rejected**: `valid_id_and_selfie` and `clean_cropped_id` failed
3. ⚠️ **One test passed document detection but failed face match**: `unclear_id` (confidence: 33.3%)

## Recommended Threshold Adjustments

### 1. Document Structure Detection
**Current values** (already updated in code, needs redeploy):
```python
min_confidence = 0.40  # Lowered from 0.60
```

**After redeploy, if still failing**:
- Lower to `0.30` (30%) for even more lenient acceptance
- Consider making it `0.25` minimum

**Location**: `app/core/document_detection.py` line 22

### 2. Face Match Thresholds
**Current values** (in .env):
```env
FACE_MATCH_CONFIDENCE_MIN=70.0    # Minimum for approval
FACE_MATCH_CONFIDENCE_HIGH=85.0   # High confidence threshold
FACE_MATCH_TOLERANCE=0.5          # Distance tolerance
```

**Recommendations based on test**:
- Lower `FACE_MATCH_CONFIDENCE_MIN` to `60.0` (more lenient)
- Keep `FACE_MATCH_CONFIDENCE_HIGH` at `85.0`
- Increase `FACE_MATCH_TOLERANCE` to `0.6` (allow more variation)

### 3. Liveness Detection
**Current values** (in .env):
```env
LIVENESS_SCORE_MIN=0.65    # 65% minimum
LIVENESS_SCORE_HIGH=0.80   # 80% high confidence
```

**Status**: Seems OK (unclear_id test showed 0.67 score)
- Consider lowering `LIVENESS_SCORE_MIN` to `0.60` if too strict

### 4. Overall Confidence Decision Thresholds
**Current values** (in verification_service.py):
```python
if overall >= 75:          # Auto-approve
    status = APPROVED
elif overall >= 55:        # Manual review
    status = MANUAL_REVIEW
else:                      # Reject
    status = REJECTED
```

**Recommendations**:
- Lower auto-approve from `75` to `70`
- Lower manual review from `55` to `50`
- This gives more cases a chance at approval or review

**Location**: `app/services/verification_service.py` lines 252-259

### 5. Weighted Scoring
**Current weights**:
```python
overall = (
    liveness_score * 0.20 +      # 20% - Liveness
    face_confidence * 0.50 +     # 50% - Face matching (most important)
    auth_score * 0.10 +          # 10% - Document auth
    deepfake_conf * 0.20         # 20% - Deepfake
)
```

**Status**: Good balance, face matching is weighted appropriately

## Step-by-Step Tuning Process

### Phase 1: Redeploy Current Changes ✅ 
1. Go to Coolify dashboard
2. Find your ID Verification API project
3. Click "Redeploy" or "Restart"
4. Wait for build to complete (~5-10 minutes)
5. Run test script again: `python test_verification_local.py`

### Phase 2: Adjust Environment Variables (if needed)
If document detection passes but face matching is too strict:

1. Update `.env` or Coolify environment variables:
```env
# More lenient face matching
FACE_MATCH_CONFIDENCE_MIN=60.0
FACE_MATCH_TOLERANCE=0.6

# More lenient liveness
LIVENESS_SCORE_MIN=0.60

# More lenient overall thresholds (requires code change)
```

2. Redeploy again

### Phase 3: Code Adjustments (if needed)
If environment variables aren't enough:

**File: `app/core/document_detection.py`**
```python
# Line 22 - Lower document detection threshold
self.min_confidence = 0.30  # or even 0.25
```

**File: `app/services/verification_service.py`**
```python
# Lines 252-259 - Lower decision thresholds
if overall >= 70:  # Was 75
    status = VerificationStatus.APPROVED
elif overall >= 50:  # Was 55
    status = VerificationStatus.MANUAL_REVIEW
else:
    status = VerificationStatus.REJECTED
```

### Phase 4: Test Each Scenario
After each adjustment, test all scenarios:

**Expected Results**:
- ✅ `valid_id_and_selfie`: Should **APPROVE** or **MANUAL_REVIEW** (not reject!)
- ✅ `clean_cropped_id`: Should **APPROVE**
- ⚠️ `unclear_id`: Should **MANUAL_REVIEW** (acceptable: REJECT)
- ⚠️ `unclear_face`: Should **MANUAL_REVIEW** (acceptable: REJECT)
- ❌ `mismatch_face`: Should **REJECT** ✓
- ❌ `fake_id`: Should **REJECT** ✓
- ❌ `deepfake_face`: Should **REJECT** ✓
- ❌ `invalid_face`: Should **REJECT** ✓

## Quick Reference: Where to Change What

| What to Adjust | File | Line(s) | Purpose |
|----------------|------|---------|---------|
| Document detection threshold | `app/core/document_detection.py` | 22 | How strict to detect ID cards |
| Face match confidence | `.env` | - | `FACE_MATCH_CONFIDENCE_MIN` |
| Face match tolerance | `.env` | - | `FACE_MATCH_TOLERANCE` |
| Liveness threshold | `.env` | - | `LIVENESS_SCORE_MIN` |
| Overall decision thresholds | `app/services/verification_service.py` | 252-259 | Approve/Review/Reject cutoffs |
| Score weights | `app/services/verification_service.py` | 246-251 | How much each check matters |

## Monitoring & Logging

After redeployment, check logs for:
```
Document structure detection results: {...}
```

This will show:
- `has_document`: true/false
- `confidence`: actual score (0-1)
- `threshold_used`: what threshold it compared against
- `features_detected`: which features were found

## Current Status

- ✅ Code changes pushed to GitHub (commit f2cc49e)
- ⏳ **Waiting for Coolify redeploy**
- 📝 Test results saved above
- 🎯 Next: Redeploy and re-test

## Support Commands

```bash
# Re-run tests
python test_verification_local.py

# Check API health
curl https://api.idyntra.space/api/v1/health

# View API documentation
# Browser: https://api.idyntra.space/docs
```
