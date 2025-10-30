from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import numpy as np
import cv2
from skimage.feature import local_binary_pattern


@dataclass
class LivenessConfig:
    """Liveness detection configuration"""
    blur_threshold: float = 100.0
    face_size_min: int = 80
    face_size_max: int = 800
    specular_reflection_min: float = 20.0
    micro_texture_score_min: float = 0.15
    depth_cue_score_min: float = 0.3
    liveness_score_threshold: float = 0.65


class LivenessDetector:
    """Modular liveness detection with configurable checks"""

    def __init__(self, config: LivenessConfig):
        self.config = config
        self._checks = [
            self._check_blur,
            self._detect_specular_reflections,
            self._analyze_micro_texture,
            self._detect_print_attack,
            self._estimate_depth_cues,
            self._check_face_proportions
        ]

    def check(self, image: np.ndarray, face_location: Optional[Tuple] = None) -> Dict:
        """Run all liveness checks"""

        if face_location is None:
            # Lazy import to avoid circular dependency
            import face_recognition
            face_locations = face_recognition.face_locations(image, model='hog')
            if not face_locations:
                return {
                    'is_live': False,
                    'liveness_score': 0.0,
                    'error': 'No face detected',
                    'checks': {}
                }
            face_location = face_locations[0]

        results = {}
        for check_fn in self._checks:
            check_name = check_fn.__name__.replace('_', ' ').title()
            try:
                results[check_fn.__name__] = check_fn(image, face_location)
            except Exception as e:
                results[check_fn.__name__] = {'passed': False, 'error': str(e)}

        checks_passed = sum(1 for r in results.values() if r.get('passed', False))
        total_checks = len(results)
        liveness_score = checks_passed / total_checks if total_checks > 0 else 0.0

        return {
            'is_live': liveness_score >= self.config.liveness_score_threshold,
            'liveness_score': liveness_score,
            'checks_passed': f"{checks_passed}/{total_checks}",
            'checks': results,
            'confidence': 'high' if liveness_score > 0.8 else 'medium' if liveness_score > 0.65 else 'low'
        }

    def _check_blur(self, image: np.ndarray, face_location: Tuple) -> Dict:
        """Blur detection using Laplacian variance"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        return {
            'blur_score': blur_score,
            'passed': blur_score > self.config.blur_threshold
        }

    def _detect_specular_reflections(self, image: np.ndarray, face_location: Tuple) -> Dict:
        """Detect eye reflections"""
        top, right, bottom, left = face_location
        eye_region = image[top:top + int((bottom - top) * 0.4), left:right]

        gray = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY) if len(eye_region.shape) == 3 else eye_region
        _, bright_spots = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        reflection_score = float(np.sum(bright_spots > 0) / bright_spots.size * 100)
        return {
            'reflection_score': reflection_score,
            'passed': reflection_score > self.config.specular_reflection_min
        }

    def _analyze_micro_texture(self, image: np.ndarray, face_location: Tuple) -> Dict:
        """Analyze micro-texture patterns"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        lbp = local_binary_pattern(gray, P=8, R=1, method='uniform')

        hist, _ = np.histogram(lbp.ravel(), bins=59, range=(0, 59))
        hist = hist.astype(float) / hist.sum()
        hist = hist[hist > 0]
        entropy = float(-np.sum(hist * np.log2(hist)))

        normalized_score = entropy / 5.9
        return {
            'micro_texture_score': normalized_score,
            'passed': normalized_score > self.config.micro_texture_score_min
        }

    def _detect_print_attack(self, image: np.ndarray, face_location: Tuple) -> Dict:
        """Detect print/photo attacks"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        fft = np.fft.fft2(gray)
        magnitude = np.abs(np.fft.fftshift(fft))

        high_freq_energy = float(np.sum(magnitude[magnitude.shape[0]//4:3*magnitude.shape[0]//4,
                                              magnitude.shape[1]//4:3*magnitude.shape[1]//4]))

        return {
            'high_freq_energy': high_freq_energy,
            'passed': high_freq_energy < 8e9
        }

    def _estimate_depth_cues(self, image: np.ndarray, face_location: Tuple) -> Dict:
        """Estimate depth cues"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)

        depth_score = float(np.std(gradient_magnitude) / (np.mean(gradient_magnitude) + 1e-6))
        depth_score = min(depth_score / 2.0, 1.0)

        return {
            'depth_score': depth_score,
            'passed': depth_score > self.config.depth_cue_score_min
        }

    def _check_face_proportions(self, face_location: Tuple, image_shape: Tuple) -> Dict:
        """Validate face size and position"""
        top, right, bottom, left = face_location
        face_width = right - left
        face_height = bottom - top

        size_valid = (
            self.config.face_size_min < face_width < self.config.face_size_max and
            self.config.face_size_min < face_height < self.config.face_size_max
        )

        return {'passed': size_valid}