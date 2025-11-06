#!/usr/bin/env python3
"""
Local verification testing script
Tests all verification scenarios against the running API
"""
import requests
import json
from pathlib import Path
from typing import Dict, Tuple
import sys
import os

# API Configuration
API_BASE_URL = "https://api.idyntra.space"
API_KEY = os.getenv("API_KEY", "api_1d7b6f4e8c404c0fb2e6b1aa90122379")  # Your API key

# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "✅ Valid ID and Selfie (Should APPROVE)",
        "folder": "valid_id_and_selfie",
        "id_file": "id.jpg",
        "selfie_file": "selfie.jpg",
        "expected_status": "approved",
        "description": "Real ID with matching selfie - should pass all checks"
    },
    {
        "name": "✅ Clean Cropped ID (Should APPROVE)",
        "folder": "clean_cropped_id",
        "id_file": "id.jpg",
        "selfie_file": "selfie.jpg",
        "expected_status": "approved",
        "description": "Well-cropped ID with matching selfie"
    },
    {
        "name": "⚠️ Unclear ID (Should MANUAL_REVIEW or REJECT)",
        "folder": "unclear_id",
        "id_file": "id.png",
        "selfie_file": "selfie.jpg",
        "expected_status": "manual_review",
        "description": "Blurry or low-quality ID scan"
    },
    {
        "name": "⚠️ Unclear Face (Should MANUAL_REVIEW or REJECT)",
        "folder": "unclear_face",
        "id_file": "id.jpg",
        "selfie_file": "selfie.png",
        "expected_status": "manual_review",
        "description": "Poor quality selfie"
    },
    {
        "name": "❌ Mismatch Face (Should REJECT)",
        "folder": "mismatch_face",
        "id_file": "id.jpg",
        "selfie_file": "selfie.png",
        "expected_status": "rejected",
        "description": "Different person in ID vs selfie"
    },
    {
        "name": "❌ Fake ID (Should REJECT)",
        "folder": "fake_id",
        "id_file": "id.png",
        "selfie_file": "selfie.png",
        "expected_status": "rejected",
        "description": "Fraudulent or tampered ID document"
    },
    {
        "name": "❌ Deepfake Face (Should REJECT)",
        "folder": "deepfake_face",
        "id_file": "id.jpg",
        "selfie_file": "selfie.png",
        "expected_status": "rejected",
        "description": "AI-generated or manipulated selfie"
    },
    {
        "name": "❌ Invalid Face (Should REJECT)",
        "folder": "invalid_face",
        "id_file": "id.jpg",
        "selfie_file": "selfie.jpg",
        "expected_status": "rejected",
        "description": "Not a real face or inappropriate image"
    }
]


def test_verification(id_path: Path, selfie_path: Path, api_key: str) -> Tuple[bool, Dict]:
    """
    Test verification endpoint with given images
    
    Returns:
        Tuple of (success, response_data)
    """
    try:
        # Prepare files
        files = {
            'id_document': ('id.jpg', open(id_path, 'rb'), 'image/jpeg'),
            'selfie': ('selfie.jpg', open(selfie_path, 'rb'), 'image/jpeg')
        }
        
        headers = {
            'X-API-Key': api_key
        }
        
        # Make request
        response = requests.post(
            f"{API_BASE_URL}/api/v1/verify",
            files=files,
            headers=headers,
            timeout=60
        )
        
        # Close files
        for file_tuple in files.values():
            file_tuple[1].close()
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {
                'error': f"HTTP {response.status_code}",
                'detail': response.text
            }
            
    except Exception as e:
        return False, {'error': str(e)}


