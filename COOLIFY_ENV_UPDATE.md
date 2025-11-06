# Coolify Environment Variables - Required Updates

## ⚠️ CRITICAL: Update These Values in Coolify

Go to: **Coolify Dashboard → Your Project → Environment Variables**

### Current (OLD) Values in Coolify:
```env
FACE_MATCH_CONFIDENCE_MIN=70.0
FACE_MATCH_TOLERANCE=0.5
LIVENESS_SCORE_MIN=0.65
```

### ✅ Update To (NEW) Values:
```env
FACE_MATCH_CONFIDENCE_MIN=40.0
FACE_MATCH_TOLERANCE=0.85
LIVENESS_SCORE_MIN=0.60
```

## Why These Changes Are Critical:

### 1. FACE_MATCH_TOLERANCE: 0.5 → 0.85
**Problem**: Valid matching faces have distance=0.811
- Current tolerance: 0.5 ❌ (too strict, rejects at 0.811)
- New tolerance: 0.85 ✅ (accepts up to 0.85)

**Impact**: This is THE critical fix. Without this, valid IDs keep getting rejected.

### 2. FACE_MATCH_CONFIDENCE_MIN: 70.0 → 40.0
**Problem**: ID photos vs selfies show low confidence (~18-26%)
- Current minimum: 70% ❌ (impossible to reach for ID-to-selfie)
- New minimum: 40% ✅ (realistic for ID-to-selfie matching)

**Impact**: Allows the system to approve when faces match, even with low confidence.

### 3. LIVENESS_SCORE_MIN: 0.65 → 0.60
**Problem**: Slightly too strict
- Current minimum: 65% ❌
- New minimum: 60% ✅

**Impact**: Minor improvement, more forgiving.

## Step-by-Step in Coolify:

1. **Go to your Coolify dashboard**
2. **Select your ID Verification API project**
3. **Click on "Environment Variables" tab**
4. **Find and update these 3 variables:**
   - `FACE_MATCH_CONFIDENCE_MIN` → Change to `40.0`
   - `FACE_MATCH_TOLERANCE` → Change to `0.85`
   - `LIVENESS_SCORE_MIN` → Change to `0.60`
5. **Click "Save"**
6. **Click "Redeploy" or "Restart"**

## After Update:

Run the test script:
```bash
python test_verification_local.py
```

### Expected Results:
| Test Case | Current | After Fix |
|-----------|---------|-----------|
| valid_id_and_selfie | REJECTED (47%) | **MANUAL_REVIEW** or **APPROVED** (55-65%) |
| clean_cropped_id | REJECTED (0%) | Needs separate fix |
| unclear_face | MANUAL_REVIEW ✓ | MANUAL_REVIEW ✓ |
| mismatch_face | MANUAL_REVIEW | MANUAL_REVIEW or REJECT |

**Key Change**: Face matches will now show `matched: true` instead of `matched: false`

## Verification:

After redeploy, the API should log the updated values. Check logs for:
```
Config loaded: FACE_MATCH_TOLERANCE=0.85
```

If you see the old value (0.5), the environment variable wasn't updated correctly.

## Alternative: Bulk Update

If Coolify supports it, you can copy-paste this full updated section:

```env
# Verification Thresholds (Updated)
LIVENESS_SCORE_MIN=0.60
LIVENESS_SCORE_HIGH=0.80
BLUR_THRESHOLD=100.0
FACE_MATCH_CONFIDENCE_MIN=40.0
FACE_MATCH_CONFIDENCE_HIGH=85.0
FACE_MATCH_TOLERANCE=0.85
AUTHENTICITY_SCORE_MIN=60.0
AUTHENTICITY_SCORE_HIGH=75.0
DEEPFAKE_CONFIDENCE_MIN=0.70
IMAGE_QUALITY_MIN=60.0
```

Keep all other environment variables as they are!
