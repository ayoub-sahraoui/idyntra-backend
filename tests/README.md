# Verification API Testing

## Overview
Comprehensive test suite for the identity verification API that tests all security scenarios, edge cases, and attack vectors.

## Security Improvements

### 🔒 New Security Checks

1. **Same-Image Attack Detection**
   - Detects when the same image is submitted for both document and selfie
   - Uses multi-method similarity detection (SSIM, histogram, perceptual hash)
   - Threshold: 95% similarity = fraud alert

2. **Document Structure Validation**
   - Ensures document image contains actual ID card/passport features
   - Checks for:
     - Card edges and rectangular structure
     - Organized text regions
     - Security features (holograms, reflective areas)
     - Photo region within document
     - Standard document proportions
   - Minimum confidence: 60%

3. **Face-Only Detection**
   - Rejects images that are just close-up faces without document structure
   - Checks if face takes >60% of image area

## Test Scenarios

### Attack Scenarios
- ✅ Same image for document and selfie (FIXED BUG)
- ✅ Photo of a photo
- ✅ Regular selfie as document
- ✅ Different persons

### Edge Cases
- ✅ No face in document
- ✅ No face in selfie
- ✅ Blurry images
- ✅ Wrong image format
- ✅ Oversized images
- ✅ Low resolution images

### Valid Cases
- ✅ Proper ID verification (requires real test images)

### Security
- ✅ Missing API key
- ✅ Wrong API key
- ✅ Missing selfie
- ✅ Missing document

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx requests opencv-python numpy

# Set environment variables
export API_KEY="your-test-api-key"
```

### Start API Server
```bash
# In terminal 1
cd d:\Projects\SaaS\idyntra\backend\v1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests
```bash
# In terminal 2
cd d:\Projects\SaaS\idyntra\backend\v1

# Run all tests with verbose output
python -m pytest tests/test_verification_scenarios.py -v -s

# Run specific test
python -m pytest tests/test_verification_scenarios.py::TestVerificationAPI::test_same_image_attack -v -s

# Run only attack scenarios
python -m pytest tests/test_verification_scenarios.py -k "attack" -v -s
```

## Test Data

Tests automatically generate synthetic test images. For testing with real documents:

1. Create `tests/test_data/` directory
2. Add real test images:
   - `valid_id.jpg` - Real ID document photo
   - `valid_selfie.jpg` - Real selfie of the same person

## Expected Results

### Before Fix (BUG)
```
❌ test_same_image_attack - PASSED (should FAIL!)
Status: approved
Confidence: 85%
Face match: 100%
```

### After Fix (CORRECT)
```
✅ test_same_image_attack - FAILED (correctly detected fraud!)
Status: rejected
Confidence: 0%
Message: Fraud detected: Same image used for both document and selfie
```

## Architecture Changes

### New Files
- `app/core/image_similarity.py` - Image similarity detection
- `app/core/document_detection.py` - Document structure validation
- `tests/test_verification_scenarios.py` - Comprehensive test suite

### Modified Files
- `app/services/verification_service.py` - Added pre-validation checks
- `app/dependencies.py` - Added new detector dependencies

## Configuration

Add to `.env` file:
```bash
# Image similarity threshold (0-1, default 0.95)
IMAGE_SIMILARITY_THRESHOLD=0.95

# Document structure confidence threshold (0-1, default 0.60)
DOCUMENT_STRUCTURE_THRESHOLD=0.60
```

## Performance Impact

- Image similarity check: +0.5-1s
- Document structure check: +0.5-1s
- Total overhead: ~1-2 seconds
- Worth it for security!

## Troubleshooting

### Tests fail with 503 error
- Ensure ML models are loaded
- Check logs for model initialization errors
- Increase timeout if needed

### High false positive rate
- Adjust `IMAGE_SIMILARITY_THRESHOLD` (lower = more strict)
- Adjust `DOCUMENT_STRUCTURE_THRESHOLD` (lower = more strict)

### Tests hang
- Check if API server is running
- Verify correct port (8000)
- Check firewall settings

## Future Improvements

1. **MRZ Validation** - Validate Machine Readable Zone on passports
2. **OCR Validation** - Extract and validate text from documents
3. **Fake Document Detection** - ML model to detect printed/edited documents
4. **Age Verification** - Validate person's age matches document
5. **Document Type Detection** - Classify document type (passport, ID, license)

## License
Internal use only
