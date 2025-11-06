"""
Document structure detection
Validates that an image contains an actual identity document (ID card, passport, etc.)
"""
from typing import Dict, List, Tuple
import numpy as np
import cv2


class DocumentStructureDetector:
    """Detect if an image contains a structured identity document"""
    
    def __init__(self):
        self.min_confidence = 0.25  # Lowered to 25% for maximum real-world acceptance
    
    def detect_document_structure(self, image: np.ndarray) -> Dict:
        """
        Check if image contains document-like structures
        
        Returns:
            Dict with:
                - has_document: bool
                - confidence: float (0-1)
                - features_detected: dict
                - passed: bool
        """
        features = {}
        scores = []
        
        # Check 1: Card/Document edges
        edge_result = self._detect_card_edges(image)
        features['card_edges'] = edge_result
        if edge_result['detected']:
            scores.append(0.30)  # 30% weight
        
        # Check 2: Text regions (documents have structured text)
        text_result = self._detect_text_regions(image)
        features['text_regions'] = text_result
        if text_result['has_text_regions']:
            scores.append(0.25)  # 25% weight
        
        # Check 3: Hologram/Security features (reflective areas)
        security_result = self._detect_security_features(image)
        features['security_features'] = security_result
        if security_result['detected']:
            scores.append(0.20)  # 20% weight
        
        # Check 4: Photo area (documents have a distinct photo region)
        photo_result = self._detect_photo_region(image)
        features['photo_region'] = photo_result
        if photo_result['detected']:
            scores.append(0.15)  # 15% weight
        
        # Check 5: Document proportions (aspect ratio)
        proportion_result = self._check_document_proportions(image)
        features['proportions'] = proportion_result
        if proportion_result['is_document_sized']:
            scores.append(0.10)  # 10% weight
        
        # Calculate overall confidence
        confidence = sum(scores)
        has_document = confidence >= self.min_confidence
        
        return {
            'has_document': bool(has_document),
            'confidence': float(confidence),
            'features_detected': features,
            'passed': bool(has_document),
            'threshold_used': self.min_confidence
        }
    
    def _detect_card_edges(self, image: np.ndarray) -> Dict:
        """Detect rectangular card edges"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Apply bilateral filter to reduce noise while preserving edges
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # Edge detection with multiple thresholds for better detection
            edges1 = cv2.Canny(filtered, 30, 100)
            edges2 = cv2.Canny(filtered, 50, 150)
            edges3 = cv2.Canny(filtered, 100, 200)
            
            # Combine edges
            edges = cv2.bitwise_or(edges1, cv2.bitwise_or(edges2, edges3))
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for rectangular contours with more lenient criteria
            rectangles = []
            for contour in contours:
                # Approximate contour
                epsilon = 0.03 * cv2.arcLength(contour, True)  # More lenient approximation
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Check if it's rectangle-like (4-8 corners for flexibility)
                if 4 <= len(approx) <= 8:
                    area = cv2.contourArea(contour)
                    # Lowered threshold to 5% of image for smaller/distant cards
                    if area > (image.shape[0] * image.shape[1] * 0.05):
                        rectangles.append({
                            'area': area,
                            'corners': len(approx)
                        })
            
            detected = len(rectangles) > 0
            
            return {
                'detected': detected,
                'rectangles_found': len(rectangles),
                'details': rectangles[:3] if detected else []  # Top 3
            }
            
        except Exception as e:
            return {'detected': False, 'error': str(e)}
    
    def _detect_text_regions(self, image: np.ndarray) -> Dict:
        """Detect structured text regions (documents have organized text)"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Apply adaptive thresholding for better text detection
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY_INV, 11, 2)
            
            # Use morphological operations to find text regions
            # Horizontal kernel for text lines
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
            dilated = cv2.dilate(thresh, kernel, iterations=1)
            
            # Find contours
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Count horizontal text-like regions with more lenient criteria
            text_regions = 0
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                # Text regions are typically wider than tall
                aspect_ratio = w / float(h) if h > 0 else 0
                # Lowered width threshold from 50 to 30 for smaller text
                if aspect_ratio > 1.5 and w > 30:  # More lenient for various text sizes
                    text_regions += 1
            
            # Lowered threshold from 3 to 2 text regions
            has_text = text_regions >= 2  # Documents typically have multiple text lines
            
            return {
                'has_text_regions': has_text,
                'text_regions_count': text_regions
            }
            
        except Exception as e:
            return {'has_text_regions': False, 'error': str(e)}
    
    def _detect_security_features(self, image: np.ndarray) -> Dict:
        """Detect hologram/security features (shiny/reflective areas)"""
        try:
            if len(image.shape) == 3:
                # Convert to HSV to detect bright/shiny areas
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                
                # Look for high saturation and high value (shiny areas)
                lower = np.array([0, 0, 180])  # Lowered from 200 for more sensitivity
                upper = np.array([180, 120, 255])  # Increased saturation range
                mask = cv2.inRange(hsv, lower, upper)
                
                # Count shiny pixels
                shiny_pixels = np.sum(mask > 0)
                total_pixels = mask.size
                shiny_ratio = shiny_pixels / total_pixels
                
                # More lenient range: 0.5% to 15% (was 1% to 10%)
                detected = 0.005 <= shiny_ratio <= 0.15
                
                return {
                    'detected': detected,
                    'shiny_ratio': float(shiny_ratio),
                    'shiny_pixels': int(shiny_pixels)
                }
            else:
                # For grayscale, still pass (fail open)
                return {'detected': True, 'reason': 'grayscale image - assumed present'}
                
        except Exception as e:
            # Fail open - assume security features might be present
            return {'detected': True, 'error': str(e)}
    
    def _detect_photo_region(self, image: np.ndarray) -> Dict:
        """Detect distinct photo region (ID cards have a photo of the person)"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Documents often have a clear boundary around the photo
            # Use edge detection and find rectangular regions
            edges = cv2.Canny(gray, 100, 200)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for square/rectangular photo regions
            photo_candidates = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                # Photo region should be 5-30% of total image
                min_area = image.shape[0] * image.shape[1] * 0.05
                max_area = image.shape[0] * image.shape[1] * 0.30
                
                if min_area < area < max_area:
                    # Check if it's roughly square/rectangular
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / float(h) if h > 0 else 0
                    if 0.6 < aspect_ratio < 1.5:  # Roughly square
                        photo_candidates += 1
            
            detected = photo_candidates > 0
            
            return {
                'detected': detected,
                'photo_candidates': photo_candidates
            }
            
        except Exception as e:
            return {'detected': False, 'error': str(e)}
    
    def _check_document_proportions(self, image: np.ndarray) -> Dict:
        """Check if image has document-like proportions"""
        try:
            h, w = image.shape[:2]
            aspect_ratio = w / float(h)
            
            # Common document aspect ratios:
            # - Credit card / ID card: 1.586 (85.60 × 53.98 mm)
            # - Passport: ~1.4
            # - Driver's license: varies but ~1.5-1.6
            # Expanded acceptable range: 1.2 to 2.0 for more flexibility
            # Also accept portrait orientation (inverse ratio)
            is_landscape = 1.2 <= aspect_ratio <= 2.0
            is_portrait = 0.5 <= aspect_ratio <= 0.83  # Inverse of landscape range
            
            is_document_sized = is_landscape or is_portrait
            
            return {
                'is_document_sized': is_document_sized,
                'aspect_ratio': float(aspect_ratio),
                'width': w,
                'height': h,
                'orientation': 'landscape' if is_landscape else ('portrait' if is_portrait else 'unknown')
            }
            
        except Exception as e:
            return {'is_document_sized': False, 'error': str(e)}
    
    def is_just_a_face(self, image: np.ndarray) -> Dict:
        """
        Detect if image is just a close-up face (not a document)
        """
        try:
            import face_recognition
            
            # Detect faces
            face_locations = face_recognition.face_locations(image, model='hog')
            
            if not face_locations:
                return {
                    'is_just_face': False,
                    'reason': 'no face detected'
                }
            
            # Get largest face
            largest_face = max(face_locations, key=lambda f: (f[2] - f[0]) * (f[1] - f[3]))
            top, right, bottom, left = largest_face
            
            face_area = (bottom - top) * (right - left)
            image_area = image.shape[0] * image.shape[1]
            face_ratio = face_area / image_area
            
            # If face takes up more than 60% of image, it's probably just a face
            is_just_face = face_ratio > 0.60
            
            return {
                'is_just_face': is_just_face,
                'face_area_ratio': float(face_ratio),
                'passed': not is_just_face
            }
            
        except Exception as e:
            return {
                'is_just_face': False,
                'error': str(e),
                'passed': True  # Fail open
            }