def print_result(scenario: Dict, success: bool, response: Dict):
    """Pretty print test result"""
    print("\n" + "="*80)
    print(f"🧪 TEST: {scenario['name']}")
    print(f"📁 Folder: {scenario['folder']}")
    print(f"📝 Description: {scenario['description']}")
    print(f"🎯 Expected: {scenario['expected_status'].upper()}")
    print("-"*80)
    
    if not success:
        print(f"❌ REQUEST FAILED: {response.get('error', 'Unknown error')}")
        if 'detail' in response:
            print(f"Details: {response['detail'][:200]}")
        return
    
    # Extract key info
    status = response.get('status', 'unknown')
    confidence = response.get('overall_confidence', 0)
    message = response.get('message', 'No message')
    
    # Detailed checks
    face_match = response.get('face_match', {})
    liveness = response.get('liveness_check', {})
    deepfake = response.get('deepfake_check', {})
    doc_auth = response.get('document_authenticity', {})
    
    print(f"✨ ACTUAL STATUS: {status.upper()}")
    print(f"📊 Confidence: {confidence:.1f}%")
    print(f"💬 Message: {message}")
    print()
    print("📋 Individual Checks:")
    print(f"   👤 Face Match: {'✅' if face_match.get('matched') else '❌'} "
          f"({face_match.get('confidence', 0):.1f}% confidence)")
    if face_match.get('error'):
        print(f"      Error: {face_match.get('error')}")
    
    liveness_score = liveness.get('liveness_score')
    print(f"   🎭 Liveness: {'✅' if liveness.get('is_live') else '❌'} "
          f"(score: {liveness_score if liveness_score is None else f'{liveness_score:.2f}'})")
    if liveness.get('error'):
        print(f"      Error: {liveness.get('error')}")
    
    print(f"   🤖 Deepfake: {'✅' if deepfake.get('is_real') else '❌'} "
          f"({deepfake.get('label', 'Unknown')})")
    if deepfake.get('error'):
        print(f"      Error: {deepfake.get('error')}")
    
    print(f"   📄 Document: {'✅' if doc_auth.get('is_authentic') else '❌'} "
          f"({doc_auth.get('authenticity_score', 0) or 0:.1f}%)")
    if doc_auth.get('error'):
        print(f"      Error: {doc_auth.get('error')}")
    
    # Check document structure if present
    if 'document_structure' in response:
        doc_struct = response['document_structure']
        print(f"\n   🔍 Document Structure Detection:")
        print(f"      Has Document: {doc_struct.get('has_document')}")
        print(f"      Confidence: {doc_struct.get('confidence', 0):.2f}")
        print(f"      Threshold: {doc_struct.get('threshold_used', 0):.2f}")
    
    # Verdict
    print()
    expected = scenario['expected_status']
    if status == expected:
        print(f"✅ TEST PASSED - Status matches expected ({expected})")
    elif status == 'manual_review' and expected in ['approved', 'rejected']:
        print(f"⚠️ TEST PARTIAL - Got manual_review instead of {expected} (acceptable)")
    else:
        print(f"❌ TEST FAILED - Expected {expected}, got {status}")
    
    print("="*80)


def main():
    print("🚀 Starting Verification API Tests")
    print(f"📡 API URL: {API_BASE_URL}")
    print(f"🔑 API Key: {API_KEY[:10]}...")
    
    docs_dir = Path(__file__).parent / "docs"
    
    if not docs_dir.exists():
        print(f"❌ Error: docs directory not found at {docs_dir}")
        sys.exit(1)
    
    results = []
    
    for scenario in TEST_SCENARIOS:
        folder_path = docs_dir / scenario['folder']
        id_path = folder_path / scenario['id_file']
        selfie_path = folder_path / scenario['selfie_file']
        
        if not id_path.exists():
            print(f"⚠️ Skipping {scenario['name']}: ID file not found at {id_path}")
            continue
        
        if not selfie_path.exists():
            print(f"⚠️ Skipping {scenario['name']}: Selfie file not found at {selfie_path}")
            continue
        
        print(f"\n🔄 Testing: {scenario['folder']}...")
        success, response = test_verification(id_path, selfie_path, API_KEY)
        print_result(scenario, success, response)
        
        results.append({
            'scenario': scenario['name'],
            'success': success,
            'status': response.get('status') if success else 'error',
            'expected': scenario['expected_status']
        })
    
    # Summary
    print("\n\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r['success'] and r['status'] == r['expected'])
    partial = sum(1 for r in results if r['success'] and r['status'] == 'manual_review')
    failed = sum(1 for r in results if not r['success'] or 
                 (r['status'] != r['expected'] and r['status'] != 'manual_review'))
    
    print(f"✅ Passed: {passed}/{len(results)}")
    print(f"⚠️ Partial (manual_review): {partial}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    print("="*80)


if __name__ == "__main__":
    main()
