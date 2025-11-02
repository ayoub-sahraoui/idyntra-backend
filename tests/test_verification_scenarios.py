"""
Comprehensive test suite for verification API
Tests all security scenarios including edge cases and attacks
"""

import pytest
import requests
import os
from pathlib import Path
import numpy as np
import cv2
from io import BytesIO


class TestVerificationAPI:
    """Test all verification scenarios"""
    
    BASE_URL = "http://localhost:8000"
    API_KEY = os.getenv("API_KEY", "your-test-api-key")
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.headers = {"X-API-Key": self.API_KEY}
        self.test_data_dir = Path(__file__).parent / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
    
    def _create_test_image(self, name: str, width: int = 800, height: int = 600, 
                          color=(200, 200, 200), add_face=False) -> Path:
        """Create a test image"""
        img = np.ones((height, width, 3), dtype=np.uint8) * np.array(color, dtype=np.uint8)
        
        if add_face:
            # Draw simple face-like structure
            center_x, center_y = width // 2, height // 2
            # Face oval
            cv2.ellipse(img, (center_x, center_y), (100, 130), 0, 0, 360, (220, 180, 160), -1)
            # Eyes
            cv2.circle(img, (center_x - 40, center_y - 20), 15, (50, 50, 50), -1)
            cv2.circle(img, (center_x + 40, center_y - 20), 15, (50, 50, 50), -1)
            # Nose
            cv2.line(img, (center_x, center_y), (center_x, center_y + 40), (180, 140, 120), 3)
            # Mouth
            cv2.ellipse(img, (center_x, center_y + 60), (40, 20), 0, 0, 180, (150, 80, 80), 2)
        
        file_path = self.test_data_dir / f"{name}.jpg"
        cv2.imwrite(str(file_path), img)
        return file_path
    
    def _make_request(self, doc_path: Path, selfie_path: Path):
        """Make verification request"""
        with open(doc_path, 'rb') as doc, open(selfie_path, 'rb') as selfie:
            files = {
                'id_document': ('document.jpg', doc, 'image/jpeg'),
                'selfie': ('selfie.jpg', selfie, 'image/jpeg')
            }
            response = requests.post(
                f"{self.BASE_URL}/api/v1/verify",
                headers=self.headers,
                files=files
            )
        return response
    
    # ==================== ATTACK SCENARIOS ====================
    
    def test_same_image_attack(self):
        """
        TEST: Send same image for both document and selfie
        EXPECTED: Should REJECT - same image indicates fraud
        CURRENT BUG: This passes but shouldn't!
        """
        selfie_path = self._create_test_image("selfie_only", add_face=True)
        
        response = self._make_request(selfie_path, selfie_path)
        result = response.json()
        
        print(f"\n[SAME IMAGE ATTACK TEST]")
        print(f"Status: {result['status']}")
        print(f"Confidence: {result['overall_confidence']:.1f}%")
        print(f"Face match: {result['face_match']['confidence']:.1f}%")
        
        # This should fail!
        assert result['status'] == 'rejected', "Same image attack should be rejected!"
        assert 'same_image' in result or 'duplicate' in result.get('message', '').lower()
    
    def test_photo_of_photo_attack(self):
        """
        TEST: Send photo of an ID instead of real ID
        EXPECTED: Should detect via liveness/document checks
        """
        # Create a "photo of ID" - basically a photo with an ID-like image inside
        photo = self._create_test_image("photo_of_id", add_face=True)
        selfie = self._create_test_image("real_selfie", add_face=True)
        
        response = self._make_request(photo, selfie)
        result = response.json()
        
        print(f"\n[PHOTO OF PHOTO ATTACK TEST]")
        print(f"Status: {result['status']}")
        print(f"Confidence: {result['overall_confidence']:.1f}%")
        
        # Should have lower confidence
        assert result['overall_confidence'] < 80, "Photo attack should have lower confidence"
    
    def test_no_document_structure(self):
        """
        TEST: Send regular selfie as document image
        EXPECTED: Should detect no document features (no MRZ, no card edges, etc.)
        """
        fake_doc = self._create_test_image("just_face", add_face=True)
        selfie = self._create_test_image("selfie", add_face=True)
        
        response = self._make_request(fake_doc, selfie)
        result = response.json()
        
        print(f"\n[NO DOCUMENT STRUCTURE TEST]")
        print(f"Status: {result['status']}")
        print(f"Has document validation: {'document_structure' in result}")
        
        assert result['status'] != 'approved', "Should reject images without document structure"
    
    def test_different_persons(self):
        """
        TEST: Different persons in document and selfie
        EXPECTED: Face matching should fail
        """
        doc = self._create_test_image("person_a", add_face=True)
        selfie = self._create_test_image("person_b", add_face=True, color=(180, 180, 180))
        
        response = self._make_request(doc, selfie)
        result = response.json()
        
        print(f"\n[DIFFERENT PERSONS TEST]")
        print(f"Status: {result['status']}")
        print(f"Face match confidence: {result['face_match']['confidence']:.1f}%")
        
        assert result['face_match']['matched'] == False, "Different faces should not match"
        assert result['status'] in ['rejected', 'manual_review']
    
    # ==================== EDGE CASES ====================
    
    def test_no_face_in_document(self):
        """
        TEST: Document image with no face
        EXPECTED: Should fail face detection
        """
        doc = self._create_test_image("no_face_doc")
        selfie = self._create_test_image("selfie", add_face=True)
        
        response = self._make_request(doc, selfie)
        result = response.json()
        
        print(f"\n[NO FACE IN DOCUMENT TEST]")
        print(f"Status: {result['status']}")
        print(f"Face match error: {result['face_match'].get('error', 'No error')}")
        
        assert result['face_match']['matched'] == False
        assert 'not detected' in result['face_match'].get('error', '').lower()
    
    def test_no_face_in_selfie(self):
        """
        TEST: Selfie with no face
        EXPECTED: Should fail face detection and liveness
        """
        doc = self._create_test_image("doc_with_face", add_face=True)
        selfie = self._create_test_image("no_face_selfie")
        
        response = self._make_request(doc, selfie)
        result = response.json()
        
        print(f"\n[NO FACE IN SELFIE TEST]")
        print(f"Status: {result['status']}")
        print(f"Liveness error: {result['liveness_check'].get('error', 'No error')}")
        
        assert result['status'] == 'rejected'
        assert result['liveness_check']['is_live'] == False
    
    def test_blurry_image(self):
        """
        TEST: Very blurry images
        EXPECTED: Should fail blur detection
        """
        # Create and blur
        doc_path = self._create_test_image("sharp_doc", add_face=True)
        img = cv2.imread(str(doc_path))
        blurry = cv2.GaussianBlur(img, (51, 51), 0)
        blurry_path = self.test_data_dir / "blurry_doc.jpg"
        cv2.imwrite(str(blurry_path), blurry)
        
        selfie = self._create_test_image("selfie", add_face=True)
        
        response = self._make_request(blurry_path, selfie)
        result = response.json()
        
        print(f"\n[BLURRY IMAGE TEST]")
        print(f"Status: {result['status']}")
        blur_check = result.get('liveness_check', {}).get('checks', {}).get('_check_blur', {})
        print(f"Blur score: {blur_check.get('blur_score', 'N/A')}")
        
        # Should have lower confidence due to blur
        assert result['overall_confidence'] < 70
    
    def test_wrong_image_format(self):
        """
        TEST: Invalid image format
        EXPECTED: Should return 400 error
        """
        # Create a text file instead of image
        fake_img = self.test_data_dir / "fake.jpg"
        with open(fake_img, 'w') as f:
            f.write("This is not an image!")
        
        selfie = self._create_test_image("selfie", add_face=True)
        
        response = self._make_request(fake_img, selfie)
        
        print(f"\n[WRONG FORMAT TEST]")
        print(f"Status code: {response.status_code}")
        
        assert response.status_code == 400
    
    def test_oversized_image(self):
        """
        TEST: Image exceeding size limits
        EXPECTED: Should return 400 error
        """
        # Create very large image (over 10MB)
        large_img_path = self.test_data_dir / "large.jpg"
        large = np.random.randint(0, 255, (8000, 8000, 3), dtype=np.uint8)
        cv2.imwrite(str(large_img_path), large, [cv2.IMWRITE_JPEG_QUALITY, 100])
        
        selfie = self._create_test_image("selfie", add_face=True)
        
        response = self._make_request(large_img_path, selfie)
        
        print(f"\n[OVERSIZED IMAGE TEST]")
        print(f"Status code: {response.status_code}")
        
        assert response.status_code == 400
    
    def test_low_resolution(self):
        """
        TEST: Images below minimum resolution
        EXPECTED: Should return 400 error
        """
        doc = self._create_test_image("low_res_doc", width=320, height=240)
        selfie = self._create_test_image("low_res_selfie", width=320, height=240)
        
        response = self._make_request(doc, selfie)
        
        print(f"\n[LOW RESOLUTION TEST]")
        print(f"Status code: {response.status_code}")
        
        assert response.status_code == 400
    
    # ==================== VALID SCENARIOS ====================
    
    @pytest.mark.skip(reason="Requires real test images")
    def test_valid_verification_real_images(self):
        """
        TEST: Valid ID and selfie from same person
        EXPECTED: Should approve
        NOTE: Requires real test images in test_data folder
        """
        doc = self.test_data_dir / "valid_id.jpg"
        selfie = self.test_data_dir / "valid_selfie.jpg"
        
        if not doc.exists() or not selfie.exists():
            pytest.skip("Real test images not available")
        
        response = self._make_request(doc, selfie)
        result = response.json()
        
        print(f"\n[VALID VERIFICATION TEST]")
        print(f"Status: {result['status']}")
        print(f"Confidence: {result['overall_confidence']:.1f}%")
        print(f"Face match: {result['face_match']['confidence']:.1f}%")
        print(f"Liveness: {result['liveness_check']['is_live']}")
        
        assert result['status'] in ['approved', 'manual_review']
        assert result['face_match']['matched'] == True
        assert result['liveness_check']['is_live'] == True
    
    # ==================== SECURITY SCENARIOS ====================
    
    def test_missing_api_key(self):
        """
        TEST: Request without API key
        EXPECTED: Should return 403
        """
        doc = self._create_test_image("doc", add_face=True)
        selfie = self._create_test_image("selfie", add_face=True)
        
        with open(doc, 'rb') as d, open(selfie, 'rb') as s:
            files = {
                'id_document': ('doc.jpg', d, 'image/jpeg'),
                'selfie': ('selfie.jpg', s, 'image/jpeg')
            }
            response = requests.post(
                f"{self.BASE_URL}/api/v1/verify",
                files=files
            )
        
        print(f"\n[MISSING API KEY TEST]")
        print(f"Status code: {response.status_code}")
        
        assert response.status_code == 403
    
    def test_wrong_api_key(self):
        """
        TEST: Request with wrong API key
        EXPECTED: Should return 403
        """
        doc = self._create_test_image("doc", add_face=True)
        selfie = self._create_test_image("selfie", add_face=True)
        
        headers = {"X-API-Key": "wrong-key-12345"}
        
        with open(doc, 'rb') as d, open(selfie, 'rb') as s:
            files = {
                'id_document': ('doc.jpg', d, 'image/jpeg'),
                'selfie': ('selfie.jpg', s, 'image/jpeg')
            }
            response = requests.post(
                f"{self.BASE_URL}/api/v1/verify",
                headers=headers,
                files=files
            )
        
        print(f"\n[WRONG API KEY TEST]")
        print(f"Status code: {response.status_code}")
        
        assert response.status_code == 403
    
    def test_missing_selfie(self):
        """
        TEST: Request with only document
        EXPECTED: Should return 422 (validation error)
        """
        doc = self._create_test_image("doc", add_face=True)
        
        with open(doc, 'rb') as d:
            files = {
                'id_document': ('doc.jpg', d, 'image/jpeg')
            }
            response = requests.post(
                f"{self.BASE_URL}/api/v1/verify",
                headers=self.headers,
                files=files
            )
        
        print(f"\n[MISSING SELFIE TEST]")
        print(f"Status code: {response.status_code}")
        
        assert response.status_code == 422
    
    def test_missing_document(self):
        """
        TEST: Request with only selfie
        EXPECTED: Should return 422 (validation error)
        """
        selfie = self._create_test_image("selfie", add_face=True)
        
        with open(selfie, 'rb') as s:
            files = {
                'selfie': ('selfie.jpg', s, 'image/jpeg')
            }
            response = requests.post(
                f"{self.BASE_URL}/api/v1/verify",
                headers=self.headers,
                files=files
            )
        
        print(f"\n[MISSING DOCUMENT TEST]")
        print(f"Status code: {response.status_code}")
        
        assert response.status_code == 422


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
