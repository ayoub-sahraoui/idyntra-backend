# Manual Testing Guide for Verification API

## Setup

### 1. Start the API Server
```powershell
cd d:\Projects\SaaS\idyntra\backend\v1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Get Your API Key
Check your `.env` file for `API_KEY` or set one:
```
API_KEY=test-key-12345
```

## Testing with cURL (PowerShell)

### Test 1: Same Image Attack (Main Bug)
This test sends the same image for both document and selfie - should be REJECTED.

```powershell
# First, create a test image (you can use any face photo)
# Save it as test_image.jpg

# PowerShell command
curl -X POST "http://localhost:8000/api/v1/verify" `
  -H "X-API-Key: test-key-12345" `
  -F "id_document=@test_image.jpg" `
  -F "selfie=@test_image.jpg"
```

**Expected Result:**
```json
{
  "status": "rejected",
  "overall_confidence": 0.0,
  "message": "❌ Fraud detected: Same image used for both document and selfie",
  "similarity_check": {
    "is_duplicate": true,
    "similarity_score": 0.99
  }
}
```

### Test 2: Valid Verification
Use different images - one with an ID card, one selfie of the same person.

```powershell
curl -X POST "http://localhost:8000/api/v1/verify" `
  -H "X-API-Key: test-key-12345" `
  -F "id_document=@real_id.jpg" `
  -F "selfie=@real_selfie.jpg"
```

**Expected Result:**
```json
{
  "status": "approved" or "manual_review",
  "overall_confidence": 75.0+,
  "face_match": {
    "matched": true,
    "confidence": 85.0+
  },
  "liveness_check": {
    "is_live": true
  },
  "similarity_check": {
    "is_duplicate": false
  },
  "document_structure": {
    "has_document": true,
    "confidence": 0.65+
  }
}
```

### Test 3: Just a Face Photo (No Document)
Send a selfie as the document.

```powershell
curl -X POST "http://localhost:8000/api/v1/verify" `
  -H "X-API-Key: test-key-12345" `
  -F "id_document=@selfie.jpg" `
  -F "selfie=@another_selfie.jpg"
```

**Expected Result:**
```json
{
  "status": "rejected",
  "message": "❌ Invalid document: Please provide a full identity document, not just a face photo",
  "face_only_check": {
    "is_just_face": true
  }
}
```

### Test 4: Missing API Key
```powershell
curl -X POST "http://localhost:8000/api/v1/verify" `
  -F "id_document=@test_image.jpg" `
  -F "selfie=@test_image.jpg"
```

**Expected Result:**
```
Status: 403 Forbidden
```

### Test 5: Different Persons
```powershell
curl -X POST "http://localhost:8000/api/v1/verify" `
  -H "X-API-Key: test-key-12345" `
  -F "id_document=@person_a_id.jpg" `
  -F "selfie=@person_b_selfie.jpg"
```

**Expected Result:**
```json
{
  "status": "rejected" or "manual_review",
  "face_match": {
    "matched": false,
    "confidence": < 60.0
  }
}
```

## Testing with Postman

### Setup
1. Open Postman
2. Create new request: POST `http://localhost:8000/api/v1/verify`
3. Add Header: `X-API-Key: test-key-12345`
4. Go to Body → form-data
5. Add two files:
   - Key: `id_document`, Type: File, Value: [select image]
   - Key: `selfie`, Type: File, Value: [select image]
6. Click Send

### Test Cases

#### Test Case 1: Same Image Bug
- id_document: face.jpg
- selfie: face.jpg (same file)
- Expected: status = "rejected", message contains "Fraud detected"

#### Test Case 2: Selfie as Document
- id_document: selfie_only.jpg (just a face)
- selfie: another_selfie.jpg
- Expected: status = "rejected", message contains "not just a face photo"

#### Test Case 3: Valid Different Images
- id_document: id_card.jpg (actual ID)
- selfie: person_selfie.jpg (same person)
- Expected: status = "approved" or "manual_review"

## Testing with Python Script

```python
import requests

API_URL = "http://localhost:8000/api/v1/verify"
API_KEY = "test-key-12345"

def test_verification(doc_path, selfie_path):
    headers = {"X-API-Key": API_KEY}
    files = {
        'id_document': open(doc_path, 'rb'),
        'selfie': open(selfie_path, 'rb')
    }
    
    response = requests.post(API_URL, headers=headers, files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json()

# Test same image attack
print("Test 1: Same Image Attack")
result = test_verification("test_image.jpg", "test_image.jpg")
assert result['status'] == 'rejected', "Should reject same image!"
print("✅ PASSED\n")

# Test valid verification
print("Test 2: Valid Verification")
result = test_verification("id_card.jpg", "selfie.jpg")
print(f"Status: {result['status']}")
print(f"Confidence: {result['overall_confidence']}")
```

## Common Issues

### Issue 1: "Verification service not initialized"
- **Cause:** ML models failed to load
- **Solution:** Check logs, ensure all dependencies are installed
- **Command:** `pip install -r requirements.txt`

### Issue 2: All tests pass with high confidence
- **Cause:** Security checks might be disabled or bypassed
- **Solution:** Check that new detectors are properly initialized in dependencies.py

### Issue 3: Images are too similar even when different
- **Cause:** Threshold too strict
- **Solution:** Adjust IMAGE_SIMILARITY_THRESHOLD in .env (try 0.90 instead of 0.95)

### Issue 4: Document structure not detected
- **Cause:** Using photos without clear document features
- **Solution:** Use actual ID card/passport photos with visible card edges and text

## Verification Checklist

After implementing fixes, verify:

- [ ] Same image attack is rejected (0% confidence)
- [ ] Selfie-only as document is rejected
- [ ] Valid different images pass or go to manual review
- [ ] Face matching still works correctly
- [ ] No false positives on valid IDs
- [ ] Response includes new fields: similarity_check, document_structure
- [ ] API key validation works
- [ ] Error messages are clear and helpful

## Performance Testing

```powershell
# Measure response time
Measure-Command {
  curl -X POST "http://localhost:8000/api/v1/verify" `
    -H "X-API-Key: test-key-12345" `
    -F "id_document=@test_id.jpg" `
    -F "selfie=@test_selfie.jpg"
}
```

Expected time: 10-15 seconds (with ML models loaded)

## Next Steps

1. Run automated test suite: `pytest tests/ -v -s`
2. Fix any failing tests
3. Test with real identity documents
4. Monitor production logs for false positives/negatives
5. Adjust thresholds based on real-world data
