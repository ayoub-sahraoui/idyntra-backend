from typing import Dict, Tuple
import numpy as np
import cv2


class FaceMatcher:
    """Ensemble face matching for higher accuracy"""

    def __init__(self, tolerance: float = 0.5, use_gpu: bool = False):
        self.tolerance = tolerance
        self.use_gpu = use_gpu
        self.face_recognition = None

    def match_faces(self, id_image: np.ndarray, selfie_image: np.ndarray) -> Dict:
        """Match faces between ID document and selfie"""
        try:
            # Lazy import
            import face_recognition

            # Convert to RGB for face_recognition
            id_rgb = cv2.cvtColor(id_image, cv2.COLOR_BGR2RGB)
            selfie_rgb = cv2.cvtColor(selfie_image, cv2.COLOR_BGR2RGB)

            # Find faces
            id_locations = face_recognition.face_locations(id_rgb, model='hog')
            selfie_locations = face_recognition.face_locations(selfie_rgb, model='hog')

            if not id_locations or not selfie_locations:
                return {
                    'matched': False,
                    'confidence': 0.0,
                    'error': 'Face not detected in one or both images'
                }

            # Get encodings
            id_encoding = face_recognition.face_encodings(id_rgb, id_locations)[0]
            selfie_encoding = face_recognition.face_encodings(selfie_rgb, selfie_locations)[0]

            # Calculate distance and confidence
            distance = float(face_recognition.face_distance([id_encoding], selfie_encoding)[0])
            matched = bool(distance <= self.tolerance)
            confidence = float((1 - distance) * 100)

            return {
                'matched': matched,
                'confidence': confidence,
                'distance': distance,
                'strategy': 'face_recognition',
                'threshold_used': self.tolerance
            }

        except Exception as e:
            return {
                'matched': False,
                'confidence': 0.0,
                'error': str(e)
            }

    def get_quality_metrics(self, image: np.ndarray) -> Dict:
        """Assess image quality for face matching"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Sharpness (blur detection)
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            # Brightness
            brightness = float(np.mean(gray))

            # Contrast
            contrast = float(np.std(gray))

            # Resolution
            height, width = image.shape[:2]
            resolution = height * width

            # Calculate scores
            sharpness_score = min(sharpness / 500.0, 1.0) * 100
            brightness_score = (1 - abs(brightness - 127) / 127) * 100
            contrast_score = min(contrast / 64.0, 1.0) * 100
            resolution_score = min(resolution / (640 * 480), 1.0) * 100

            overall_quality = (sharpness_score + brightness_score + contrast_score + resolution_score) / 4

            return {
                'sharpness': float(sharpness),
                'brightness': float(brightness),
                'contrast': float(contrast),
                'resolution': int(resolution),
                'quality_score': float(overall_quality),
                'is_good_quality': bool(overall_quality >= 60.0)
            }

        except Exception as e:
            return {
                'is_good_quality': False,
                'error': str(e)
            }